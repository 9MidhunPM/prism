from fastapi import HTTPException, Response

from app.auth import read_session
from app.main import TeacherCredentials, bootstrap_teacher, current_teacher, init_db, login


def test_teacher_bootstrap_and_login_create_valid_session(tmp_path, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "DB", tmp_path / "test.db")
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setattr(main, "UPLOADS", tmp_path / "uploads")
    init_db()

    bootstrap_response = Response()
    teacher = bootstrap_teacher(TeacherCredentials(name="A Teacher", email="Teacher@example.com", password="a-secure-password"), bootstrap_response)
    token = bootstrap_response.headers["set-cookie"].split("prism_session=", 1)[1].split(";", 1)[0]
    assert read_session(token, main.settings.session_secret.get_secret_value()) == teacher["id"]
    assert current_teacher(token)["email"] == "teacher@example.com"

    login_response = Response()
    logged_in = login(TeacherCredentials(email="teacher@example.com", password="a-secure-password"), login_response)
    assert logged_in["id"] == teacher["id"]


def test_teacher_bootstrap_is_available_only_once(tmp_path, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "DB", tmp_path / "test.db")
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setattr(main, "UPLOADS", tmp_path / "uploads")
    init_db()
    bootstrap_teacher(TeacherCredentials(name="A Teacher", email="teacher@example.com", password="a-secure-password"), Response())

    try:
        bootstrap_teacher(TeacherCredentials(name="Another Teacher", email="other@example.com", password="another-secure-password"), Response())
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Bootstrap must be unavailable after the first teacher is created.")
