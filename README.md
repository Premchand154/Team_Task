# Team Task Manager

Full-stack task management app with authentication, role-based access control, project/team management, task assignment, and a dashboard for progress tracking.

## Features

- Signup and login with session auth
- First user becomes Admin automatically
- Admin and Member roles
- Project creation and team member management
- Task creation, assignment, status, priority, and due dates
- Dashboard metrics for tasks, progress, and overdue items
- REST API under `/api`
- PostgreSQL-ready for Railway deployment

## Local setup

1. Copy `.env.example` to `.env` and set `SECRET_KEY`.
2. Install dependencies with `pip install -r requirements.txt`.
3. Run the app with `gunicorn wsgi:app` or `python -m flask --app wsgi run`.

## Railway deployment

1. Push the repository to GitHub.
2. Create a new Railway project from the repo.
3. Add a PostgreSQL plugin in Railway.
4. Set `SECRET_KEY` and `DATABASE_URL` in Railway variables.
5. Use `gunicorn wsgi:app` as the start command if Railway does not detect it automatically.

## API examples

### Create project

```bash
POST /api/projects
{
  "name": "Marketing Launch",
  "description": "Prepare campaign assets and launch checklist."
}
```

### Create task

```bash
POST /api/projects/1/tasks
{
  "title": "Design landing page",
  "description": "Draft hero section and CTA.",
  "assignee_id": 2,
  "status": "in_progress",
  "priority": "high",
  "due_date": "2026-05-10"
}
```
