from functools import wraps

from datetime import datetime

from flask import current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from services import (
    SUCCESS_VALUES,
    add_client,
    add_payment,
    build_report,
    build_group_report,
    delete_payment,
    list_client_payments,
    list_clients,
    to_int,
)


def base_context(selected_client_id=None, report=None, group_report=None):
    payments = []
    if selected_client_id:
        payments = list_client_payments(selected_client_id)

    return {
        "clients": list_clients(),
        "payments": payments,
        "selected_client_id": selected_client_id,
        "today": datetime.now().strftime("%Y-%m-%d"),
        "success_values": SUCCESS_VALUES,
        "report": report,
        "group_report": group_report,
    }


def register_routes(app):
    def _configured_accounts():
        # Primary: two accounts (admin + user)
        admin_user = current_app.config.get("ADMIN_USERNAME", "")
        admin_hash = current_app.config.get("ADMIN_PASSWORD_HASH", "")
        user_user = current_app.config.get("USER_USERNAME", "")
        user_hash = current_app.config.get("USER_PASSWORD_HASH", "")

        accounts = []
        if admin_user and admin_hash:
            accounts.append({"username": admin_user, "password_hash": admin_hash, "role": "admin"})
        if user_user and user_hash:
            accounts.append({"username": user_user, "password_hash": user_hash, "role": "user"})

        # Backward compatibility: single account via APP_USERNAME / APP_PASSWORD_HASH
        legacy_user = current_app.config.get("APP_USERNAME", "")
        legacy_hash = current_app.config.get("APP_PASSWORD_HASH", "")
        if legacy_user and legacy_hash and not accounts:
            accounts.append({"username": legacy_user, "password_hash": legacy_hash, "role": "admin"})

        return accounts

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("is_authenticated"):
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)

        return wrapped

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            accounts = _configured_accounts()

            if not accounts:
                flash("Не настроены аккаунты в .env (ADMIN_* и USER_*).", "error")
                return render_template("login.html")

            for acc in accounts:
                if username == acc["username"] and check_password_hash(acc["password_hash"], password):
                    session["is_authenticated"] = True
                    session["username"] = username
                    session["role"] = acc["role"]
                    next_url = request.args.get("next") or url_for("index")
                    return redirect(next_url)

            flash("Неверный логин или пароль.", "error")

        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        flash("Вы вышли из системы.", "success")
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def index():
        selected_client_id = to_int(request.args.get("client_id"))
        return render_template("index.html", **base_context(selected_client_id=selected_client_id))

    @app.post("/clients/add")
    @login_required
    def add_client_route():
        client_id, error = add_client(request.form.get("client_name"))
        if error:
            flash(error, "error")
            return redirect(url_for("index"))
        flash("Клиент добавлен.", "success")
        return redirect(url_for("index", client_id=client_id))

    @app.post("/payments/add")
    @login_required
    def add_payment_route():
        client_id = to_int(request.form.get("client_id"))
        error = add_payment(
            client_id,
            request.form.get("date"),
            request.form.get("amount"),
            request.form.get("commission_percent"),
            request.form.get("status"),
            request.form.get("success"),
        )
        if error:
            flash(error, "error")
        else:
            flash("Платеж добавлен.", "success")

        if client_id:
            return redirect(url_for("index", client_id=client_id))
        return redirect(url_for("index"))

    @app.post("/payments/delete/<int:payment_id>")
    @login_required
    def delete_payment_route(payment_id: int):
        client_id = to_int(request.form.get("client_id"))
        delete_payment(payment_id)
        flash(f"Платеж ID={payment_id} удален.", "success")
        if client_id:
            return redirect(url_for("index", client_id=client_id))
        return redirect(url_for("index"))

    @app.get("/report/day")
    @login_required
    def report_day():
        client_id = to_int(request.args.get("client_id"))
        if not client_id:
            flash("Сначала выберите клиента.", "error")
            return redirect(url_for("index"))

        report, error = build_report(client_id, "day", (request.args.get("date") or "").strip())
        if error:
            flash(error, "error")
            return redirect(url_for("index", client_id=client_id))
        return render_template("index.html", **base_context(selected_client_id=client_id, report=report))

    @app.get("/report/month")
    @login_required
    def report_month():
        client_id = to_int(request.args.get("client_id"))
        if not client_id:
            flash("Сначала выберите клиента.", "error")
            return redirect(url_for("index"))

        report, error = build_report(client_id, "month", (request.args.get("month") or "").strip())
        if error:
            flash(error, "error")
            return redirect(url_for("index", client_id=client_id))
        return render_template("index.html", **base_context(selected_client_id=client_id, report=report))

    @app.get("/report/year")
    @login_required
    def report_year():
        client_id = to_int(request.args.get("client_id"))
        if not client_id:
            flash("Сначала выберите клиента.", "error")
            return redirect(url_for("index"))

        report, error = build_report(client_id, "year", (request.args.get("year") or "").strip())
        if error:
            flash(error, "error")
            return redirect(url_for("index", client_id=client_id))
        return render_template("index.html", **base_context(selected_client_id=client_id, report=report))

    @app.get("/report/group/day")
    @login_required
    def group_report_day():
        value = (request.args.get("date") or "").strip()
        report, error = build_group_report("day", value)
        if error:
            flash(error, "error")
            return redirect(url_for("index"))
        selected_client_id = to_int(request.args.get("client_id"))
        return render_template(
            "index.html",
            **base_context(selected_client_id=selected_client_id, group_report=report),
        )

    @app.get("/report/group/month")
    @login_required
    def group_report_month():
        value = (request.args.get("month") or "").strip()
        report, error = build_group_report("month", value)
        if error:
            flash(error, "error")
            return redirect(url_for("index"))
        selected_client_id = to_int(request.args.get("client_id"))
        return render_template(
            "index.html",
            **base_context(selected_client_id=selected_client_id, group_report=report),
        )

    @app.get("/report/group/year")
    @login_required
    def group_report_year():
        value = (request.args.get("year") or "").strip()
        report, error = build_group_report("year", value)
        if error:
            flash(error, "error")
            return redirect(url_for("index"))
        selected_client_id = to_int(request.args.get("client_id"))
        return render_template(
            "index.html",
            **base_context(selected_client_id=selected_client_id, group_report=report),
        )
