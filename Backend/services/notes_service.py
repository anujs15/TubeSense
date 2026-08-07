# services/notes_service.py

from __future__ import annotations

from datetime import date

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from dotenv import load_dotenv

from models.notes_model import  State


from utils.notes_Websearch import research_node
from utils.notes_routerSystem import router_node, route_next
from utils.notes_orchSystem import orchestrator_node
from utils.note_decideImage import decide_images, generate_and_place_images
from utils.notes_workerSystem import worker_node


load_dotenv()

# ============================================================
# Blog Writer (Router → (Research?) → Orchestrator → Workers → ReducerWithImages)
# Patches image capability using your 3-node reducer flow:
#   merge_content -> decide_images -> generate_and_place_images
# ============================================================


#llm = init_chat_model("google_genai:gemini-2.5-flash-lite", timeout=30)
llm = init_chat_model("mistralai:mistral-medium-latest", timeout=30)


def fanout(state: State):
    assert state["plan"] is not None
    return [
        Send(
            "worker",
            {
                "task": task.model_dump(),
                "topic": state["topic"],
                "mode": state["mode"],
                "as_of": state["as_of"],
                "recency_days": state["recency_days"],
                "plan": state["plan"].model_dump(),
                "evidence": [e.model_dump() for e in state.get("evidence", [])],
            },
        )
        for task in state["plan"].tasks
    ]


def merge_content(state: State) -> dict:
    plan = state["plan"]
    if plan is None:
        raise ValueError("merge_content called without plan.")
    ordered_sections = [md for _, md in sorted(state["sections"], key=lambda x: x[0])]
    body = "\n\n".join(ordered_sections).strip()
    merged_md = f"# {plan.blog_title}\n\n{body}\n"
    return {"merged_md": merged_md}



# build reducer subgraph
reducer_graph = StateGraph(State)
reducer_graph.add_node("merge_content", merge_content)
reducer_graph.add_node("decide_images", decide_images)
reducer_graph.add_node("generate_and_place_images", generate_and_place_images)
reducer_graph.add_edge(START, "merge_content")
reducer_graph.add_edge("merge_content", "decide_images")
reducer_graph.add_edge("decide_images", "generate_and_place_images")
reducer_graph.add_edge("generate_and_place_images", END)
reducer_subgraph = reducer_graph.compile()

# -----------------------------
# Build main graph
# -----------------------------
g = StateGraph(State)
g.add_node("router", router_node)
g.add_node("research", research_node)
g.add_node("orchestrator", orchestrator_node)
g.add_node("worker", worker_node)
g.add_node("reducer", reducer_subgraph)

g.add_edge(START, "router")
g.add_conditional_edges("router", route_next, {"research": "research", "orchestrator": "orchestrator"})
g.add_edge("research", "orchestrator")

g.add_conditional_edges("orchestrator", fanout, ["worker"])
g.add_edge("worker", "reducer")
g.add_edge("reducer", END)

app = g.compile()


async def run_note_writer(transcript: str) -> dict:
    """
    Run the notes writer graph with the given transcript as the topic.
    Returns the final state after execution.
    """
    if not transcript or not str(transcript).strip():
        raise ValueError("No transcript available. Analyze a video first via /youtube/analyze.")

    state = {
        "topic": transcript,
        # routing / research defaults (router_node overrides these)
        "mode": "closed_book",
        "needs_research": False,
        "queries": [],
        "evidence": [],
        "plan": None,
        # recency: as_of must be a valid ISO date for the router/research nodes
        "as_of": date.today().isoformat(),
        "recency_days": 3650,
        # worker accumulator
        "sections": [],
    }

    return await app.ainvoke(state)