# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teachers can sign students up for activities and unregister them
- Students can view the activity roster without signing in

## Teacher Accounts

Create or update a teacher account from the `src` directory:

```
python manage_teachers.py
```

The command stores a salted PBKDF2 password hash in `teachers.json`. That file is
ignored by Git and should remain private. Set a session-signing secret before
starting the server:

```
export TEACHER_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
uvicorn app:app --reload
```

For deployment over HTTPS, also set `TEACHER_COOKIE_SECURE=true`. The teacher
session cookie is HTTP-only, same-site strict, and expires after eight hours.

## Getting Started

1. Install the dependencies from the repository root:

   ```
   pip install -r requirements.txt
   ```

2. From the `src` directory, create a teacher account:

   ```
   python manage_teachers.py
   ```

3. From the `src` directory, set a session secret and start the server:

   ```
   export TEACHER_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
   uvicorn app:app --reload
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/auth/login`                                                      | Sign in as a teacher and set a secure session cookie                 |
| GET    | `/auth/me`                                                         | Check the current teacher session                                   |
| POST   | `/auth/logout`                                                     | End the teacher session                                             |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher-only: sign up a student                                     |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher-only: unregister a student                               |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity and registration data is stored in memory, which means it resets when
the server restarts. Teacher password hashes are stored separately in the
Git-ignored `teachers.json` file.
