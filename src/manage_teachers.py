"""Create or update a local teacher account without storing a plaintext password."""

import json
import os
from getpass import getpass

from app import TEACHER_CREDENTIALS_FILE, hash_teacher_password


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username or any(character.isspace() for character in username):
        raise SystemExit("Username must be non-empty and contain no spaces.")

    password = getpass("Teacher password (minimum 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")

    credentials: list[dict[str, str]] = []
    if TEACHER_CREDENTIALS_FILE.exists():
        try:
            data = json.loads(TEACHER_CREDENTIALS_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
                raise ValueError
            credentials = data
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            raise SystemExit("Existing teacher account file is invalid; no changes made.") from exc

    credentials = [item for item in credentials if item.get("username") != username]
    credentials.append({"username": username, **hash_teacher_password(password)})

    TEACHER_CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEACHER_CREDENTIALS_FILE.write_text(
        json.dumps(credentials, indent=2) + "\n", encoding="utf-8"
    )
    if os.name == "posix":
        TEACHER_CREDENTIALS_FILE.chmod(0o600)

    print(f"Teacher account '{username}' saved.")


if __name__ == "__main__":
    main()