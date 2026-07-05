from typing import List, TypedDict


class Suggestion(TypedDict, total=False):
    category: str
    title: str
    detail: str
    paragraph_index: int
    priority: str
    suggested_revision: str
    source: str


class ThesisReviewState(TypedDict, total=False):
    selected_file: str
    selected_scope: str
    selected_target_id: str
    selected_label: str
    user_goal: str
    current_text: str
    paragraphs: List[str]
    suggestions: List[Suggestion]
    summary: str
    review_source: str
    revision_summary: str
    revised_text: str
