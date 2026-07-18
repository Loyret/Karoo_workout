from __future__ import annotations

from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, jsonify,
)
from flask_login import login_required, current_user

from models import db, User, WorkoutHistory
from generator.zwo import ZWOGenerator, Workout
from generator.workouts import WorkoutTemplates

dashboard_bp = Blueprint("dashboard", __name__)
templates_store = WorkoutTemplates()


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    workouts = (
        WorkoutHistory.query
        .filter_by(user_id=current_user.id)
        .order_by(WorkoutHistory.created_at.desc())
        .limit(20)
        .all()
    )
    total = WorkoutHistory.query.filter_by(user_id=current_user.id).count()
    completed = (
        WorkoutHistory.query
        .filter_by(user_id=current_user.id, completed=True)
        .count()
    )
    total_min = (
        db.session.query(db.func.sum(WorkoutHistory.duration_sec))
        .filter_by(user_id=current_user.id)
        .scalar()
        or 0
    ) // 60

    return render_template(
        "dashboard.html",
        workouts=workouts,
        total=total,
        completed=completed,
        total_min=total_min,
    )


@dashboard_bp.route("/dashboard/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        ftp = request.form.get("ftp")
        weight = request.form.get("weight")
        if ftp:
            current_user.ftp = int(ftp)
        if weight:
            current_user.weight_kg = float(weight)
        db.session.commit()
        flash("Профиль обновлён", "success")
        return redirect(url_for("dashboard.dashboard"))

    return render_template("dashboard_settings.html")


@dashboard_bp.route("/api/workout/save", methods=["POST"])
@login_required
def api_save_workout():
    data = request.json
    template_id = data.get("template_id")
    ftp = int(data.get("ftp", current_user.ftp))

    tmpl = templates_store.get_by_id(template_id)
    if not tmpl:
        return jsonify({"error": "Template not found"}), 404

    workout = tmpl.build(ftp)
    zwo_content = ZWOGenerator.generate(workout)

    wh = WorkoutHistory(
        user_id=current_user.id,
        template_id=template_id,
        name=workout.name,
        description=workout.description,
        ftp_at_time=ftp,
        duration_sec=workout.total_duration(),
        zwo_content=zwo_content,
    )
    db.session.add(wh)
    db.session.commit()

    return jsonify({"ok": True, "id": wh.id})


@dashboard_bp.route("/api/workout/complete/<int:wid>", methods=["POST"])
@login_required
def api_complete_workout(wid: int):
    wh = WorkoutHistory.query.get_or_404(wid)
    if wh.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403

    wh.completed = True
    wh.completed_at = datetime.now(timezone.utc)
    data = request.json or {}
    if data.get("notes"):
        wh.notes = data["notes"]
    db.session.commit()
    return jsonify({"ok": True})


@dashboard_bp.route("/api/workout/delete/<int:wid>", methods=["POST"])
@login_required
def api_delete_workout(wid: int):
    wh = WorkoutHistory.query.get_or_404(wid)
    if wh.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403

    db.session.delete(wh)
    db.session.commit()
    return jsonify({"ok": True})


@dashboard_bp.route("/api/workout/download/<int:wid>")
@login_required
def api_download_workout(wid: int):
    wh = WorkoutHistory.query.get_or_404(wid)
    if wh.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403

    from flask import send_file
    import io

    filename = f"{wh.template_id}_{wh.ftp_at_time}w.zwo"
    return send_file(
        io.BytesIO(wh.zwo_content.encode("utf-8")),
        mimetype="application/xml",
        as_attachment=True,
        download_name=filename,
    )
