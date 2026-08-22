#services/Aichat_service.py

from functools import lru_cache

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langgraph.checkpoint.mongodb import MongoDBSaver

from llm_config import make_chat_model
from database.database import get_client, get_db_name, sessions_col

load_dotenv()

llm = make_chat_model()

embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")


@lru_cache(maxsize=32)
def _build_retriever(session_id: str):
    """Build a FAISS retriever from a session's transcript.

    Bounded LRU cache keyed by ``session_id``: one session == one immutable
    video, so re-embedding the whole transcript through the Google embeddings
    API on every single tool call (the old behaviour) is pure waste. Errors are
    NOT cached — if the transcript isn't loaded yet the exception propagates and
    the next call (after /analyze) rebuilds cleanly.
    """
    session = sessions_col().find_one({"_id": session_id})
    video = (session or {}).get("video") or {}
    transcript = video.get("transcript")
    if not transcript or not str(transcript).strip():
        raise ValueError(
            "No transcript loaded for this session yet. Analyze a video "
            "(POST /youtube/analyze) before chatting."
        )

    docs = [Document(page_content=str(transcript))]
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    vector_store = FAISS.from_documents(chunks, embeddings)
    return vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})


@tool
def rag_tool(query: str, config: RunnableConfig) -> dict:
    """
    Retrieve relevant information from the video's transcript.
    Use this tool when the user asks factual / conceptual questions
    that might be answered from the stored transcript.
    """
   
    session_id = (config or {}).get("configurable", {}).get("thread_id")
    if not session_id:
        raise ValueError("Missing session context for retrieval.")

    retriever = _build_retriever(session_id)
    result = retriever.invoke(query)

    context = [doc.page_content for doc in result]
    metadata = [doc.metadata for doc in result]

    return {
        'query': query,
        'context': context,
        'metadata': metadata,
    }


tools = [rag_tool]
llm_with_tools = llm.bind_tools(tools)


CHAT_SYSTEM_PROMPT = (
    "You are a helpful assistant for a YouTube video. The video's transcript "
    "is already stored and searchable through the `rag_tool`. To answer any "
    "question about the video's content, call `rag_tool` with a query to "
    "retrieve the relevant transcript passages, then answer using them. "
    "Never ask the user to provide or paste the transcript — it is already "
    "available to you. If the retrieved context does not contain the answer, "
    "say so briefly."
)


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def chat_node(state: ChatState):
   
    messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT), *state['messages']]
    response = llm_with_tools.invoke(messages)
    return {'messages': [response]}


tool_node = ToolNode(tools)
graph = StateGraph(ChatState)

graph.add_node('chat_node', chat_node)
graph.add_node('tools', tool_node)

graph.add_edge(START, 'chat_node')
graph.add_conditional_edges('chat_node', tools_condition)
graph.add_edge('tools', 'chat_node')


@lru_cache(maxsize=1)
def get_chatbot():
    """Compile the chat graph with a MongoDB checkpointer, once.

    Built lazily (not at import) because ``MongoDBSaver.__init__`` creates its
    indexes eagerly — i.e. it connects to the cluster. Doing that at import
    would crash the whole app on boot while ``MONGODB_URI`` is still a
    placeholder. Deferring it here means the app boots fine and only a real chat
    request touches the DB. The sync saver is safe under the async graph: its
    ``aget``/``aput`` run pymongo in a thread-pool executor.
    """
    checkpointer = MongoDBSaver(get_client(), db_name=get_db_name())
    return graph.compile(checkpointer=checkpointer)


def _message_text(message) -> str:
    """Best-effort extraction of an assistant/user message's text, tolerant of
    string content, content-block lists, and ``.text`` being a property."""
    text = getattr(message, "text", None)
    if callable(text):
        try:
            text = text()
        except Exception:
            text = None
    if isinstance(text, str) and text:
        return text

    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", "") or "")
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content or "")


async def chatwithAi(session_id: str, user_query: str) -> str:
    config = {"configurable": {"thread_id": session_id}}

   
    result = await get_chatbot().ainvoke(
        {"messages": [HumanMessage(content=user_query)]},
        config=config,
    )

    return _message_text(result['messages'][-1])


async def get_chat_history(session_id: str) -> list[dict]:
    """Reconstruct the visible chat history for a session from the checkpointer
    (the single source of truth). Returns [] for a brand-new thread."""
    config = {"configurable": {"thread_id": session_id}}
    snap = await get_chatbot().aget_state(config)

    values = getattr(snap, "values", None) or {}
    messages = values.get("messages", []) if isinstance(values, dict) else []

    history = []
    for m in messages:
        text = _message_text(m)
        if not text or not text.strip():
            continue  
        mtype = getattr(m, "type", None)
        if mtype == "human":
            history.append({"role": "user", "content": text})
        elif mtype == "ai":
            history.append({"role": "assistant", "content": text})
      
    return history
