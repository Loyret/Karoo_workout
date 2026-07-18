from __future__ import annotations

from flask import Flask
from flask_mail import Mail

mail = Mail()


def init_mail(app: Flask) -> None:
    mail.init_app(app)
