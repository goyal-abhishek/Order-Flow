from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "orderflow_secret_key_change_this"

DB = "orders.db"

STATUSES = [
    "Created",
    "Confirmed",
    "Preparing",
    "Ready",
    "Served",
    "Paid",
    "Completed"
]

ORDER_TYPES = [
    "Dine-In",
    "Takeaway",
    "Delivery"
]


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT NOT NULL,
            order_type TEXT NOT NULL,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Created',
            created_at TEXT NOT NULL,
            phone TEXT DEFAULT '',
            address TEXT DEFAULT ''
        )
    """)

    # Upgrade old database automatically
    columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(orders)").fetchall()
    ]

    if "phone" not in columns:
        conn.execute(
            "ALTER TABLE orders ADD COLUMN phone TEXT DEFAULT ''"
        )

    if "address" not in columns:
        conn.execute(
            "ALTER TABLE orders ADD COLUMN address TEXT DEFAULT ''"
        )

    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Remove old Owner account
    conn.execute(
        "DELETE FROM users WHERE username='owner'"
    )

    # Create Admin
    admin = conn.execute(
        "SELECT * FROM users WHERE username='admin'"
    ).fetchone()

    if not admin:
        conn.execute(
            """
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
            """,
            (
                "admin",
                generate_password_hash("admin123"),
                "admin"
            )
        )

    # Create Staff
    staff = conn.execute(
        "SELECT * FROM users WHERE username='staff'"
    ).fetchone()

    if not staff:
        conn.execute(
            """
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
            """,
            (
                "staff",
                generate_password_hash("staff123"),
                "staff"
            )
        )

    conn.commit()
    conn.close()


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("index"))

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- DASHBOARD ----------------

@app.route("/")
def index():

    if "user_id" not in session:
        return redirect(url_for("login"))

    status = request.args.get("status", "")

    conn = get_db()

    if session["role"] == "admin":

        if status in STATUSES:
            orders = conn.execute(
                """
                SELECT *
                FROM orders
                WHERE status=?
                ORDER BY id ASC
                """,
                (status,)
            ).fetchall()

        else:
            orders = conn.execute(
                """
                SELECT *
                FROM orders
                ORDER BY id ASC
                """
            ).fetchall()

    else:

        if status in STATUSES:
            orders = conn.execute(
                """
                SELECT
                    id,
                    customer,
                    order_type,
                    items,
                    total,
                    status,
                    created_at
                FROM orders
                WHERE status=?
                ORDER BY id ASC
                """,
                (status,)
            ).fetchall()

        else:
            orders = conn.execute(
                """
                SELECT
                    id,
                    customer,
                    order_type,
                    items,
                    total,
                    status,
                    created_at
                FROM orders
                ORDER BY id ASC
                """
            ).fetchall()

    counts = {
        s: conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status=?",
            (s,)
        ).fetchone()[0]
        for s in STATUSES
    }

    conn.close()

    return render_template(
        "index.html",
        orders=orders,
        counts=counts,
        statuses=STATUSES,
        order_types=ORDER_TYPES,
        selected=status
    )


# ---------------- PHONE VALIDATION ----------------

def valid_phone(phone):
    return (
        phone.isdigit()
        and len(phone) == 10
        and 1000000000 <= int(phone) <= 9999999999
    )


# ---------------- ADD ORDER ----------------

@app.route("/add", methods=["POST"])
def add_order():

    if "user_id" not in session:
        return redirect(url_for("login"))

    customer = request.form["customer"].strip()
    phone = request.form["phone"].strip()
    address = request.form["address"].strip()
    order_type = request.form["order_type"]
    items = request.form["items"].strip()

    # Validate phone number
    if not valid_phone(phone):
        return redirect(url_for("index"))

    total = float(request.form["total"] or 0)

    conn = get_db()

    conn.execute(
        """
        INSERT INTO orders
        (
            customer,
            phone,
            address,
            order_type,
            items,
            total,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'Created', ?)
        """,
        (
            customer,
            phone,
            address,
            order_type,
            items,
            total,
            datetime.now().strftime(
                "%d %b %Y, %I:%M %p"
            )
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("index"))


# ---------------- EDIT ORDER ----------------

@app.route("/edit/<int:order_id>", methods=["GET", "POST"])
def edit_order(order_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Only Admin can edit
    if session["role"] != "admin":
        return redirect(url_for("index"))

    conn = get_db()

    order = conn.execute(
        "SELECT * FROM orders WHERE id=?",
        (order_id,)
    ).fetchone()

    if not order:
        conn.close()
        return redirect(url_for("index"))

    if request.method == "POST":

        customer = request.form["customer"].strip()
        phone = request.form["phone"].strip()
        address = request.form["address"].strip()
        order_type = request.form["order_type"]
        items = request.form["items"].strip()

        # Validate phone
        if not valid_phone(phone):
            conn.close()

            return render_template(
                "edit_order.html",
                order=order,
                order_types=ORDER_TYPES,
                error="Phone number must contain exactly 10 digits."
            )

        total = float(request.form["total"] or 0)

        conn.execute(
            """
            UPDATE orders
            SET
                customer=?,
                phone=?,
                address=?,
                order_type=?,
                items=?,
                total=?
            WHERE id=?
            """,
            (
                customer,
                phone,
                address,
                order_type,
                items,
                total,
                order_id
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("index"))

    conn.close()

    return render_template(
        "edit_order.html",
        order=order,
        order_types=ORDER_TYPES
    )


# ---------------- ADVANCE ORDER ----------------

@app.route("/advance/<int:order_id>", methods=["POST"])
def advance(order_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    order = conn.execute(
        "SELECT status FROM orders WHERE id=?",
        (order_id,)
    ).fetchone()

    if order:

        i = STATUSES.index(order["status"])

        if i < len(STATUSES) - 1:

            conn.execute(
                """
                UPDATE orders
                SET status=?
                WHERE id=?
                """,
                (
                    STATUSES[i + 1],
                    order_id
                )
            )

            conn.commit()

    conn.close()

    return redirect(
        request.referrer or url_for("index")
    )


# ---------------- DELETE ORDER ----------------

@app.route("/delete/<int:order_id>", methods=["POST"])
def delete(order_id):

    if "user_id" not in session:
        return redirect(url_for("index"))

    conn = get_db()

    conn.execute(
        "DELETE FROM orders WHERE id=?",
        (order_id,)
    )

    conn.commit()
    conn.close()

    return redirect(
        request.referrer or url_for("index")
    )


# ---------------- RUN ----------------

if __name__ == "__main__":

    init_db()

    app.run(
        debug=False,
        use_reloader=False,
        port=5000
    )