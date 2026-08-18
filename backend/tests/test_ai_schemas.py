from app.ai import ExamImportResult, PerceptionResult
from app.main import imported_draft


def test_perception_preserves_structured_uncertainty_and_regions():
    result = PerceptionResult.model_validate({"answers": [{"question_id": "Q1", "mapping_basis": "visible_identifier", "mapping_confidence": 0.96, "sequence": 1, "transcription": "gradient [UNCERTAIN: decent | descent]", "confidence": 0.72, "uncertain_segments": [{"text": "decent", "alternatives": ["descent"], "confidence": 0.61}], "visual_regions": [{"kind": "diagram", "description": "downward arrow", "bbox": [0.1, 0.2, 0.4, 0.6]}], "formula_regions": []}]})
    answer = result.answers[0]
    assert answer.uncertain_segments[0].alternatives == ["descent"]
    assert answer.visual_regions[0].kind == "diagram"


def test_perception_allows_an_unmapped_or_continued_fragment():
    result = PerceptionResult.model_validate({"answers": [{"question_id": None, "mapping_basis": "unknown", "mapping_confidence": 0.2, "sequence": 1, "transcription": "continued working", "confidence": 0.9}]})
    assert result.answers[0].question_id is None
    assert result.answers[0].mapping_basis == "unknown"


def test_exam_import_draft_warns_when_rubric_marks_do_not_match_visible_marks():
    result = ExamImportResult.model_validate({"title": "Science quiz", "subject": "Science", "questions": [{"number": "Q1", "text": "Explain photosynthesis.", "max_marks": 5, "confidence": 0.81, "criteria": [{"title": "Inputs", "description": "Names inputs.", "max_marks": 2, "concept": "Photosynthesis"}, {"title": "Process", "description": "Explains process.", "max_marks": 2, "concept": "Photosynthesis"}]}]})
    draft = imported_draft(result)
    assert draft["questions"][0]["max_marks"] == 5
    assert "criteria total 4, but the paper shows 5 marks" in draft["warnings"][0]
