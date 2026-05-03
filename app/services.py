from __future__ import annotations

from datetime import date

from flask import abort

from app.extensions import db
from app.models import Project, ProjectMember, Task, TaskPriority, TaskStatus, User


def normalize_email(value: str) -> str:
    return value.strip().lower()


def accessible_projects_query(user: User):
    if user.is_admin:
        return Project.query.order_by(Project.updated_at.desc(), Project.created_at.desc())

    return (
        Project.query.join(ProjectMember, ProjectMember.project_id == Project.id)
        .filter(ProjectMember.user_id == user.id)
        .distinct()
        .order_by(Project.updated_at.desc(), Project.created_at.desc())
    )


def accessible_projects(user: User) -> list[Project]:
    return accessible_projects_query(user).all()


def project_membership_exists(project_id: int, user_id: int) -> bool:
    return (
        db.session.query(ProjectMember.id)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
        is not None
    )


def can_access_project(user: User, project: Project) -> bool:
    return user.is_admin or project.owner_id == user.id or project_membership_exists(project.id, user.id)


def can_manage_project(user: User, project: Project) -> bool:
    return user.is_admin or project.owner_id == user.id


def get_project_or_404(user: User, project_id: int) -> Project:
    project = db.session.get(Project, project_id)
    if project is None:
        abort(404)
    if not can_access_project(user, project):
        abort(403)
    return project


def get_task_or_404(user: User, task_id: int) -> Task:
    task = db.session.get(Task, task_id)
    if task is None:
        abort(404)
    if not can_access_project(user, task.project):
        abort(403)
    return task


def serialize_user(user: User | None) -> dict | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
    }


def serialize_task(task: Task) -> dict:
    return {
        "id": task.id,
        "project_id": task.project_id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "is_overdue": task.is_overdue,
        "assignee": serialize_user(task.assignee),
        "creator": serialize_user(task.creator),
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


def serialize_project(project: Project) -> dict:
    tasks = project.tasks
    overdue_tasks = [task for task in tasks if task.is_overdue]
    completed_tasks = [task for task in tasks if task.status == TaskStatus.DONE]

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "owner": serialize_user(project.owner),
        "task_count": len(tasks),
        "completed_count": len(completed_tasks),
        "overdue_count": len(overdue_tasks),
        "progress": round((len(completed_tasks) / len(tasks)) * 100) if tasks else 0,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }


def dashboard_summary(user: User) -> dict:
    projects = accessible_projects(user)
    all_tasks = [task for project in projects for task in project.tasks]
    overdue_tasks = [task for task in all_tasks if task.is_overdue]
    active_tasks = [task for task in all_tasks if task.status in {TaskStatus.TODO, TaskStatus.IN_PROGRESS}]

    return {
        "project_count": len(projects),
        "task_count": len(all_tasks),
        "active_task_count": len(active_tasks),
        "completed_task_count": len([task for task in all_tasks if task.status == TaskStatus.DONE]),
        "overdue_count": len(overdue_tasks),
        "projects": projects,
        "recent_tasks": sorted(all_tasks, key=lambda task: task.updated_at, reverse=True)[:6],
        "overdue_tasks": sorted(overdue_tasks, key=lambda task: task.due_date or date.max)[:6],
    }


def create_project(owner: User, name: str, description: str | None) -> Project:
    project = Project(name=name.strip(), description=(description or "").strip() or None, owner_id=owner.id)
    db.session.add(project)
    db.session.flush()
    db.session.add(ProjectMember(project_id=project.id, user_id=owner.id))
    db.session.commit()
    return project


def add_member_to_project(project: Project, email: str) -> tuple[bool, str]:
    user = User.query.filter_by(email=normalize_email(email)).first()
    if user is None:
        return False, "No user matches that email yet. Ask them to sign up first."

    if project_membership_exists(project.id, user.id):
        return False, "That user is already on the team."

    db.session.add(ProjectMember(project_id=project.id, user_id=user.id))
    db.session.commit()
    return True, f"Added {user.full_name} to the team."


def remove_member_from_project(project: Project, user_id: int) -> tuple[bool, str]:
    membership = ProjectMember.query.filter_by(project_id=project.id, user_id=user_id).first()
    if membership is None:
        return False, "That member is not attached to this project."

    if project.owner_id == user_id:
        return False, "The project owner cannot be removed."

    db.session.delete(membership)
    db.session.commit()
    return True, "Team member removed."


def task_choices_for_project(project: Project) -> list[tuple[int, str]]:
    members = [membership.user for membership in project.memberships]
    members.sort(key=lambda user: user.full_name.lower())
    return [(0, "Unassigned")] + [(member.id, member.full_name) for member in members]


def create_task(project: Project, creator: User, payload: dict) -> tuple[bool, str]:
    title = (payload.get("title") or "").strip()
    if not title:
        return False, "Task title is required."

    assignee_id = payload.get("assignee_id")
    if assignee_id in {None, "", 0, "0"}:
        assignee_id = None
    else:
        assignee_id = int(assignee_id)
        if not project_membership_exists(project.id, assignee_id) and not creator.is_admin:
            return False, "Assignee must be a member of the project."

    status = payload.get("status") or TaskStatus.TODO
    if status not in {TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.DONE}:
        return False, "Invalid task status."

    priority = payload.get("priority") or TaskPriority.MEDIUM
    if priority not in {TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH}:
        return False, "Invalid task priority."

    due_date = payload.get("due_date") or None
    if due_date:
        if isinstance(due_date, str):
            due_date = date.fromisoformat(due_date)

    task = Task(
        project_id=project.id,
        title=title,
        description=(payload.get("description") or "").strip() or None,
        status=status,
        priority=priority,
        due_date=due_date,
        assignee_id=assignee_id,
        created_by_id=creator.id,
    )
    db.session.add(task)
    db.session.commit()
    return True, "Task created."


def update_task(task: Task, payload: dict) -> tuple[bool, str]:
    title = (payload.get("title") or task.title).strip()
    if not title:
        return False, "Task title is required."

    status = payload.get("status") or task.status
    if status not in {TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.DONE}:
        return False, "Invalid task status."

    priority = payload.get("priority") or task.priority
    if priority not in {TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH}:
        return False, "Invalid task priority."

    assignee_id = payload.get("assignee_id")
    if assignee_id in {None, "", 0, "0"}:
        assignee_id = None
    else:
        assignee_id = int(assignee_id)
        if not project_membership_exists(task.project_id, assignee_id):
            return False, "Assignee must be a member of the project."

    due_date = payload.get("due_date")
    if due_date == "":
        due_date = None
    elif isinstance(due_date, str):
        due_date = date.fromisoformat(due_date)

    task.title = title
    task.description = (payload.get("description") or task.description or "").strip() or None
    task.status = status
    task.priority = priority
    task.assignee_id = assignee_id
    task.due_date = due_date
    db.session.commit()
    return True, "Task updated."


def delete_task(task: Task) -> None:
    db.session.delete(task)
    db.session.commit()


def delete_project(project: Project) -> None:
    db.session.delete(project)
    db.session.commit()
