from pydantic import BaseModel


class ReviewRequest(BaseModel):
    selected_file: str
    selected_scope: str
    selected_target_id: str = ""
    user_goal: str


class ReviewResponse(BaseModel):
    selected_label: str
    review_source: str
    summary: str
    suggestions: list[dict]
