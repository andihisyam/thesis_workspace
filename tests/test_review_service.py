from app.services.review_service import analyze_paragraphs


def test_analyze_paragraphs_flags_missing_citation() -> None:
    paragraphs = [
        "Ini adalah paragraf yang sangat panjang " * 12,
    ]

    suggestions = analyze_paragraphs(paragraphs)

    assert any(item["category"] == "citation-gap" for item in suggestions)
