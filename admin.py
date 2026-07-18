from __future__ import annotations

from functools import wraps
from datetime import datetime, timedelta

from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, jsonify,
)
from flask_login import login_required, current_user
from sqlalchemy import func

from models import db, User, WorkoutHistory, AdminLog
from generator.workouts import WorkoutTemplates

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
templates_store = WorkoutTemplates()


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("Доступ запрещён. Нужны права администратора.", "error")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


def log_admin_action(action: str, target_type: str, target_id: int = None, details: str = "") -> None:
    log = AdminLog(
        admin_id=current_user.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()


@admin_bp.route("/")
@admin_required
def dashboard():
    now = datetime.utcnow()

    total_users = User.query.count()
    verified_users = User.query.filter_by(is_verified=True).count()
    new_users_week = User.query.filter(
        User.created_at >= now - timedelta(days=7)
    ).count()
    new_users_month = User.query.filter(
        User.created_at >= now - timedelta(days=30)
    ).count()

    total_workouts = WorkoutHistory.query.count()
    completed_workouts = WorkoutHistory.query.filter_by(completed=True).count()
    workouts_week = WorkoutHistory.query.filter(
        WorkoutHistory.created_at >= now - timedelta(days=7)
    ).count()

    total_minutes = (
        db.session.query(func.sum(WorkoutHistory.duration_sec))
        .scalar() or 0
    ) // 60

    avg_ftp = (
        db.session.query(func.avg(User.ftp))
        .scalar() or 0
    )

    popular_templates = (
        db.session.query(
            WorkoutHistory.template_id,
            func.count(WorkoutHistory.id).label("cnt"),
        )
        .group_by(WorkoutHistory.template_id)
        .order_by(func.count(WorkoutHistory.id).desc())
        .limit(5)
        .all()
    )

    recent_users = (
        User.query
        .order_by(User.created_at.desc())
        .limit(10)
        .all()
    )

    recent_logs = (
        AdminLog.query
        .order_by(AdminLog.created_at.desc())
        .limit(10)
        .all()
    )

    daily_registrations = []
    for i in range(29, -1, -1):
        day = (now - timedelta(days=i)).date()
        count = User.query.filter(
            func.date(User.created_at) == day
        ).count()
        daily_registrations.append({"date": day.isoformat(), "count": count})

    daily_workouts = []
    for i in range(29, -1, -1):
        day = (now - timedelta(days=i)).date()
        count = WorkoutHistory.query.filter(
            func.date(WorkoutHistory.created_at) == day
        ).count()
        daily_workouts.append({"date": day.isoformat(), "count": count})

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        verified_users=verified_users,
        new_users_week=new_users_week,
        new_users_month=new_users_month,
        total_workouts=total_workouts,
        completed_workouts=completed_workouts,
        workouts_week=workouts_week,
        total_minutes=total_minutes,
        avg_ftp=int(avg_ftp),
        popular_templates=popular_templates,
        recent_users=recent_users,
        recent_logs=recent_logs,
        daily_registrations=daily_registrations,
        daily_workouts=daily_workouts,
    )


@admin_bp.route("/users")
@admin_required
def users_list():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    per_page = 20

    query = User.query

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                User.username.ilike(like),
                User.email.ilike(like),
            )
        )

    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        "admin/users.html",
        users=pagination.items,
        pagination=pagination,
        search=search,
    )


@admin_bp.route("/users/<int:user_id>")
@admin_required
def user_detail(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        flash("Пользователь не найден", "error")
        return redirect(url_for("admin.users_list"))

    workouts = (
        WorkoutHistory.query
        .filter_by(user_id=user_id)
        .order_by(WorkoutHistory.created_at.desc())
        .limit(50)
        .all()
    )

    total_workouts = WorkoutHistory.query.filter_by(user_id=user_id).count()
    completed = WorkoutHistory.query.filter_by(user_id=user_id, completed=True).count()
    total_min = (
        db.session.query(func.sum(WorkoutHistory.duration_sec))
        .filter_by(user_id=user_id)
        .scalar() or 0
    ) // 60

    return render_template(
        "admin/user_detail.html",
        user=user,
        workouts=workouts,
        total_workouts=total_workouts,
        completed=completed,
        total_min=total_min,
    )


@admin_bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        flash("Пользователь не найден", "error")
        return redirect(url_for("admin.users_list"))

    if user.id == current_user.id:
        flash("Нельзя изменить свои собственные права", "error")
        return redirect(url_for("admin.user_detail", user_id=user_id))

    user.is_admin = not user.is_admin
    db.session.commit()

    action = "grant_admin" if user.is_admin else "revoke_admin"
    log_admin_action(action, "user", user_id, f"username={user.username}")
    flash(f"Права администратора для {user.username}: {'выданы' if user.is_admin else 'отозваны'}", "success")
    return redirect(url_for("admin.user_detail", user_id=user_id))


@admin_bp.route("/users/<int:user_id>/toggle-verify", methods=["POST"])
@admin_required
def toggle_verify(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        flash("Пользователь не найден", "error")
        return redirect(url_for("admin.users_list"))

    user.is_verified = not user.is_verified
    db.session.commit()

    action = "verify_user" if user.is_verified else "unverify_user"
    log_admin_action(action, "user", user_id, f"username={user.username}")
    flash(f"Email {user.username}: {'подтверждён' if user.is_verified else 'отменён'}", "success")
    return redirect(url_for("admin.user_detail", user_id=user_id))


@admin_bp.route("/users/<int:user_id>/set-ftp", methods=["POST"])
@admin_required
def set_user_ftp(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        flash("Пользователь не найден", "error")
        return redirect(url_for("admin.users_list"))

    ftp = request.form.get("ftp")
    if ftp and ftp.isdigit() and 50 <= int(ftp) <= 500:
        old_ftp = user.ftp
        user.ftp = int(ftp)
        db.session.commit()
        log_admin_action("set_ftp", "user", user_id, f"old={old_ftp}, new={user.ftp}")
        flash(f"FTP для {user.username} изменён на {user.ftp} Вт", "success")
    else:
        flash("Некорректное значение FTP (50-500)", "error")

    return redirect(url_for("admin.user_detail", user_id=user_id))


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def reset_user_password(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        flash("Пользователь не найден", "error")
        return redirect(url_for("admin.users_list"))

    import secrets
    new_password = secrets.token_urlsafe(8)
    user.set_password(new_password)
    db.session.commit()

    log_admin_action("reset_password", "user", user_id, f"username={user.username}")
    flash(f"Пароль для {user.username} сброшен. Новый пароль: {new_password}", "success")
    return redirect(url_for("admin.user_detail", user_id=user_id))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        flash("Пользователь не найден", "error")
        return redirect(url_for("admin.users_list"))

    if user.id == current_user.id:
        flash("Нельзя удалить самого себя", "error")
        return redirect(url_for("admin.user_detail", user_id=user_id))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    log_admin_action("delete_user", "user", user_id, f"username={username}")
    flash(f"Пользователь {username} удалён", "success")
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/workouts")
@admin_required
def workouts_list():
    page = request.args.get("page", 1, type=int)
    per_page = 20

    pagination = (
        WorkoutHistory.query
        .order_by(WorkoutHistory.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return render_template(
        "admin/workouts.html",
        workouts=pagination.items,
        pagination=pagination,
    )


@admin_bp.route("/workouts/<int:wid>/delete", methods=["POST"])
@admin_required
def delete_workout(wid: int):
    wh = db.session.get(WorkoutHistory, wid)
    if not wh:
        flash("Тренировка не найдена", "error")
        return redirect(url_for("admin.workouts_list"))

    user_name = wh.user.username if wh.user else "?"
    db.session.delete(wh)
    db.session.commit()

    log_admin_action("delete_workout", "workout", wid, f"user={user_name}, name={wh.name}")
    flash("Тренировка удалена", "success")
    return redirect(url_for("admin.workouts_list"))


@admin_bp.route("/logs")
@admin_required
def logs_list():
    page = request.args.get("page", 1, type=int)
    per_page = 30

    pagination = (
        AdminLog.query
        .order_by(AdminLog.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return render_template(
        "admin/logs.html",
        logs=pagination.items,
        pagination=pagination,
    )


@admin_bp.route("/api/stats")
@admin_required
def api_stats():
    now = datetime.utcnow()

    daily = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        users = User.query.filter(func.date(User.created_at) == day).count()
        workouts = WorkoutHistory.query.filter(
            func.date(WorkoutHistory.created_at) == day
        ).count()
        daily.append({
            "date": day.isoformat(),
            "users": users,
            "workouts": workouts,
        })

    return jsonify({
        "daily": daily,
        "total_users": User.query.count(),
        "total_workouts": WorkoutHistory.query.count(),
    })
