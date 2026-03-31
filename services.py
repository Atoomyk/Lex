from datetime import datetime
from decimal import Decimal, InvalidOperation

import sqlite3

from db import get_conn


SUCCESS_VALUES = ["Успешно", "Неуспешно", "В обработке"]


def validate_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def to_int(value: str):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def list_clients():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM clients ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


def list_client_payments(client_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, date, amount
        FROM payments
        WHERE client_id = ?
        ORDER BY date DESC, id DESC
        """,
        (client_id,),
    )
    rows = cur.fetchall()
    conn.close()

    payments = []
    for row in rows:
        amount = Decimal(str(row["amount"])).quantize(Decimal("0.01"))
        payments.append({"id": row["id"], "date": row["date"], "amount": str(amount)})
    return payments


def add_client(name: str):
    clean_name = (name or "").strip()
    if not clean_name:
        return None, "Имя клиента не может быть пустым."

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO clients (name) VALUES (?)", (clean_name,))
        conn.commit()
        client_id = cur.lastrowid
        conn.close()
        return client_id, None
    except sqlite3.IntegrityError:
        conn.close()
        return None, "Клиент с таким именем уже существует."


def add_payment(client_id, date_str, amount_str, commission_str, status, success):
    if not client_id:
        return "Нельзя добавить платеж без выбора клиента."

    date_value = (date_str or "").strip() or datetime.now().strftime("%Y-%m-%d")
    if not validate_date(date_value):
        return "Дата должна быть в формате YYYY-MM-DD."

    try:
        amount = Decimal((amount_str or "").strip())
    except (InvalidOperation, TypeError):
        return "Сумма должна быть числом."

    if amount <= 0:
        return "Сумма должна быть больше 0."

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM payments WHERE client_id = ? AND date = ?",
        (client_id, date_value),
    )
    cnt = cur.fetchone()["cnt"]
    if cnt >= 20:
        conn.close()
        return "Нельзя добавить больше 20 платежей в день для одного клиента."

    cur.execute(
        """
        SELECT commission_percent
        FROM payments
        WHERE client_id = ? AND date = ?
        LIMIT 1
        """,
        (client_id, date_value),
    )
    row = cur.fetchone()

    if row is not None:
        commission = Decimal(str(row["commission_percent"]))
    else:
        try:
            commission = Decimal((commission_str or "").strip())
        except (InvalidOperation, TypeError):
            conn.close()
            return "Комиссия должна быть числом."

    if commission < 0 or commission > 100:
        conn.close()
        return "Комиссия должна быть в диапазоне 0..100."

    cur.execute(
        """
        INSERT INTO payments (client_id, date, amount, commission_percent, status, success)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            client_id,
            date_value,
            float(amount),
            float(commission),
            (status or "").strip(),
            (success or "").strip(),
        ),
    )
    conn.commit()
    conn.close()
    return None


def delete_payment(payment_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
    conn.commit()
    conn.close()


def build_report(client_id: int, mode: str, value: str):
    conn = get_conn()
    cur = conn.cursor()

    if mode == "day":
        if not validate_date(value):
            conn.close()
            return None, "Неверный формат даты. Используйте YYYY-MM-DD."
        title = f"Отчет за день {value}"
        cur.execute(
            """
            SELECT amount, commission_percent
            FROM payments
            WHERE client_id = ? AND date = ?
            """,
            (client_id, value),
        )
    elif mode == "month":
        try:
            datetime.strptime(value, "%Y-%m")
        except ValueError:
            conn.close()
            return None, "Неверный формат месяца. Используйте YYYY-MM."
        title = f"Отчет за месяц {value}"
        cur.execute(
            """
            SELECT amount, commission_percent
            FROM payments
            WHERE client_id = ? AND date LIKE ?
            """,
            (client_id, f"{value}%"),
        )
    elif mode == "year":
        if len(value) != 4 or not value.isdigit():
            conn.close()
            return None, "Неверный формат года. Используйте YYYY."
        title = f"Отчет за год {value}"
        cur.execute(
            """
            SELECT amount, commission_percent
            FROM payments
            WHERE client_id = ? AND date LIKE ?
            """,
            (client_id, f"{value}%"),
        )
    else:
        conn.close()
        return None, "Неверный тип отчета."

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return {
            "title": title,
            "count": 0,
            "total_sum": "0.00",
            "total_result": "0.00",
        }, None

    total_sum = Decimal("0")
    total_result = Decimal("0")
    for row in rows:
        amount = Decimal(str(row["amount"]))
        commission = Decimal(str(row["commission_percent"]))
        total_sum += amount
        total_result += amount * (Decimal("1") - commission / Decimal("100"))

    total_sum = total_sum.quantize(Decimal("0.01"))
    total_result = total_result.quantize(Decimal("0.01"))
    return {
        "title": title,
        "count": len(rows),
        "total_sum": str(total_sum),
        "total_result": str(total_result),
    }, None


def build_group_report(mode: str, value: str):
    conn = get_conn()
    cur = conn.cursor()

    if mode == "day":
        if not validate_date(value):
            conn.close()
            return None, "Неверный формат даты. Используйте YYYY-MM-DD."
        title = f"Сводный отчет за день {value}"
        cur.execute(
            """
            SELECT c.id AS client_id, c.name AS client_name, p.amount, p.commission_percent
            FROM payments p
            JOIN clients c ON c.id = p.client_id
            WHERE p.date = ?
            ORDER BY c.name
            """,
            (value,),
        )
    elif mode == "month":
        try:
            datetime.strptime(value, "%Y-%m")
        except ValueError:
            conn.close()
            return None, "Неверный формат месяца. Используйте YYYY-MM."
        title = f"Сводный отчет за месяц {value}"
        cur.execute(
            """
            SELECT c.id AS client_id, c.name AS client_name, p.amount, p.commission_percent
            FROM payments p
            JOIN clients c ON c.id = p.client_id
            WHERE p.date LIKE ?
            ORDER BY c.name
            """,
            (f"{value}%",),
        )
    elif mode == "year":
        if len(value) != 4 or not value.isdigit():
            conn.close()
            return None, "Неверный формат года. Используйте YYYY."
        title = f"Сводный отчет за год {value}"
        cur.execute(
            """
            SELECT c.id AS client_id, c.name AS client_name, p.amount, p.commission_percent
            FROM payments p
            JOIN clients c ON c.id = p.client_id
            WHERE p.date LIKE ?
            ORDER BY c.name
            """,
            (f"{value}%",),
        )
    else:
        conn.close()
        return None, "Неверный тип отчета."

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return {
            "title": title,
            "rows": [],
            "total_sum": "0.00",
            "total_result": "0.00",
        }, None

    by_client = {}
    for row in rows:
        client_id = row["client_id"]
        if client_id not in by_client:
            by_client[client_id] = {
                "client_name": row["client_name"],
                "payment_count": 0,
                "total_sum": Decimal("0"),
                "total_result": Decimal("0"),
            }

        amount = Decimal(str(row["amount"]))
        commission = Decimal(str(row["commission_percent"]))
        by_client[client_id]["payment_count"] += 1
        by_client[client_id]["total_sum"] += amount
        by_client[client_id]["total_result"] += amount * (Decimal("1") - commission / Decimal("100"))

    report_rows = []
    grand_sum = Decimal("0")
    grand_result = Decimal("0")

    for item in by_client.values():
        client_sum = item["total_sum"].quantize(Decimal("0.01"))
        client_result = item["total_result"].quantize(Decimal("0.01"))
        grand_sum += client_sum
        grand_result += client_result
        report_rows.append(
            {
                "client_name": item["client_name"],
                "payment_count": item["payment_count"],
                "total_sum": str(client_sum),
                "total_result": str(client_result),
            }
        )

    report_rows.sort(key=lambda x: x["client_name"].lower())
    grand_sum = grand_sum.quantize(Decimal("0.01"))
    grand_result = grand_result.quantize(Decimal("0.01"))

    return {
        "title": title,
        "rows": report_rows,
        "total_sum": str(grand_sum),
        "total_result": str(grand_result),
    }, None
