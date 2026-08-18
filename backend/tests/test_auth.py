from fastapi import HTTPException, Response

from app.auth import token_hash
from app.main import TeacherCredentials, bootstrap_teacher, current_account, current_student, current_teacher, login, logout, own_submission, own_submissions, set_session
from app.models import Account, AccountRole, AuthSession, ClassCohort, Exam, Student, Submission
from datetime import datetime, timezone
from app.demo import seed_demo_accounts
from app.settings import Settings
from app import database


def test_teacher_bootstrap_and_login_create_valid_session(isolated_database):
    import app.main as main

    bootstrap_response = Response()
    teacher = bootstrap_teacher(TeacherCredentials(name="A Teacher", email="Teacher@example.com", password="a-secure-password"), bootstrap_response)
    token = bootstrap_response.headers["set-cookie"].split("prism_session=", 1)[1].split(";", 1)[0]
    with database.SessionLocal() as db:
        auth_session = db.query(AuthSession).filter_by(token_hash=token_hash(token)).one()
        assert auth_session.account_id == current_account(token)["id"]
        assert auth_session.revoked_at is None
    assert current_teacher(current_account(token))["email"] == "teacher@example.com"

    login_response = Response()
    logged_in = login(TeacherCredentials(email="teacher@example.com", password="a-secure-password"), login_response)
    assert logged_in["id"] == teacher["id"]
    assert logged_in["role"] == "teacher"

    logout(Response(), token)
    try:
        current_account(token)
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("A logged out token must not remain usable.")


def test_teacher_bootstrap_is_available_only_once(isolated_database):
    bootstrap_teacher(TeacherCredentials(name="A Teacher", email="teacher@example.com", password="a-secure-password"), Response())

    try:
        bootstrap_teacher(TeacherCredentials(name="Another Teacher", email="other@example.com", password="another-secure-password"), Response())
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Bootstrap must be unavailable after the first teacher is created.")


def test_student_session_cannot_resolve_a_teacher_identity(isolated_database):
    import app.main as main

    teacher = bootstrap_teacher(TeacherCredentials(name="A Teacher", email="teacher@example.com", password="a-secure-password"), Response())
    with database.SessionLocal() as db:
        cohort = ClassCohort(teacher_id=teacher["id"], name="Class A")
        db.add(cohort); db.flush()
        student = Student(class_id=cohort.id, name="A Student", identifier="S-1")
        db.add(student); db.flush()
        other_student = Student(class_id=cohort.id, name="Another Student", identifier="S-2")
        db.add(other_student); db.flush()
        exam = Exam(teacher_id=teacher["id"], title="Assessment", subject="Math", total_marks=1)
        db.add(exam); db.flush()
        own = Submission(exam_id=exam.id, student_id=student.id, released_at=datetime.now(timezone.utc))
        other = Submission(exam_id=exam.id, student_id=other_student.id)
        db.add_all([own, other])
        account = Account(email="student@example.com", password_hash="not-used", role=AccountRole.STUDENT, student_id=student.id)
        db.add(account); db.commit()
        response = Response()
        set_session(response, account)
        token = response.headers["set-cookie"].split("prism_session=", 1)[1].split(";", 1)[0]

    student_identity = current_student(current_account(token))
    assert student_identity["id"] == student.id
    assert [submission["id"] for submission in own_submissions(student_identity)] == [own.id]
    try:
        own_submission(other.id, student_identity)
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("A student must not retrieve another student's result.")
    try:
        current_teacher(current_account(token))
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("A student session must not access teacher routes.")


def test_demo_seed_is_idempotent_and_uses_configured_credentials(isolated_database):
    settings = Settings(
        demo_mode=True,
        demo_teacher_name="Demo Teacher",
        demo_teacher_email="demo-teacher@example.com",
        demo_teacher_password="demo-teacher-password",
        demo_student_name="Demo Student",
        demo_student_email="demo-student@example.com",
        demo_student_password="demo-student-password",
    )
    first = seed_demo_accounts(settings)
    second = seed_demo_accounts(settings)
    assert first["status"] == second["status"] == "seeded"
    with database.SessionLocal() as db:
        assert db.query(Account).count() == 2
