"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

TEACHER_CREDENTIALS_FILE = Path(__file__).with_name("teachers.json")
TEACHER_SESSION_COOKIE = "teacher_session"
TEACHER_SESSION_MAX_AGE = 8 * 60 * 60
PASSWORD_HASH_ITERATIONS = 600_000


class TeacherLogin(BaseModel):
    username: str
    password: str


def hash_teacher_password(password: str, salt: bytes | None = None) -> dict[str, str]:
    salt = salt or secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return {"salt": salt.hex(), "password_hash": password_hash.hex()}


def get_session_secret() -> bytes:
    secret = os.environ.get("TEACHER_SESSION_SECRET", "").encode("utf-8")
    if len(secret) < 32:
        raise HTTPException(
            status_code=503,
            detail="Teacher login is not configured. Set TEACHER_SESSION_SECRET.",
        )
    return secret


def create_teacher_session(username: str, issued_at: int | None = None) -> str:
    payload = f"{username}:{issued_at or int(time.time())}"
    encoded_payload = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    signature = hmac.new(
        get_session_secret(), encoded_payload.encode("ascii"), hashlib.sha256
    ).hexdigest()
    return f"{encoded_payload}.{signature}"


def get_teacher_from_session(request: Request) -> str | None:
    token = request.cookies.get(TEACHER_SESSION_COOKIE)
    if not token or "." not in token:
        return None

    encoded_payload, signature = token.rsplit(".", 1)
    expected_signature = hmac.new(
        get_session_secret(), encoded_payload.encode("ascii"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        padding = "=" * (-len(encoded_payload) % 4)
        payload = base64.urlsafe_b64decode(encoded_payload + padding).decode("utf-8")
        username, issued_at_text = payload.rsplit(":", 1)
        issued_at = int(issued_at_text)
    except (ValueError, UnicodeDecodeError):
        return None

    now = int(time.time())
    if not username or issued_at > now or now - issued_at > TEACHER_SESSION_MAX_AGE:
        return None

    return username


def require_teacher(request: Request) -> str:
    try:
        username = get_teacher_from_session(request)
    except HTTPException:
        username = None

    if username is None:
        raise HTTPException(
            status_code=401,
            detail="Teacher login required",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return username


def load_teacher_credentials() -> list[dict[str, str]]:
    try:
        with TEACHER_CREDENTIALS_FILE.open(encoding="utf-8") as credentials_file:
            credentials = json.load(credentials_file)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Teacher accounts are not configured. Run manage_teachers.py.",
        ) from exc
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=503, detail="Teacher accounts could not be loaded.") from exc

    if not isinstance(credentials, list):
        raise HTTPException(status_code=503, detail="Teacher accounts could not be loaded.")
    return credentials


def verify_teacher_credentials(username: str, password: str) -> bool:
    credentials = load_teacher_credentials()
    record = next(
        (teacher for teacher in credentials if teacher.get("username") == username), None
    )
    salt_text = record.get("salt", "") if record else "00" * 16
    expected_hash = record.get("password_hash", "") if record else "00" * 32

    try:
        salt = bytes.fromhex(salt_text)
        expected = bytes.fromhex(expected_hash)
    except ValueError:
        raise HTTPException(status_code=503, detail="Teacher accounts could not be loaded.")

    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return record is not None and hmac.compare_digest(actual, expected)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/me")
def get_current_teacher(request: Request):
    try:
        username = get_teacher_from_session(request)
    except HTTPException:
        username = None
    return {"authenticated": username is not None, "username": username}


@app.post("/auth/login")
def login(teacher: TeacherLogin, response: Response):
    get_session_secret()
    if not verify_teacher_credentials(teacher.username, teacher.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    response.set_cookie(
        key=TEACHER_SESSION_COOKIE,
        value=create_teacher_session(teacher.username),
        max_age=TEACHER_SESSION_MAX_AGE,
        httponly=True,
        secure=os.environ.get("TEACHER_COOKIE_SECURE", "false").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"authenticated": True, "username": teacher.username}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key=TEACHER_SESSION_COOKIE,
        httponly=True,
        secure=os.environ.get("TEACHER_COOKIE_SECURE", "false").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"authenticated": False}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, _teacher: str = Depends(require_teacher)):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str, email: str, _teacher: str = Depends(require_teacher)
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
