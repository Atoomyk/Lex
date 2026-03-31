from datetime import datetime

from flask import flash, redirect, render_template, request, url_for

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
    @app.get("/")
    def index():
        selected_client_id = to_int(request.args.get("client_id"))
        return render_template("index.html", **base_context(selected_client_id=selected_client_id))

    @app.post("/clients/add")
    def add_client_route():
        client_id, error = add_client(request.form.get("client_name"))
        if error:
            flash(error, "error")
            return redirect(url_for("index"))
        flash("Клиент добавлен.", "success")
        return redirect(url_for("index", client_id=client_id))

    @app.post("/payments/add")
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
    def delete_payment_route(payment_id: int):
        client_id = to_int(request.form.get("client_id"))
        delete_payment(payment_id)
        flash(f"Платеж ID={payment_id} удален.", "success")
        if client_id:
            return redirect(url_for("index", client_id=client_id))
        return redirect(url_for("index"))

    @app.get("/report/day")
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
