from flask_wtf import FlaskForm
from wtforms import DateField, PasswordField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class SignupForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired()])


class ProjectForm(FlaskForm):
    name = StringField("Project name", validators=[DataRequired(), Length(min=3, max=120)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=4000)])


class TaskForm(FlaskForm):
    title = StringField("Task title", validators=[DataRequired(), Length(min=3, max=160)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=4000)])
    assignee_id = SelectField("Assign to", coerce=int)
    status = SelectField(
        "Status",
        choices=[("todo", "To do"), ("in_progress", "In progress"), ("done", "Done")],
    )
    priority = SelectField(
        "Priority",
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
    )
    due_date = DateField("Due date", validators=[Optional()], format="%Y-%m-%d")


class MemberForm(FlaskForm):
    email = StringField("Member email", validators=[DataRequired(), Email(), Length(max=255)])
