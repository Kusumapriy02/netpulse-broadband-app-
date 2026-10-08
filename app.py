import sqlite3
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, g

app = Flask(__name__)
DB_PATH = "broadband.db"

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        DROP TABLE IF EXISTS usage_logs;
        DROP TABLE IF EXISTS transactions;
        DROP TABLE IF EXISTS customers;
        DROP TABLE IF EXISTS plans;

        CREATE TABLE plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            speed TEXT NOT NULL,
            data_limit TEXT NOT NULL,
            validity_days INTEGER NOT NULL,
            price REAL NOT NULL
        );

        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            connection_id TEXT UNIQUE NOT NULL,
            address TEXT,
            plan_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            followed_up INTEGER DEFAULT 0,
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        );

        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_mode TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        );

        CREATE TABLE usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            data_consumed REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
        """
    )

    plans = [
        ("Home Basic", "50 Mbps", "500 GB", 30, 499),
        ("Home Plus", "100 Mbps", "1000 GB", 30, 799),
        ("Home Pro Unlimited", "300 Mbps", "Unlimited", 30, 1299),
    ]
    db.executemany(
        "INSERT INTO plans (name, speed, data_limit, validity_days, price) VALUES (?, ?, ?, ?, ?)",
        plans,
    )

    customers = [
        ("Ravi Kumar", "BB-1001", "12 Gandhi Nagar", 1),
        ("Priya Sharma", "BB-1002", "45 Lake View Rd", 2),
        ("Arjun Reddy", "BB-1003", "7 MG Road", 3),
        ("Sneha Patel", "BB-1004", "22 Park Street", 1),
        ("Kiran Rao", "BB-1005", "9 Hill View Colony", 2),
        ("Divya Menon", "BB-1006", "3 Church Street", 3),
    ]

    today = datetime.now()
    customer_ids = []
    for name, cid, addr, plan_id in customers:
        start = today - timedelta(days=random.randint(20, 90))
        validity = [r[3] for r in plans if plans.index(r) == plan_id - 1][0]
        due = start + timedelta(days=validity)
        cur = db.execute(
            "INSERT INTO customers (name, connection_id, address, plan_id, start_date, due_date) VALUES (?, ?, ?, ?, ?, ?)",
            (name, cid, addr, plan_id, start.strftime("%Y-%m-%d"), due.strftime("%Y-%m-%d")),
        )
        customer_ids.append((cur.lastrowid, plan_id))

    # Force a couple of customers to be near expiry for the demo
    near_expiry_days = [3, 6]
    for i, (cust_id, plan_id) in enumerate(customer_ids[:2]):
        due = today + timedelta(days=near_expiry_days[i])
        db.execute("UPDATE customers SET due_date = ? WHERE id = ?", (due.strftime("%Y-%m-%d"), cust_id))

    # Seed transactions over the past 5 months for revenue trend
    payment_modes = ["UPI", "Card", "Net Banking"]
    plan_price = {p_id: price for p_id, (_, _, _, _, price) in enumerate([p for p in plans], start=1)}
    plan_prices = {i + 1: plans[i][4] for i in range(len(plans))}

    for cust_id, plan_id in customer_ids:
        for month_back in range(5):
            tx_date = today - timedelta(days=month_back * 30 + random.randint(0, 5))
            status = "Success" if random.random() > 0.18 else "Failed"
            db.execute(
                "INSERT INTO transactions (customer_id, plan_id, amount, payment_mode, date, status) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    cust_id,
                    plan_id,
                    plan_prices[plan_id],
                    random.choice(payment_modes),
                    tx_date.strftime("%Y-%m-%d"),
                    status,
                ),
            )
        # Usage logs - a handful of days per customer
        for d in range(6):
            log_date = today - timedelta(days=d * 5)
            db.execute(
                "INSERT INTO usage_logs (customer_id, date, data_consumed) VALUES (?, ?, ?)",
                (cust_id, log_date.strftime("%Y-%m-%d"), round(random.uniform(2, 25), 1)),
            )

    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Routes - pages
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/customer")
def customer_select():
    db = get_db()
    customers = db.execute("SELECT id, name, connection_id FROM customers ORDER BY name").fetchall()
    return render_template("customer_select.html", customers=customers)


@app.route("/customer/<int:customer_id>")
def customer_view(customer_id):
    db = get_db()
    customer = db.execute(
        """SELECT c.*, p.name AS plan_name, p.speed, p.data_limit, p.price, p.validity_days
           FROM customers c JOIN plans p ON c.plan_id = p.id WHERE c.id = ?""",
        (customer_id,),
    ).fetchone()
    transactions = db.execute(
        "SELECT * FROM transactions WHERE customer_id = ? ORDER BY date DESC LIMIT 10", (customer_id,)
    ).fetchall()
    plans = db.execute("SELECT * FROM plans").fetchall()

    days_left = (datetime.strptime(customer["due_date"], "%Y-%m-%d") - datetime.now()).days

    return render_template(
        "customer_view.html", customer=customer, transactions=transactions, plans=plans, days_left=days_left
    )


@app.route("/recharge/<int:customer_id>", methods=["POST"])
def recharge(customer_id):
    db = get_db()
    payment_mode = request.form.get("payment_mode", "UPI")
    simulate_fail = request.form.get("simulate_fail") == "on"

    customer = db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    plan = db.execute("SELECT * FROM plans WHERE id = ?", (customer["plan_id"],)).fetchone()

    status = "Failed" if simulate_fail else "Success"
    today = datetime.now()

    db.execute(
        "INSERT INTO transactions (customer_id, plan_id, amount, payment_mode, date, status) VALUES (?, ?, ?, ?, ?, ?)",
        (customer_id, plan["id"], plan["price"], payment_mode, today.strftime("%Y-%m-%d"), status),
    )

    if status == "Success":
        new_due = today + timedelta(days=plan["validity_days"])
        db.execute(
            "UPDATE customers SET due_date = ?, followed_up = 0 WHERE id = ?",
            (new_due.strftime("%Y-%m-%d"), customer_id),
        )

    db.commit()
    return redirect(url_for("customer_view", customer_id=customer_id))


@app.route("/expiry")
def expiry_list():
    db = get_db()
    today = datetime.now()
    week = today + timedelta(days=7)
    rows = db.execute(
        """SELECT c.*, p.name AS plan_name, p.price
           FROM customers c JOIN plans p ON c.plan_id = p.id
           WHERE date(c.due_date) BETWEEN date(?) AND date(?)
           ORDER BY c.due_date ASC""",
        (today.strftime("%Y-%m-%d"), week.strftime("%Y-%m-%d")),
    ).fetchall()

    enriched = []
    for r in rows:
        days_left = (datetime.strptime(r["due_date"], "%Y-%m-%d") - today).days
        enriched.append({**dict(r), "days_left": days_left})

    return render_template("expiry.html", customers=enriched)


@app.route("/followup/<int:customer_id>", methods=["POST"])
def followup(customer_id):
    db = get_db()
    db.execute("UPDATE customers SET followed_up = 1 WHERE id = ?", (customer_id,))
    db.commit()
    return redirect(url_for("expiry_list"))


@app.route("/admin")
def admin_dashboard():
    return render_template("admin.html")


# ---------------------------------------------------------------------------
# Routes - JSON APIs powering the dashboard charts
# ---------------------------------------------------------------------------

@app.route("/api/revenue_trend")
def api_revenue_trend():
    db = get_db()
    rows = db.execute(
        """SELECT strftime('%Y-%m', date) AS month, SUM(amount) AS total
           FROM transactions WHERE status = 'Success'
           GROUP BY month ORDER BY month ASC"""
    ).fetchall()
    return jsonify({"labels": [r["month"] for r in rows], "values": [r["total"] for r in rows]})


@app.route("/api/plan_distribution")
def api_plan_distribution():
    db = get_db()
    rows = db.execute(
        """SELECT p.name AS plan_name, COUNT(c.id) AS subscribers
           FROM plans p LEFT JOIN customers c ON c.plan_id = p.id
           GROUP BY p.id"""
    ).fetchall()
    return jsonify({"labels": [r["plan_name"] for r in rows], "values": [r["subscribers"] for r in rows]})


@app.route("/api/renewal_rate")
def api_renewal_rate():
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()["n"]
    success = db.execute("SELECT COUNT(*) AS n FROM transactions WHERE status = 'Success'").fetchone()["n"]
    failed = total - success
    return jsonify({"labels": ["Renewed", "Lapsed / Failed"], "values": [success, failed]})


@app.route("/api/summary")
def api_summary():
    db = get_db()
    total_revenue = db.execute(
        "SELECT COALESCE(SUM(amount), 0) AS t FROM transactions WHERE status = 'Success'"
    ).fetchone()["t"]
    total_customers = db.execute("SELECT COUNT(*) AS n FROM customers").fetchone()["n"]
    total = db.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()["n"]
    success = db.execute("SELECT COUNT(*) AS n FROM transactions WHERE status = 'Success'").fetchone()["n"]
    recovery_rate = round((success / total) * 100, 1) if total else 0
    today = datetime.now()
    week = today + timedelta(days=7)
    nearing = db.execute(
        "SELECT COUNT(*) AS n FROM customers WHERE date(due_date) BETWEEN date(?) AND date(?)",
        (today.strftime("%Y-%m-%d"), week.strftime("%Y-%m-%d")),
    ).fetchone()["n"]
    return jsonify(
        {
            "total_revenue": total_revenue,
            "total_customers": total_customers,
            "recovery_rate": recovery_rate,
            "nearing_expiry": nearing,
        }
    )


init_db()  # seed data on startup, including under gunicorn

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)