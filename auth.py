from __future__ import annotations

from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, current_app,
)
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange

from models import db, User
from email_service import send_verification_email, send_reset_email

auth_bp = Blueprint("auth", __name__)


class RegisterForm(FlaskForm):
    username = StringField(
        "Имя пользователя",
        validators=[DataRequired(), Length(min=3, max=80)],
    )
    email = StringField(
        "Email", validators=[DataRequired(), Email()]
    )
    password = PasswordField(
        "Пароль", validators=[DataRequired(), Length(min=6)]
    )
    password2 = PasswordField(
        "Повторите пароль",
        validators=[DataRequired(), EqualTo("password", message="Пароли не совпадают")],
    )
    ftp = IntegerField(
        "FTP", validators=[DataRequired(), NumberRange(min=50, max=500)]
    )


class LoginForm(FlaskForm):
    username = StringField("Имя пользователя", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember = BooleanField("Запомнить меня")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "Новый пароль", validators=[DataRequired(), Length(min=6)]
    )
    password2 = PasswordField(
        "Повторите пароль",
        validators=[DataRequired(), EqualTo("password", message="Пароли не совпадают")],
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        errors = []
        if User.query.filter_by(username=username).first():
            errors.append("Это имя пользователя уже занято")
        if User.query.filter_by(email=email).first():
            errors.append("Этот email уже зарегистрирован")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("auth/register.html", form=form)

        user = User(username=username, email=email, ftp=form.ftp.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        token = user.generate_verify_token()
        db.session.commit()

        try:
            send_verification_email(user, token)
            flash("Письмо с подтверждением отправлено на " + email, "success")
        except Exception:
            current_app.logger.warning("Failed to send verification email")
            flash("Аккаунт создан. Письмо не удалось отправить.", "info")

        login_user(user)
        return redirect(url_for("dashboard.dashboard"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/verify/<token>")
def verify_email(token: str):
    user = User.query.filter_by(verify_token=token).first()
    if not user:
        flash("Недействительная ссылка подтверждения", "error")
        return redirect(url_for("index"))

    if user.verify_email(token):
        db.session.commit()
        flash("Email подтверждён! Добро пожаловать!", "success")
    else:
        flash("Ссылка подтверждения истекла. Запросите новую.", "error")

    return redirect(url_for("dashboard.dashboard"))


@auth_bp.route("/resend-verify")
@login_required
def resend_verify():
    if current_user.is_verified:
        flash("Ваш email уже подтверждён", "info")
        return redirect(url_for("dashboard.dashboard"))

    token = current_user.generate_verify_token()
    db.session.commit()

    try:
        send_verification_email(current_user, token)
        flash("Новое письмо отправлено на " + current_user.email, "success")
    except Exception:
        flash("Не удалось отправить письмо. Попробуйте позже.", "error")

    return redirect(url_for("dashboard.dashboard"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user and user.check_password(form.password.data):
            if not user.is_verified:
                flash("Подтвердите email перед входом. Проверьте почту.", "error")
                return render_template("auth/login.html", form=form)

            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            flash(f"С возвращением, {user.username}!", "success")
            return redirect(next_page or url_for("dashboard.dashboard"))

        flash("Неверное имя пользователя или пароль", "error")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            try:
                send_reset_email(user, token)
            except Exception:
                current_app.logger.warning("Failed to send reset email")
        flash(
            "Если аккаунт с таким email существует, письмо отправлено",
            "info",
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset/<token>", methods=["GET", "POST"])
def reset_password_form(token: str):
    user = User.query.filter_by(reset_token=token).first()
    if not user:
        flash("Недействительная ссылка сброса", "error")
        return redirect(url_for("index"))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        if user.reset_password(token, form.password.data):
            db.session.commit()
            flash("Пароль изменён! Войдите с новым паролем.", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("Ссылка сброса истекла. Запросите новую.", "error")
            return redirect(url_for("auth.forgot_password"))

    return render_template("auth/reset_password.html", form=form, token=token)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта", "info")
    return redirect(url_for("index"))
