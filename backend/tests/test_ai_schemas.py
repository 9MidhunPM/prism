from app.ai import PerceptionResult


def test_perception_preserves_structured_uncertainty_and_regions():
    result = PerceptionResult.model_validate({"answers": [{"question_id": "Q1", "transcription": "gradient [UNCERTAIN: decent | descent]", "confidence": 0.72, "uncertain_segments": [{"text": "decent", "alternatives": ["descent"], "confidence": 0.61}], "visual_regions": [{"kind": "diagram", "description": "downward arrow", "bbox": [0.1, 0.2, 0.4, 0.6]}], "formula_regions": []}]})
    answer = result.answers[0]
    assert answer.uncertain_segments[0].alternatives == ["descent"]
    assert answer.visual_regions[0].kind == "diagram"
