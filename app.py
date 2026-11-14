"""
Money OS — Flask Backend Application
A personal budgeting tool for university students and first-time earners in Malaysia.
"""

import os
import re
import html
import sqlite3
import csv
import io
from flask import Flask, request, jsonify, render_template, Response, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize Flask App
app = Flask(__name__)

# Configuration from Environment Variables
def get_db_path():
    return os.environ.get("DATABASE_PATH", "money_os.db")

def get_admin_password():
    return os.environ.get("ADMIN_PASSWORD", "admin123")

PORT = int(os.environ.get("PORT", 5000))

# Initialize Rate Limiter: 10 per minute for write endpoints
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

# Email validation regex (RFC 5322 compatible simplified pattern)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


# --------------------------------------------------------------------------
# Database Setup & Connection Helper
# --------------------------------------------------------------------------
def get_db():
    """
    Establish a connection to the SQLite database.
    Row factory enables dict-like attribute access.
    """
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initialize database schema automatically on application startup.
    Creates tables for waitlist, questions, and budgets if they don't exist.
    """
    conn = get_db()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                income REAL NOT NULL,
                needs REAL NOT NULL,
                wants REAL NOT NULL,
                savings REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.close()


# Ensure tables exist at startup
init_db()


# --------------------------------------------------------------------------
# Custom Error Handlers
# --------------------------------------------------------------------------
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded with standardized JSON error."""
    return jsonify({
        "error": "Rate limit exceeded. You may only make 10 requests per minute. Please wait a moment."
    }), 429


@app.errorhandler(404)
def not_found_handler(e):
    """
    Serve styled 404 page for browser navigation,
    or JSON error if the client requested an API endpoint.
    """
    if request.path.startswith("/api/"):
        return jsonify({"error": "Resource not found"}), 404
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error_handler(e):
    """Handle unexpected server errors gracefully."""
    return jsonify({"error": "Internal server error. Please try again later."}), 500


# --------------------------------------------------------------------------
# Application Routes
# --------------------------------------------------------------------------

# 1. Main Welcome Page
@app.route("/", methods=["GET"])
def index():
    """Serve the primary Money OS landing page."""
    return render_template("index.html")


# 2. Health Check
@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for Render monitoring and uptime checks."""
    return jsonify({"status": "ok"}), 200


# 3. Budget Calculation & Persistence API
@app.route("/api/budget", methods=["POST"])
@limiter.limit("10 per minute")
def create_budget():
    """
    Calculate and persist a 50/30/20 budget breakdown.
    Validates income is between 0 and 1,000,000 RM.
    Returns calculated values rounded to 2 decimal places.
    """
    data = request.get_json(silent=True)
    if not data or "income" not in data:
        return jsonify({"error": "Missing 'income' in request body."}), 400

    try:
        income = float(data["income"])
    except (ValueError, TypeError):
        return jsonify({"error": "Income must be a valid number."}), 400

    if income < 0 or income > 1000000:
        return jsonify({"error": "Income must be between 0 and 1,000,000 RM."}), 400

    # Calculate 50% Needs, 30% Wants, 20% Savings
    needs = round(income * 0.50, 2)
    wants = round(income * 0.30, 2)
    savings = round(income * 0.20, 2)

    # Persist calculation record using parameterized SQL
    conn = get_db()
    with conn:
        conn.execute(
            "INSERT INTO budgets (income, needs, wants, savings) VALUES (?, ?, ?, ?)",
            (income, needs, wants, savings)
        )
    conn.close()

    return jsonify({
        "income": income,
        "needs": needs,
        "wants": wants,
        "savings": savings
    }), 200


# 4. Waitlist Signup API
@app.route("/api/waitlist", methods=["POST"])
@limiter.limit("10 per minute")
def join_waitlist():
    """
    Add a user to the student early-access waitlist.
    Validates email syntax and rejects duplicates with a 409 Conflict.
    """
    data = request.get_json(silent=True)
    if not data or "email" not in data:
        return jsonify({"error": "Missing 'email' field in request body."}), 400

    email = str(data["email"]).strip().lower()

    if not EMAIL_REGEX.match(email):
        return jsonify({"error": "Please provide a valid email address (e.g. name@student.edu.my)."}), 400

    conn = get_db()
    try:
        with conn:
            conn.execute(
                "INSERT INTO waitlist (email) VALUES (?)",
                (email,)
            )
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({
            "error": "You are already on the waitlist! We will notify you soon."
        }), 409
    finally:
        conn.close()

    return jsonify({
        "message": "Welcome to the waitlist! You're in."
    }), 201


# 5. Question Submission API
@app.route("/api/questions", methods=["POST"])
@limiter.limit("10 per minute")
def submit_question():
    """
    Receive questions from university students and beginners.
    Requires name, valid email, and message between 10 and 1000 characters.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON request payload."}), 400

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    message = str(data.get("message", "")).strip()

    if not name:
        return jsonify({"error": "Please provide your name."}), 400

    if not email or not EMAIL_REGEX.match(email):
        return jsonify({"error": "Please provide a valid email address."}), 400

    if len(message) < 10 or len(message) > 1000:
        return jsonify({"error": "Message must be between 10 and 1000 characters."}), 400

    # Escape HTML to prevent XSS attacks when stored or rendered in admin
    clean_name = html.escape(name)
    clean_email = html.escape(email)
    clean_message = html.escape(message)

    conn = get_db()
    with conn:
        conn.execute(
            "INSERT INTO questions (name, email, message) VALUES (?, ?, ?)",
            (clean_name, clean_email, clean_message)
        )
    conn.close()

    return jsonify({
        "message": "Thank you! Your question has been received. We will respond shortly."
    }), 201


# 6. Public Aggregated Statistics API
@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Return public counts of waitlist entries and budgets created."""
    conn = get_db()
    waitlist_count = conn.execute("SELECT COUNT(*) FROM waitlist").fetchone()[0]
    budgets_count = conn.execute("SELECT COUNT(*) FROM budgets").fetchone()[0]
    conn.close()

    return jsonify({
        "waitlist_count": waitlist_count,
        "budgets_created": budgets_count
    }), 200


# --------------------------------------------------------------------------
# Admin Dashboard & CSV Export
# --------------------------------------------------------------------------
def check_admin_auth():
    """Helper to verify HTTP Basic authentication for the admin route."""
    auth = request.authorization
    if not auth or auth.password != get_admin_password():
        return False
    return True


@app.route("/admin/waitlist", methods=["GET"])
def admin_waitlist():
    """
    Protected Admin Dashboard.
    Displays waitlist entries, submitted questions, and a CSV download button.
    """
    if not check_admin_auth():
        return Response(
            "Authentication required for Money OS Admin.",
            401,
            {"WWW-Authenticate": 'Basic realm="Money OS Admin"'}
        )

    conn = get_db()
    waitlist = conn.execute("SELECT * FROM waitlist ORDER BY id DESC").fetchall()
    questions = conn.execute("SELECT * FROM questions ORDER BY id DESC").fetchall()
    budgets_count = conn.execute("SELECT COUNT(*) FROM budgets").fetchone()[0]
    conn.close()

    # Render clean HTML admin table
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Money OS — Admin Dashboard</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body class="admin-body">
  <div class="admin-card">
    <div style="display: flex; justify-content: space-between; align-items: baseline; border-bottom: 2px solid var(--ink); padding-bottom: 1rem;">
      <div>
        <h1 style="font-size: 2rem;">Money OS Administration</h1>
        <p style="color: #4a537d; font-family: var(--font-receipt); font-size: 0.85rem;">System overview and visitor submissions</p>
      </div>
      <div>
        <a href="/admin/export-csv" class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.85rem;">Download CSV</a>
        <a href="/" class="btn btn-secondary" style="padding: 0.5rem 1rem; font-size: 0.85rem; margin-left: 0.5rem;">View Site</a>
      </div>
    </div>

    <div style="display: flex; gap: 1.5rem; margin-top: 1.5rem;">
      <div style="flex: 1; padding: 1.25rem; background: #EEF0FF; border: 2px solid var(--ink);">
        <span style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase;">Waitlist Signups</span>
        <h2 style="font-size: 2.2rem; color: var(--cobalt);">{len(waitlist)}</h2>
      </div>
      <div style="flex: 1; padding: 1.25rem; background: #EEF0FF; border: 2px solid var(--ink);">
        <span style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase;">Questions Received</span>
        <h2 style="font-size: 2.2rem; color: var(--cobalt);">{len(questions)}</h2>
      </div>
      <div style="flex: 1; padding: 1.25rem; background: #EEF0FF; border: 2px solid var(--ink);">
        <span style="font-size: 0.8rem; font-weight: 700; text-transform: uppercase;">Total Budgets Calculated</span>
        <h2 style="font-size: 2.2rem; color: var(--cobalt);">{budgets_count}</h2>
      </div>
    </div>

    <h2 style="margin-top: 2.5rem; font-size: 1.5rem;">Waitlist ({len(waitlist)})</h2>
    <table class="admin-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Email Address</th>
          <th>Joined At (UTC)</th>
        </tr>
      </thead>
      <tbody>
        {"".join(f"<tr><td>{w['id']}</td><td>{w['email']}</td><td>{w['created_at']}</td></tr>" for w in waitlist) if waitlist else "<tr><td colspan='3' style='text-align: center; color: #666;'>No waitlist entries yet.</td></tr>"}
      </tbody>
    </table>

    <h2 style="margin-top: 2.5rem; font-size: 1.5rem;">Questions ({len(questions)})</h2>
    <table class="admin-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>Email</th>
          <th>Message</th>
          <th>Date</th>
        </tr>
      </thead>
      <tbody>
        {"".join(f"<tr><td>{q['id']}</td><td>{q['name']}</td><td>{q['email']}</td><td>{q['message']}</td><td>{q['created_at']}</td></tr>" for q in questions) if questions else "<tr><td colspan='5' style='text-align: center; color: #666;'>No questions submitted yet.</td></tr>"}
      </tbody>
    </table>
  </div>
</body>
</html>"""
    return html_content, 200


@app.route("/admin/export-csv", methods=["GET"])
def export_csv():
    """Generate and download a CSV file of waitlist signups."""
    if not check_admin_auth():
        return Response(
            "Authentication required for Money OS Admin.",
            401,
            {"WWW-Authenticate": 'Basic realm="Money OS Admin"'}
        )

    conn = get_db()
    waitlist = conn.execute("SELECT id, email, created_at FROM waitlist ORDER BY id ASC").fetchall()
    conn.close()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["ID", "Email", "Joined At (UTC)"])
    for row in waitlist:
        cw.writerow([row["id"], row["email"], row["created_at"]])

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=money_os_waitlist.csv"}
    )


# --------------------------------------------------------------------------
# Main Execution Entry Point
# --------------------------------------------------------------------------
if __name__ == "__main__":
    # Never run with debug=True in production environments
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=PORT, debug=debug_mode)
