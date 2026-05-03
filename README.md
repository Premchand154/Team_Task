# Team Task Manager

A full-featured task management application with user authentication, role-based access control, team collaboration, and comprehensive dashboard analytics. Built with Flask and SQLAlchemy.

**Live Demo:** https://web-production-81f2e.up.railway.app

## Overview

Team Task Manager allows users to organize projects, assign tasks, and track progress collaboratively. The first registered user becomes an Admin with full control; subsequent users join as Members and can be assigned to projects.

## Features

- **Authentication & Authorization**
  - User signup and login with secure session management
  - First user automatically becomes Admin
  - Role-based access control (Admin and Member roles)
  - Login required for task and project operations

- **Project Management**
  - Create and manage projects
  - Add/remove team members from projects
  - Track project ownership and membership

- **Task Management**
  - Create, update, and delete tasks within projects
  - Assign tasks to team members
  - Set task status (todo, in_progress, completed)
  - Set task priority (low, medium, high)
  - Track due dates
  - View task assignments and history

- **Dashboard & Analytics**
  - Overview of all tasks (assigned, pending, completed)
  - Progress metrics per project
  - Overdue task tracking
  - Completion statistics

- **REST API**
  - Full REST API under `/api` for programmatic access
  - JSON request/response format
  - Session-based authentication for API requests

- **Database**
  - SQLite for local development
  - PostgreSQL for production (Railway)
  - SQLAlchemy ORM with automatic schema creation

## Tech Stack

- **Backend:** Flask 3.1, Flask-Login, Flask-SQLAlchemy, Flask-WTF
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Forms:** WTForms with email-validator
- **Server:** Gunicorn WSGI
- **Deployment:** Railway.app
- **ORM:** SQLAlchemy 2.0

## Project Structure

```
Team_Task/
├── app/
│   ├── __init__.py          # Flask app factory, DB init
│   ├── extensions.py        # Flask extensions (db, login_manager, csrf)
│   ├── models.py            # User, Project, Task, Member models
│   ├── views.py             # Web and API blueprints
│   ├── forms.py             # WTForms (Login, Signup, Project, Task)
│   ├── services.py          # Business logic (project, task, auth)
│   ├── static/
│   │   └── css/style.css    # Stylesheet
│   └── templates/
│       ├── base.html        # Base template
│       ├── dashboard.html   # Dashboard view
│       ├── auth/
│       │   ├── login.html
│       │   └── signup.html
│       └── projects/
│           ├── index.html
│           └── detail.html
├── instance/                # Instance folder (SQLite DB, .env)
├── requirements.txt         # Python dependencies
├── wsgi.py                  # WSGI entry point for Gunicorn
├── Procfile                 # Railway deployment config
└── .env.example             # Environment variables template
```

## Local Setup

### Prerequisites

- Python 3.10+
- pip or venv

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/Premchand154/Team_Task.git
   cd Team_Task
   ```

2. Create and activate a virtual environment
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment
   ```bash
   cp .env.example .env
   # Edit .env and set SECRET_KEY to a random string
   echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env
   ```

5. Run the development server
   ```bash
   python -m flask --app wsgi run
   ```

6. Open http://localhost:5000 in your browser

### Database

The app auto-creates the database and tables on first run. For SQLite (dev), the database is stored at `instance/team_task.db`.

To reset the database:
```bash
rm instance/team_task.db
python -m flask --app wsgi run  # Recreates schema
```

## Railway Deployment

This app is configured for one-click deployment to Railway.

### Prerequisites

- GitHub repository (push this code)
- Railway account (free tier available)

### Steps

1. **Create Railway Project**
   - Go to [railway.app](https://railway.app) and sign in
   - Click "New Project" → "Deploy from GitHub repo"
   - Select this repository

2. **Add PostgreSQL Service**
   - Click "Add Service" in Railway
   - Select "PostgreSQL"
   - Railway will automatically create the service

3. **Configure Environment Variables**
   - In Railway project dashboard, go to your app service → "Variables"
   - Add:
     - `SECRET_KEY`: Generate a random 64-character hex string
       ```bash
       python -c "import secrets; print(secrets.token_hex(32))"
       ```
     - `DATABASE_URL`: Automatically injected from PostgreSQL service

4. **Verify Deployment**
   - Railway auto-detects the `Procfile` and runs: `gunicorn --bind 0.0.0.0:${PORT:-8000} wsgi:app`
   - Check Deployment logs for any errors
   - Once "SUCCESS", your app is live at the provided Railway domain

### Important Notes

- Railway automatically injects `PORT` and `DATABASE_URL` environment variables
- The app normalizes PostgreSQL URLs: both `postgres://` and `postgresql://` are converted to `postgresql+psycopg://` for psycopg3 compatibility
- First user to sign up becomes Admin automatically
- Subsequent users join as Members

## API Documentation

All endpoints require session authentication (cookie-based).

### Authentication

#### Sign Up
```
POST /api/auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}

Response (201):
{
  "user_id": 1,
  "email": "user@example.com",
  "role": "admin"
}
```

#### Log In
```
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}

Response (200):
{
  "user_id": 1,
  "email": "user@example.com",
  "role": "admin"
}
```

### Projects

#### List Projects
```
GET /api/projects

Response (200):
[
  {
    "id": 1,
    "name": "Marketing Campaign",
    "description": "Q2 marketing launch",
    "owner_id": 1,
    "members": [
      {"id": 1, "email": "admin@example.com", "role": "member"},
      {"id": 2, "email": "user@example.com", "role": "member"}
    ]
  }
]
```

#### Create Project
```
POST /api/projects
Content-Type: application/json

{
  "name": "Marketing Launch",
  "description": "Prepare campaign assets and launch checklist."
}

Response (201):
{
  "id": 1,
  "name": "Marketing Launch",
  "description": "Prepare campaign assets and launch checklist.",
  "owner_id": 1,
  "members": []
}
```

#### Get Project
```
GET /api/projects/1

Response (200):
{
  "id": 1,
  "name": "Marketing Launch",
  "description": "Prepare campaign assets and launch checklist.",
  "owner_id": 1,
  "members": [...]
}
```

#### Update Project
```
PUT /api/projects/1
Content-Type: application/json

{
  "name": "Updated Project Name",
  "description": "Updated description"
}

Response (200): [Updated project object]
```

#### Delete Project
```
DELETE /api/projects/1

Response (204): No content
```

### Tasks

#### Create Task
```
POST /api/projects/1/tasks
Content-Type: application/json

{
  "title": "Design landing page",
  "description": "Draft hero section and CTA.",
  "assignee_id": 2,
  "status": "in_progress",
  "priority": "high",
  "due_date": "2026-05-10"
}

Response (201):
{
  "id": 1,
  "project_id": 1,
  "title": "Design landing page",
  "description": "Draft hero section and CTA.",
  "assignee_id": 2,
  "status": "in_progress",
  "priority": "high",
  "due_date": "2026-05-10",
  "created_at": "2026-05-03T10:00:00Z",
  "updated_at": "2026-05-03T10:00:00Z"
}
```

#### List Tasks (Project)
```
GET /api/projects/1/tasks

Response (200):
[
  {
    "id": 1,
    "project_id": 1,
    "title": "Design landing page",
    ...
  }
]
```

#### Update Task
```
PUT /api/projects/1/tasks/1
Content-Type: application/json

{
  "status": "completed",
  "priority": "medium"
}

Response (200): [Updated task object]
```

#### Delete Task
```
DELETE /api/projects/1/tasks/1

Response (204): No content
```

### Members

#### Add Member to Project
```
POST /api/projects/1/members
Content-Type: application/json

{
  "email": "newmember@example.com"
}

Response (201):
{
  "user_id": 3,
  "email": "newmember@example.com",
  "role": "member"
}
```

#### Remove Member from Project
```
DELETE /api/projects/1/members/3

Response (204): No content
```

## Error Responses

All endpoints return standard HTTP status codes:

- `200 OK`: Successful GET or PUT
- `201 Created`: Successful POST
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Invalid input (e.g., missing required field)
- `401 Unauthorized`: Not logged in
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include a JSON object:
```json
{
  "error": "Description of the error"
}
```

## Models

### User
- `id`: Integer (PK)
- `email`: String, unique
- `password_hash`: Hashed password
- `role`: Admin or Member
- `created_at`: Timestamp

### Project
- `id`: Integer (PK)
- `name`: String
- `description`: Text
- `owner_id`: Foreign key → User
- `created_at`: Timestamp
- `updated_at`: Timestamp

### Task
- `id`: Integer (PK)
- `project_id`: Foreign key → Project
- `title`: String
- `description`: Text
- `assignee_id`: Foreign key → User (nullable)
- `status`: todo, in_progress, completed
- `priority`: low, medium, high
- `due_date`: Date (nullable)
- `created_at`: Timestamp
- `updated_at`: Timestamp

### ProjectMember
- `id`: Integer (PK)
- `project_id`: Foreign key → Project
- `user_id`: Foreign key → User
- `role`: admin or member (within project)
- `joined_at`: Timestamp

## Environment Variables

### Required
- `SECRET_KEY`: Flask secret key for session encryption

### Optional (Auto-set in Railway)
- `DATABASE_URL`: PostgreSQL connection string
- `PORT`: Server port (default: 8000 for Railway, 5000 for local)

### Example `.env` (Local Development)
```
SECRET_KEY=your-secret-key-here-minimum-32-chars
DATABASE_URL=sqlite:///team_task.db
```

## Development

### Running Tests
```bash
python -m pytest
```

### Code Style
- Python 3.10+
- Follow PEP 8
- Type hints recommended

### Database Migrations
For schema changes, currently using SQLAlchemy's `db.create_all()` on app startup. For production, consider using Alembic for migration management.

## Troubleshooting

### PostgreSQL Connection Error (psycopg2 not found)
**Cause:** SQLAlchemy is looking for psycopg2 instead of psycopg3
**Solution:** Ensure `DATABASE_URL` is normalized to `postgresql+psycopg://...` (not `postgres://`)

### First User Not Admin
**Cause:** Role not properly set on signup
**Check:** Verify `services.py` sets role to `UserRole.ADMIN` for first user

### CSRF Token Missing
**Cause:** Form submission without CSRF token
**Solution:** All forms in templates include `{{ csrf_token() }}` hidden field

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

For issues, questions, or suggestions, please open a GitHub issue.
