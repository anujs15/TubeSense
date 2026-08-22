# services/notes_service.py

from __future__ import annotations

from datetime import date

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


async def run_note_writer(topic: str) -> dict:
    """
    Run the notes writer graph with the given topic.
    Returns the final state after execution.
    """
    if not topic or not str(topic).strip():
        raise ValueError("No topic provided. Please specify a topic for the notes writer.")

    state = {
        "topic": topic,
        "mode": "closed_book",
        "needs_research": False,
        "queries": [],
        "evidence": [],
        "plan": None,
        "as_of": date.today().isoformat(),
        "recency_days": 3650,
        "sections": [],
    }

    return await app.ainvoke(state)


async def run_note_writer_stream(topic: str):
    """
    Streaming variant of run_note_writer. Yields JSON-serializable event dicts
    as the graph makes progress, so the UI can show the outline and each section
    the moment it is ready instead of blocking ~2-3 min for the whole run.

    Event types (all fields JSON-safe):
      {"type":"stage","stage":<key>,"detail"?:<str>}         progress checkpoint
      {"type":"plan","blog_title","blog_kind","sections":[{"id","title"}]}
      {"type":"section","id","title","markdown"}             one finished section
      {"type":"final","markdown"}                            authoritative document

    This changes NO LLM call: every node runs exactly as in run_note_writer. We
    only observe LangGraph's `updates` stream. Structured-output steps
    (router/orchestrator/images) are intentionally NOT token-streamed — their
    partial JSON is useless and interleaving parallel workers is fragile. The
    win comes from the already-parallel section workers, whose updates arrive
    incrementally as each finishes (verified), plus surfacing the outline early.
    Errors are not caught here; the caller wraps them into an error event.
    """
    if not topic or not str(topic).strip():
        raise ValueError("No topic provided. Please specify a topic for the notes writer.")

    state = {
        "topic": topic,
        "mode": "closed_book",
        "needs_research": False,
        "queries": [],
        "evidence": [],
        "plan": None,
        "as_of": date.today().isoformat(),
        "recency_days": 3650,
        "sections": [],
    }

    section_titles: dict[int, str] = {}
    final_md: str | None = None

    yield {"type": "stage", "stage": "starting"}


    async for _ns, update in app.astream(state, stream_mode="updates", subgraphs=True):
        for node, delta in update.items():
            if not isinstance(delta, dict):
                continue

            if node == "router":
                if delta.get("needs_research"):
                    yield {"type": "stage", "stage": "research",
                           "detail": f"mode={delta.get('mode')}"}
                else:
                    yield {"type": "stage", "stage": "planning"}

            elif node == "research":
                ev = delta.get("evidence") or []
                yield {"type": "stage", "stage": "planning",
                       "detail": f"{len(ev)} source(s)"}

            elif node == "orchestrator":
                plan = delta.get("plan")
                if plan is not None:
                    for t in plan.tasks:
                        section_titles[t.id] = t.title
                    yield {
                        "type": "plan",
                        "blog_title": plan.blog_title,
                        "blog_kind": plan.blog_kind,
                        "sections": [{"id": t.id, "title": t.title} for t in plan.tasks],
                    }

            elif node == "worker":
                for item in delta.get("sections") or []:
                    try:
                        sid, md = item
                    except (TypeError, ValueError):
                        continue
                    yield {"type": "section", "id": sid,
                           "title": section_titles.get(sid), "markdown": md}

            elif node == "merge_content":
                yield {"type": "stage", "stage": "assembling"}

            elif node == "decide_images":
                specs = delta.get("image_specs") or []
                if specs:
                    yield {"type": "stage", "stage": "images",
                           "detail": f"{len(specs)} image(s)"}
                else:
                    yield {"type": "stage", "stage": "finalizing"}

            elif node in ("generate_and_place_images", "reducer"):
                fm = delta.get("final")
                if fm:
                    final_md = fm

    yield {"type": "final", "markdown": final_md or ""}