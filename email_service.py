from __future__ import annotations

import os
import logging

from flask import render_template, url_for, current_app
from flask_mail import Message

from mail import mail

logger = logging.getLogger(__name__)

MAIL_ENABLED = os.environ.get("MAIL_ENABLED", "true").lower() == "true"


def send_verification_email(user, token: str) -> None:
    if not MAIL_ENABLED:
        verify_url = url_for("auth.verify_email", token=token, _external=True)
        logger.info(f"[MAIL DISABLED] Verification URL for {user.email}: {verify_url}")
        print(f"\n{'='*60}")
        print(f"[ПОЧТА ОТКЛЮЧЕНА] Верификация для {user.email}")
        print(f"Ссылка: {verify_url}")
        print(f"{'='*60}\n")
        return

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
    if not MAIL_ENABLED:
        reset_url = url_for("auth.reset_password_form", token=token, _external=True)
        logger.info(f"[MAIL DISABLED] Reset URL for {user.email}: {reset_url}")
        print(f"\n{'='*60}")
        print(f"[ПОЧТА ОТКЛЮЧЕНА] Сброс пароля для {user.email}")
        print(f"Ссылка: {reset_url}")
        print(f"{'='*60}\n")
        return

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
