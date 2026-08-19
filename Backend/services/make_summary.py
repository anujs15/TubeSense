#services/make_summary.py

from __future__ import annotations
import operator
from typing import Annotated, List, TypedDict
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from dotenv import load_dotenv
from pydantic import BaseModel
from llm_config import make_chat_model

load_dotenv()

class StrOutput(BaseModel):
      content: str

model = make_chat_model()

llm= model.with_structured_output(StrOutput)


class OverallState(TypedDict):
    texts: List[str] 
    summaries: Annotated[List[str], operator.add] 
    final_summary: str

class MapState(TypedDict):
    text: str 


def generate_chunk_summaries(state: MapState):
    """Map Step: Summarize a single chunk of the transcript."""

    prompt = ChatPromptTemplate.from_template(
        "Summarize the following portion of a video transcript concisely:\n\n{text}"
    )
    chain = prompt | llm
    response = chain.invoke({"text": state["text"]})
    
    return {"summaries": [response.content]}


def map_summaries(state: OverallState):
    """Fan-out Step: Send each chunk to the summary node in parallel."""
    return [Send("generate_chunk_summaries", {"text": text}) for text in state["texts"]]


def generate_final_summary(state: OverallState):
    """Reduce Step: Combine all chunk summaries into one final summary."""
    prompt = ChatPromptTemplate.from_template(
        "The following are chronological summaries of parts of a video. "
        "Combine them into one cohesive, comprehensive final summary:\n\n{summaries}"
    )
    chain = prompt | llm
    
    joined_summaries = "\n\n".join(state["summaries"])
    response = chain.invoke({"summaries": joined_summaries})
    
    return {"final_summary": response.content}


graph = StateGraph(OverallState)

graph.add_node("generate_chunk_summaries", generate_chunk_summaries)
graph.add_node("generate_final_summary", generate_final_summary)

graph.add_conditional_edges(START, map_summaries, ["generate_chunk_summaries"])

graph.add_edge("generate_chunk_summaries", "generate_final_summary")

graph.add_edge("generate_final_summary", END)

app = graph.compile()



def summarize_transcript(transcript: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=10000, 
        chunk_overlap=500
    )
    chunks = splitter.split_text(transcript)
    

    result = app.invoke({"texts": chunks, "summaries": []})
    
    return result["final_summary"]
