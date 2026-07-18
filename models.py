from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    ftp = db.Column(db.Integer, default=200)
    weight_kg = db.Column(db.Float, nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.utcnow()
    )

    verify_token = db.Column(db.String(64), unique=True, nullable=True)
    verify_token_expires = db.Column(db.DateTime, nullable=True)

    reset_token = db.Column(db.String(64), unique=True, nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    workouts = db.relationship(
        "WorkoutHistory", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def generate_verify_token(self) -> str:
        self.verify_token = secrets.token_urlsafe(32)
        self.verify_token_expires = datetime.utcnow() + timedelta(hours=24)
        return self.verify_token

    def verify_email(self, token: str) -> bool:
        if (
            self.verify_token == token
            and self.verify_token_expires
            and datetime.utcnow() < self.verify_token_expires
        ):
            self.is_verified = True
            self.verify_token = None
            self.verify_token_expires = None
            return True
        return False

    def generate_reset_token(self) -> str:
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        return self.reset_token

    def reset_password(self, token: str, new_password: str) -> bool:
        if (
            self.reset_token == token
            and self.reset_token_expires
            and datetime.utcnow() < self.reset_token_expires
        ):
            self.set_password(new_password)
            self.reset_token = None
            self.reset_token_expires = None
            return True
        return False

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class WorkoutHistory(db.Model):
    __tablename__ = "workout_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    template_id = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    ftp_at_time = db.Column(db.Integer, nullable=False)
    duration_sec = db.Column(db.Integer, nullable=False)
    zwo_content = db.Column(db.Text, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, default="")
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.utcnow()
    )
    completed_at = db.Column(db.DateTime, nullable=True)

    def duration_min(self) -> int:
        return self.duration_sec // 60

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "template_id": self.template_id,
            "name": self.name,
            "ftp_at_time": self.ftp_at_time,
            "duration_min": self.duration_min(),
            "completed": self.completed,
            "notes": self.notes,
            "created_at": self.created_at.strftime("%d.%m.%Y %H:%M"),
            "completed_at": (
                self.completed_at.strftime("%d.%m.%Y %H:%M")
                if self.completed_at
                else None
            ),
        }
