from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class UserRole:
    ADMIN = "admin"
    MEMBER = "member"


class TaskStatus:
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.MEMBER)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    memberships = db.relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")
    owned_projects = db.relationship("Project", back_populates="owner", foreign_keys="Project.owner_id")
    assigned_tasks = db.relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    created_tasks = db.relationship("Task", back_populates="creator", foreign_keys="Task.created_by_id")

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = db.relationship("User", back_populates="owned_projects", foreign_keys=[owner_id])
    memberships = db.relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    tasks = db.relationship("Task", back_populates="project", cascade="all, delete-orphan", order_by="desc(Task.updated_at)")

    def __repr__(self) -> str:
        return f"<Project {self.name}>"


class ProjectMember(db.Model):
    __tablename__ = "project_members"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    project = db.relationship("Project", back_populates="memberships")
    user = db.relationship("User", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<ProjectMember project={self.project_id} user={self.user_id}>"


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=TaskStatus.TODO)
    priority = db.Column(db.String(20), nullable=False, default=TaskPriority.MEDIUM)
    due_date = db.Column(db.Date, nullable=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    project = db.relationship("Project", back_populates="tasks")
    assignee = db.relationship("User", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    creator = db.relationship("User", back_populates="created_tasks", foreign_keys=[created_by_id])

    @property
    def is_overdue(self) -> bool:
        return bool(self.due_date and self.status != TaskStatus.DONE and self.due_date < datetime.utcnow().date())

    def __repr__(self) -> str:
        return f"<Task {self.title}>"
