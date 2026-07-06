from app.services.review_service import build_rule_based_suggestions


def test_rule_based_review_flags_missing_citation() -> None:
    paragraphs = ["Ini adalah paragraf yang sangat panjang " * 12]

    suggestions = build_rule_based_suggestions(paragraphs)

    assert any(item["category"] == "citation-gap" for item in suggestions)


def test_rule_based_review_returns_healthy_draft_for_short_text() -> None:
    suggestions = build_rule_based_suggestions(["Kalimat singkat dan jelas."])

    assert len(suggestions) == 1
    assert suggestions[0]["category"] == "healthy-draft"
    assert suggestions[0]["source"] == "rule-based"
