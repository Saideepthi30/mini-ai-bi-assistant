import re
import calendar
from datetime import datetime
from .database import get_connection

MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})

def _month_from_text(text):
    """Return YYYY-MM if the question contains a month and optional year."""
    lower = text.lower()
    # Exact YYYY-MM format.
    match = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", lower)
    if match:
        return match.group(0)
    # Month name plus optional year; default to 2026 if omitted.
    for name, number in sorted(MONTHS.items(), key=lambda item: -len(item[0])):
        match = re.search(rf"\b{re.escape(name)}\b(?:\s+(20\d{{2}}))?", lower)
        if match:
            year = match.group(1) or "2026"
            return f"{year}-{number:02d}"
    return None

def _month_mentions(question):
    # Find distinct YYYY-MM values and month-name mentions in their order.
    found = []
    for match in re.finditer(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", question):
        found.append((match.start(), f"{match.group(1)}-{match.group(2)}"))
    lower = question.lower()
    for name, number in MONTHS.items():
        for match in re.finditer(rf"\b{re.escape(name)}\b(?:\s+(20\d{{2}}))?", lower):
            year = match.group(1) or "2026"
            found.append((match.start(), f"{year}-{number:02d}"))
    ordered = []
    for _, month in sorted(found):
        if month not in ordered:
            ordered.append(month)
    return ordered

def _run(sql, params=()):
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

def answer_question(question: str):
    q = " ".join(question.strip().lower().split())
    if not q:
        return {"ok": False, "error": "Question cannot be empty.", "examples": _examples()}

    # Month-to-month comparison must be checked before general monthly trend.
    months = _month_mentions(q)
    comparison_words = any(w in q for w in ["change", "compare", "comparison", "difference", "between"])
    if comparison_words and len(months) >= 2:
        first, second = months[0], months[1]
        rows = _run("""
            SELECT month, ROUND(SUM(revenue), 2) AS revenue
            FROM sales_transactions
            WHERE month IN (?, ?)
            GROUP BY month
        """, (first, second))
        totals = {r["month"]: float(r["revenue"] or 0) for r in rows}
        a, b = totals.get(first, 0.0), totals.get(second, 0.0)
        delta = round(b - a, 2)
        pct = round((delta / a) * 100, 2) if a else None
        direction = "increased" if delta > 0 else "decreased" if delta < 0 else "did not change"
        return {
            "ok": True,
            "question": question,
            "answer": f"Revenue {direction} by {abs(delta):,.2f} from {first} to {second}.",
            "metric": "revenue_change",
            "data": {"from_month": first, "from_revenue": round(a, 2),
                     "to_month": second, "to_revenue": round(b, 2),
                     "change": delta, "percentage_change": pct},
            "sql": "SELECT month, ROUND(SUM(revenue), 2) AS revenue FROM sales_transactions WHERE month IN (?, ?) GROUP BY month",
            "params": [first, second]
        }

    if any(term in q for term in ["monthly trend", "month-wise", "monthly revenue", "revenue trend", "each month", "per month"]):
        sql = """
            SELECT month, ROUND(SUM(revenue), 2) AS revenue
            FROM sales_transactions
            GROUP BY month ORDER BY month
        """
        rows = _run(sql)
        return {"ok": True, "question": question, "answer": "Monthly revenue trend retrieved from the database.",
                "metric": "monthly_revenue", "data": rows, "sql": " ".join(sql.split()), "params": []}

    if ("highest" in q or "top" in q or "best" in q) and any(x in q for x in ["product", "item"]):
        sql = """
            SELECT product, ROUND(SUM(revenue), 2) AS revenue
            FROM sales_transactions GROUP BY product
            ORDER BY revenue DESC LIMIT 1
        """
        rows = _run(sql)
        item = rows[0] if rows else None
        answer = (f"{item['product']} generated the highest revenue: {item['revenue']:,.2f}."
                  if item else "No sales data is available.")
        return {"ok": True, "question": question, "answer": answer, "metric": "top_product",
                "data": item, "sql": " ".join(sql.split()), "params": []}

    if ("highest" in q or "top" in q or "best" in q) and any(x in q for x in ["region", "sales by region"]):
        sql = """
            SELECT region, ROUND(SUM(revenue), 2) AS revenue
            FROM sales_transactions GROUP BY region
            ORDER BY revenue DESC LIMIT 1
        """
        rows = _run(sql)
        item = rows[0] if rows else None
        answer = (f"{item['region']} generated the highest sales: {item['revenue']:,.2f}."
                  if item else "No sales data is available.")
        return {"ok": True, "question": question, "answer": answer, "metric": "top_region",
                "data": item, "sql": " ".join(sql.split()), "params": []}

    if "revenue" in q and len(months) == 1 and any(w in q for w in ["in ", "for ", "during "]):
        month = months[0]
        sql = "SELECT month, ROUND(COALESCE(SUM(revenue), 0), 2) AS revenue FROM sales_transactions WHERE month = ? GROUP BY month"
        rows = _run(sql, (month,))
        value = float(rows[0]["revenue"]) if rows else 0.0
        return {"ok": True, "question": question, "answer": f"Revenue for {month} was {value:,.2f}.",
                "metric": "monthly_total", "data": {"month": month, "revenue": value},
                "sql": sql, "params": [month]}

    if "revenue" in q and any(w in q for w in ["total", "overall", "sum", "how much", "sales amount"]):
        sql = "SELECT ROUND(COALESCE(SUM(revenue), 0), 2) AS total_revenue FROM sales_transactions"
        row = _run(sql)[0]
        value = float(row["total_revenue"])
        return {"ok": True, "question": question, "answer": f"Total revenue is {value:,.2f}.",
                "metric": "total_revenue", "data": {"total_revenue": value},
                "sql": sql, "params": []}

    return {
        "ok": False,
        "question": question,
        "error": "I couldn't map that question to a supported sales query.",
        "examples": _examples()
    }

def _examples():
    return [
        "What is the total revenue?",
        "Which product generated the highest revenue?",
        "What is the monthly revenue trend?",
        "Which region generated the highest sales?",
        "How did revenue change between January and February?",
        "What was the revenue in March 2026?"
    ]
