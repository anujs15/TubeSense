#services/Aichat_service.py

from llm_config import make_chat_model
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_google_genai import GoogleGenerativeAIEmbeddings


from database.database import database

load_dotenv()

#llm = init_chat_model("google_genai:gemini-2.5-flash-lite", timeout=30)

llm = make_chat_model()


embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")


def _build_retriever():
	"""Build a fresh retriever from the current database state."""
	if isinstance(database, dict):
		transcript = database.get("transcript")
		if not transcript or not str(transcript).strip():
			raise ValueError(
				"No transcript loaded yet. Call /youtube/analyze before chatting."
			)
		docs = [Document(page_content=transcript)]
	else:
		loader = TextLoader(str(database), encoding="utf-8")
		docs = loader.load()

	splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
	chunks = splitter.split_documents(docs)

	vector_store = FAISS.from_documents(chunks, embeddings)
	return vector_store.as_retriever(search_type='similarity', search_kwargs={'k':4})


@tool
def rag_tool(query: str) -> dict:

    """
    Retrieve relevant information from the pdf document.
    Use this tool when the user asks factual / conceptual questions
    that might be answered from the stored documents.
    """
    retriever = _build_retriever()
    result = retriever.invoke(query)

    context = [doc.page_content for doc in result]
    metadata = [doc.metadata for doc in result]

    return {
        'query': query,
        'context': context,
        'metadata': metadata
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

    messages = state['messages']

    response = llm_with_tools.invoke(messages)

    return {'messages': [response]}


tool_node = ToolNode(tools)
graph = StateGraph(ChatState)

graph.add_node('chat_node', chat_node)
graph.add_node('tools', tool_node)

graph.add_edge(START, 'chat_node')
graph.add_conditional_edges('chat_node', tools_condition)
graph.add_edge('tools', 'chat_node')

chatbot = graph.compile()


async def chatwithAi(user_query: str) -> str:

  query = user_query

  result = await chatbot.ainvoke(
    {
        "messages": [
            SystemMessage(content=CHAT_SYSTEM_PROMPT),
            HumanMessage(
                content=query
            )
        ]
    }
  )

  
  return result['messages'][-1].text
