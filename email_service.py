from __future__ import annotations

from flask import render_template, url_for
from flask_mail import Message

from mail import mail


def send_verification_email(user, token: str) -> None:
    verify_url = url_for("auth.verify_email", token=token, _external=True)
    msg = Message(
        subject="Подтвердите ваш email — Karoo Trainer",
        recipients=[user.email],
        html=render_template(
            "emails/verify.html",
            user=user,
            verify_url=verify_url,
        ),
        body=(
            f"Привет, {user.username}!\n\n"
            f"Перейдите по ссылке для подтверждения email:\n{verify_url}\n\n"
            f"Ссылка действительна 24 часа."
        ),
    )
    mail.send(msg)


def send_reset_email(user, token: str) -> None:
    reset_url = url_for("auth.reset_password_form", token=token, _external=True)
    msg = Message(
        subject="Сброс пароля — Karoo Trainer",
        recipients=[user.email],
        html=render_template(
            "emails/reset.html",
            user=user,
            reset_url=reset_url,
        ),
        body=(
            f"Привет, {user.username}!\n\n"
            f"Для сброса пароля перейдите по ссылке:\n{reset_url}\n\n"
            f"Ссылка действительна 1 час.\n"
            f"Если вы не запрашивали сброс — просто проигнорируйте это письмо."
        ),
    )
    mail.send(msg)
