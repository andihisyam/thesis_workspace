from langgraph.graph import END, StateGraph

from app.models.state import ThesisReviewState
from app.services.latex_structure_service import parse_latex_structure, resolve_review_unit
from app.services.llm_review_service import build_llm_suggestions, llm_review_available
from app.services.review_service import build_rule_based_suggestions, build_summary, split_paragraphs


def run_review_workflow(
    repository,
    selected_file: str,
    user_goal: str,
    selected_scope: str,
    selected_target_id: str | None = None,
) -> ThesisReviewState:
    def load_tex(state: ThesisReviewState) -> ThesisReviewState:
        current_text = repository.read_tex(state["selected_file"])
        return {**state, "current_text": current_text}

    def resolve_scope(state: ThesisReviewState) -> ThesisReviewState:
        document = parse_latex_structure(state["selected_file"], state["current_text"])
        unit = resolve_review_unit(
            document=document,
            scope_type=state["selected_scope"],
            target_id=state.get("selected_target_id"),
        )
        return {
            **state,
            "current_text": unit["raw_latex"],
            "selected_label": unit["path"],
        }

    def prepare_paragraphs(state: ThesisReviewState) -> ThesisReviewState:
        paragraphs = split_paragraphs(state["current_text"])
        return {**state, "paragraphs": paragraphs}

    def generate_suggestions(state: ThesisReviewState) -> ThesisReviewState:
        available, reason = llm_review_available()
        if available:
            try:
                suggestions, llm_summary = build_llm_suggestions(
                    state["paragraphs"],
                    user_goal=state["user_goal"],
                    context_label=state["selected_label"],
                )
                return {
                    **state,
                    "suggestions": suggestions,
                    "review_source": "openrouter",
                    "summary": llm_summary,
                }
            except Exception as exc:  # pragma: no cover - network/runtime dependent
                suggestions = build_rule_based_suggestions(
                    state["paragraphs"],
                    selected_label=state["selected_label"],
                    source_text=state["current_text"],
                )
                fallback_summary = (
                    f"Reviewer OpenRouter gagal dipakai ({exc}). Sistem beralih ke fallback lokal."
                )
                return {
                    **state,
                    "suggestions": suggestions,
                    "review_source": "rule-based",
                    "summary": fallback_summary,
                }

        suggestions = build_rule_based_suggestions(
            state["paragraphs"],
            selected_label=state["selected_label"],
            source_text=state["current_text"],
        )
        return {
            **state,
            "suggestions": suggestions,
            "review_source": f"rule-based ({reason})",
        }

    def finalize(state: ThesisReviewState) -> ThesisReviewState:
        summary = state.get("summary") or build_summary(
            state["selected_label"],
            state["suggestions"],
            state["review_source"],
        )
        return {**state, "summary": summary}

    graph = StateGraph(ThesisReviewState)
    graph.add_node("load_tex", load_tex)
    graph.add_node("resolve_scope", resolve_scope)
    graph.add_node("prepare_paragraphs", prepare_paragraphs)
    graph.add_node("generate_suggestions", generate_suggestions)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("load_tex")
    graph.add_edge("load_tex", "resolve_scope")
    graph.add_edge("resolve_scope", "prepare_paragraphs")
    graph.add_edge("prepare_paragraphs", "generate_suggestions")
    graph.add_edge("generate_suggestions", "finalize")
    graph.add_edge("finalize", END)

    workflow = graph.compile()
    return workflow.invoke(
        {
            "selected_file": selected_file,
            "selected_scope": selected_scope,
            "selected_target_id": selected_target_id or "",
            "user_goal": user_goal,
        }
    )
