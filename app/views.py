from __future__ import annotations

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.forms import LoginForm, MemberForm, ProjectForm, SignupForm, TaskForm
from app.models import TaskStatus, User, UserRole
from app.services import (
    accessible_projects,
    add_member_to_project,
    can_manage_project,
    create_project,
    create_task,
    dashboard_summary,
    delete_project,
    delete_task,
    get_project_or_404,
    get_task_or_404,
    normalize_email,
    project_membership_exists,
    remove_member_from_project,
    serialize_project,
    serialize_task,
    serialize_user,
    task_choices_for_project,
    update_task,
)


auth_bp = Blueprint("auth", __name__)
web_bp = Blueprint("web", __name__)
api_bp = Blueprint("api", __name__)


def _json_error(message: str, status_code: int = 400):
    return jsonify({"error": message}), status_code


def _json_ok(payload: dict, status_code: int = 200):
    return jsonify(payload), status_code


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("web.dashboard"))

    form = SignupForm()
    if form.validate_on_submit():
        email = normalize_email(form.email.data)
        existing_user = User.query.filter_by(email=email).first()
        if existing_user is not None:
            form.email.errors.append("That email is already registered.")
        else:
            role = UserRole.ADMIN if User.query.count() == 0 else UserRole.MEMBER
            user = User(
                full_name=form.full_name.data.strip(),
                email=email,
                role=role,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Account created. You are now signed in.", "success")
            return redirect(url_for("web.dashboard"))

    return render_template("auth/signup.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("web.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = normalize_email(form.email.data)
        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(form.password.data):
            form.password.errors.append("Invalid email or password.")
        else:
            login_user(user)
            flash("Welcome back.", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("web.dashboard"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@web_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("web.dashboard"))
    return redirect(url_for("auth.login"))


@web_bp.route("/dashboard")
@login_required
def dashboard():
    summary = dashboard_summary(current_user)
    return render_template("dashboard.html", summary=summary)


@web_bp.route("/projects", methods=["GET", "POST"])
@login_required
def projects():
    form = ProjectForm()
    if form.validate_on_submit():
        create_project(current_user, form.name.data, form.description.data)
        flash("Project created.", "success")
        return redirect(url_for("web.projects"))

    projects_list = accessible_projects(current_user)
    return render_template("projects/index.html", projects=projects_list, form=form)


@web_bp.route("/projects/<int:project_id>")
@login_required
def project_detail(project_id: int):
    project = get_project_or_404(current_user, project_id)
    members = [membership.user for membership in project.memberships]
    members.sort(key=lambda user: user.full_name.lower())

    task_form = TaskForm()
    task_form.assignee_id.choices = task_choices_for_project(project)
    task_form.status.data = TaskStatus.TODO
    task_form.priority.data = "medium"

    member_form = MemberForm()
    return render_template(
        "projects/detail.html",
        project=project,
        members=members,
        task_form=task_form,
        member_form=member_form,
        can_manage=can_manage_project(current_user, project),
    )


@web_bp.route("/projects/<int:project_id>/tasks", methods=["POST"])
@login_required
def create_project_task(project_id: int):
    project = get_project_or_404(current_user, project_id)
    form = TaskForm()
    form.assignee_id.choices = task_choices_for_project(project)

    if form.validate_on_submit():
        success, message = create_task(
            project,
            current_user,
            {
                "title": form.title.data,
                "description": form.description.data,
                "assignee_id": form.assignee_id.data,
                "status": form.status.data,
                "priority": form.priority.data,
                "due_date": form.due_date.data.isoformat() if form.due_date.data else None,
            },
        )
        flash(message, "success" if success else "danger")
    else:
        flash("Please correct the task form errors.", "danger")

    return redirect(url_for("web.project_detail", project_id=project.id))


@web_bp.route("/projects/<int:project_id>/members", methods=["POST"])
@login_required
def add_project_member(project_id: int):
    project = get_project_or_404(current_user, project_id)
    if not can_manage_project(current_user, project):
        abort(403)

    form = MemberForm()
    if form.validate_on_submit():
        success, message = add_member_to_project(project, form.email.data)
        flash(message, "success" if success else "danger")
    else:
        flash("Please provide a valid email address.", "danger")

    return redirect(url_for("web.project_detail", project_id=project.id))


@web_bp.route("/projects/<int:project_id>/members/<int:user_id>/remove", methods=["POST"])
@login_required
def remove_project_member(project_id: int, user_id: int):
    project = get_project_or_404(current_user, project_id)
    if not can_manage_project(current_user, project):
        abort(403)

    success, message = remove_member_from_project(project, user_id)
    flash(message, "success" if success else "danger")
    return redirect(url_for("web.project_detail", project_id=project.id))


@web_bp.route("/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project_route(project_id: int):
    project = get_project_or_404(current_user, project_id)
    if not can_manage_project(current_user, project):
        abort(403)

    delete_project(project)
    flash("Project deleted.", "info")
    return redirect(url_for("web.projects"))


@web_bp.route("/tasks/<int:task_id>/update", methods=["POST"])
@login_required
def update_task_route(task_id: int):
    task = get_task_or_404(current_user, task_id)
    if not can_manage_project(current_user, task.project) and not project_membership_exists(task.project_id, current_user.id):
        abort(403)

    success, message = update_task(
        task,
        {
            "title": request.form.get("title"),
            "description": request.form.get("description"),
            "assignee_id": request.form.get("assignee_id"),
            "status": request.form.get("status"),
            "priority": request.form.get("priority"),
            "due_date": request.form.get("due_date"),
        },
    )
    flash(message, "success" if success else "danger")
    return redirect(url_for("web.project_detail", project_id=task.project_id))


@web_bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task_route(task_id: int):
    task = get_task_or_404(current_user, task_id)
    if not can_manage_project(current_user, task.project) and not project_membership_exists(task.project_id, current_user.id):
        abort(403)

    project_id = task.project_id
    delete_task(task)
    flash("Task deleted.", "info")
    return redirect(url_for("web.project_detail", project_id=project_id))


@api_bp.route("/auth/signup", methods=["POST"])
def api_signup():
    payload = request.get_json(silent=True) or {}
    full_name = (payload.get("full_name") or "").strip()
    email = normalize_email(payload.get("email") or "")
    password = payload.get("password") or ""

    if len(full_name) < 2:
        return _json_error("Full name is required.")
    if "@" not in email:
        return _json_error("A valid email address is required.")
    if len(password) < 8:
        return _json_error("Password must be at least 8 characters long.")
    if User.query.filter_by(email=email).first() is not None:
        return _json_error("That email is already registered.", 409)

    role = UserRole.ADMIN if User.query.count() == 0 else UserRole.MEMBER
    user = User(full_name=full_name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return _json_ok({"user": serialize_user(user)}, 201)


@api_bp.route("/auth/login", methods=["POST"])
def api_login():
    payload = request.get_json(silent=True) or {}
    email = normalize_email(payload.get("email") or "")
    password = payload.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return _json_error("Invalid email or password.", 401)

    login_user(user)
    return _json_ok({"user": serialize_user(user)})


@api_bp.route("/auth/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return _json_ok({"message": "Logged out."})


@api_bp.route("/me", methods=["GET"])
@login_required
def api_me():
    return _json_ok({"user": serialize_user(current_user)})


@api_bp.route("/dashboard", methods=["GET"])
@login_required
def api_dashboard():
    summary = dashboard_summary(current_user)
    return _json_ok(
        {
            "project_count": summary["project_count"],
            "task_count": summary["task_count"],
            "active_task_count": summary["active_task_count"],
            "completed_task_count": summary["completed_task_count"],
            "overdue_count": summary["overdue_count"],
            "projects": [serialize_project(project) for project in summary["projects"]],
            "recent_tasks": [serialize_task(task) for task in summary["recent_tasks"]],
            "overdue_tasks": [serialize_task(task) for task in summary["overdue_tasks"]],
        }
    )


@api_bp.route("/projects", methods=["GET", "POST"])
@login_required
def api_projects():
    if request.method == "GET":
        return _json_ok({"projects": [serialize_project(project) for project in accessible_projects(current_user)]})

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if len(name) < 3:
        return _json_error("Project name is required.")

    project = create_project(current_user, name, payload.get("description"))
    return _json_ok({"project": serialize_project(project)}, 201)


@api_bp.route("/projects/<int:project_id>", methods=["GET", "PATCH", "DELETE"])
@login_required
def api_project_detail(project_id: int):
    project = get_project_or_404(current_user, project_id)

    if request.method == "GET":
        members = [serialize_user(membership.user) for membership in project.memberships]
        return _json_ok(
            {
                "project": serialize_project(project),
                "members": members,
                "tasks": [serialize_task(task) for task in project.tasks],
            }
        )

    if request.method == "DELETE":
        if not can_manage_project(current_user, project):
            return _json_error("You do not have permission to delete this project.", 403)
        delete_project(project)
        return _json_ok({"message": "Project deleted."})

    payload = request.get_json(silent=True) or {}
    if not can_manage_project(current_user, project):
        return _json_error("You do not have permission to update this project.", 403)

    name = (payload.get("name") or project.name).strip()
    if len(name) < 3:
        return _json_error("Project name is required.")

    project.name = name
    project.description = (payload.get("description") or project.description or "").strip() or None
    db.session.commit()
    return _json_ok({"project": serialize_project(project)})


@api_bp.route("/projects/<int:project_id>/members", methods=["POST"])
@login_required
def api_add_member(project_id: int):
    project = get_project_or_404(current_user, project_id)
    if not can_manage_project(current_user, project):
        return _json_error("You do not have permission to manage this team.", 403)

    payload = request.get_json(silent=True) or {}
    success, message = add_member_to_project(project, payload.get("email") or "")
    status_code = 200 if success else 400
    return _json_ok({"message": message}, status_code)


@api_bp.route("/projects/<int:project_id>/members/<int:user_id>", methods=["DELETE"])
@login_required
def api_remove_member(project_id: int, user_id: int):
    project = get_project_or_404(current_user, project_id)
    if not can_manage_project(current_user, project):
        return _json_error("You do not have permission to manage this team.", 403)

    success, message = remove_member_from_project(project, user_id)
    status_code = 200 if success else 400
    return _json_ok({"message": message}, status_code)


@api_bp.route("/projects/<int:project_id>/tasks", methods=["GET", "POST"])
@login_required
def api_tasks(project_id: int):
    project = get_project_or_404(current_user, project_id)
    if request.method == "GET":
        return _json_ok({"tasks": [serialize_task(task) for task in project.tasks]})

    payload = request.get_json(silent=True) or {}
    success, message = create_task(project, current_user, payload)
    if not success:
        return _json_error(message)

    created_task = project.tasks[0] if project.tasks else None
    return _json_ok(
        {
            "message": message,
            "task": serialize_task(created_task) if created_task else None,
        },
        201,
    )


@api_bp.route("/tasks/<int:task_id>", methods=["PATCH", "DELETE"])
@login_required
def api_task_detail(task_id: int):
    task = get_task_or_404(current_user, task_id)
    if request.method == "DELETE":
        if not can_manage_project(current_user, task.project) and not project_membership_exists(task.project_id, current_user.id):
            return _json_error("You do not have permission to delete this task.", 403)
        delete_task(task)
        return _json_ok({"message": "Task deleted."})

    payload = request.get_json(silent=True) or {}
    if not can_manage_project(current_user, task.project) and not project_membership_exists(task.project_id, current_user.id):
        return _json_error("You do not have permission to update this task.", 403)

    success, message = update_task(task, payload)
    if not success:
        return _json_error(message)
    return _json_ok({"message": message, "task": serialize_task(task)})
