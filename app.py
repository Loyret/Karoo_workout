from __future__ import annotations

import io
import json
import os
from pathlib import Path

from flask import (
    Flask, render_template, request, jsonify, send_file,
)
from flask_login import LoginManager, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import get_config
from models import db, User
from mail import mail, init_mail
from auth import auth_bp
from dashboard import dashboard_bp
from generator.zwo import ZWOGenerator, Workout, WorkoutStep
from generator.workouts import WorkoutTemplates
from generator.zones import TrainingZones


limiter = Limiter(key_func=get_remote_address)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config())

    db.init_app(app)
    init_mail(app)
    limiter.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Войдите, чтобы получить доступ"
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    limiter.limit("10/minute")(
        app.view_functions.get("auth.login", lambda: None)
    )
    limiter.limit("5/minute")(
        app.view_functions.get("auth.register", lambda: None)
    )

    templates_store = WorkoutTemplates()

    def _workout_to_chart_data(workout: Workout) -> dict:
        labels = []
        powers = []
        colors = []
        cadences = []
        texts = []
        t = 0

        for step in workout.steps:
            if step.type == "Intervals":
                for _ in range(step.repeat):
                    for on_step in step.on_steps:
                        labels.append(_fmt_time(t))
                        p = on_step.power or 0
                        powers.append(round(p * 100))
                        colors.append(TrainingZones.get_zone_color(p))
                        cadences.append(on_step.cadence or 0)
                        texts.append(on_step.text or "")
                        t += on_step.duration
                    for off_step in step.off_steps:
                        labels.append(_fmt_time(t))
                        p = off_step.power or 0
                        powers.append(round(p * 100))
                        colors.append(TrainingZones.get_zone_color(p))
                        cadences.append(off_step.cadence or 0)
                        texts.append(off_step.text or "")
                        t += off_step.duration
            else:
                labels.append(_fmt_time(t))
                p = step.power or (
                    (step.power_low or 0) + (step.power_high or 0)
                ) / 2
                powers.append(round(p * 100))
                colors.append(TrainingZones.get_zone_color(p))
                cadences.append(step.cadence or 0)
                texts.append(step.text or "")
                t += step.duration

        return {
            "labels": labels,
            "powers": powers,
            "colors": colors,
            "cadences": cadences,
            "texts": texts,
        }

    def _fmt_time(seconds: int) -> str:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    @app.context_processor
    def inject_globals():
        return {
            "user_ftp": current_user.ftp if current_user.is_authenticated else 200,
        }

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/templates")
    def workout_templates():
        categories = templates_store.get_categories()
        return render_template(
            "templates.html",
            templates=templates_store.templates,
            categories=categories,
        )

    @app.route("/template/<template_id>")
    def template_detail(template_id: str):
        tmpl = templates_store.get_by_id(template_id)
        if not tmpl:
            return "Not found", 404
        default_ftp = current_user.ftp if current_user.is_authenticated else 200
        ftp = int(request.args.get("ftp", default_ftp))
        workout = tmpl.build(ftp)
        chart_data = _workout_to_chart_data(workout)
        return render_template(
            "template_detail.html",
            template=tmpl,
            workout=workout,
            chart_data=json.dumps(chart_data),
            ftp=ftp,
            zones=TrainingZones.ZONES,
            fmt_time=_fmt_time,
        )

    @app.route("/builder")
    def builder():
        default_ftp = current_user.ftp if current_user.is_authenticated else 200
        return render_template(
            "builder.html", zones=TrainingZones.ZONES, default_ftp=default_ftp
        )

    @app.route("/education")
    def education():
        return render_template(
            "education.html", zones=TrainingZones.ZONES
        )

    @app.route("/api/generate", methods=["POST"])
    def api_generate():
        data = request.json
        template_id = data.get("template_id")
        ftp = int(data.get("ftp", 200))

        tmpl = templates_store.get_by_id(template_id)
        if not tmpl:
            return jsonify({"error": "Template not found"}), 404

        workout = tmpl.build(ftp)
        zwo_content = ZWOGenerator.generate(workout)

        return jsonify({
            "zwo": zwo_content,
            "name": workout.name,
            "duration": workout.total_duration(),
        })

    @app.route("/api/download/<template_id>")
    def api_download(template_id: str):
        ftp = int(request.args.get("ftp", 200))
        tmpl = templates_store.get_by_id(template_id)
        if not tmpl:
            return "Not found", 404

        workout = tmpl.build(ftp)
        zwo_content = ZWOGenerator.generate(workout)

        filename = f"{template_id}_{ftp}w.zwo"
        return send_file(
            io.BytesIO(zwo_content.encode("utf-8")),
            mimetype="application/xml",
            as_attachment=True,
            download_name=filename,
        )

    @app.route("/api/zones")
    def api_zones():
        ftp = int(request.args.get("ftp", 200))
        result = []
        for zone in TrainingZones.ZONES:
            low, high = zone.power_range(ftp)
            result.append({
                "name": zone.name,
                "short": zone.short,
                "power_low": low,
                "power_high": high,
                "description": zone.description,
                "purpose": zone.purpose,
                "color": zone.color,
            })
        return jsonify(result)

    @app.route("/api/build_custom", methods=["POST"])
    def api_build_custom():
        data = request.json
        ftp = int(data.get("ftp", 200))
        name = data.get("name", "Кастомная тренировка")
        description = data.get("description", "")
        steps_data = data.get("steps", [])

        steps = []
        for s in steps_data:
            stype = s.get("type", "SteadyState")
            if stype == "Intervals":
                on_steps = [
                    WorkoutStep(
                        type="SteadyState",
                        duration=on.get("duration", 60),
                        power=on.get("power", 1.0),
                        cadence=on.get("cadence"),
                        text=on.get("text", ""),
                    )
                    for on in s.get("on", [])
                ]
                off_steps = [
                    WorkoutStep(
                        type="SteadyState",
                        duration=off.get("duration", 60),
                        power=off.get("power", 0.5),
                        cadence=off.get("cadence"),
                        text=off.get("text", ""),
                    )
                    for off in s.get("off", [])
                ]
                steps.append(WorkoutStep(
                    type="Intervals",
                    repeat=s.get("repeat", 1),
                    on_steps=on_steps,
                    off_steps=off_steps,
                    text=s.get("text", ""),
                ))
            else:
                steps.append(WorkoutStep(
                    type=stype,
                    duration=s.get("duration", 60),
                    power=s.get("power"),
                    power_low=s.get("power_low"),
                    power_high=s.get("power_high"),
                    cadence=s.get("cadence"),
                    text=s.get("text", ""),
                ))

        workout = Workout(
            name=name,
            description=description,
            steps=steps,
        )

        zwo_content = ZWOGenerator.generate(workout)
        chart_data = _workout_to_chart_data(workout)

        return jsonify({
            "zwo": zwo_content,
            "name": workout.name,
            "duration": workout.total_duration(),
            "chart_data": chart_data,
        })

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000, use_reloader=False)
