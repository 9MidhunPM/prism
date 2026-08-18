from app.main import init_db, create_exam, ExamInput, QuestionInput, CriterionInput


def test_exam_totals_are_deterministic(tmp_path, monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "DB", tmp_path / "test.db")
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setattr(main, "UPLOADS", tmp_path / "uploads")
    init_db()
    exam = create_exam(ExamInput(title="T", subject="S", questions=[QuestionInput(number="Q1", text="Question", criteria=[CriterionInput(title="C", description="D", max_marks=2, concept="X")])]))
    assert exam["total_marks"] == 2
