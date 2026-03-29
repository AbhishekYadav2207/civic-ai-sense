from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "database", "complaints.db")

# ---------------- DB CONNECTION ----------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- PRIORITY PREDICTION ----------------
def predict_priority(complaint_text, category):
    text = complaint_text.lower()
    category = category.lower()

    high_keywords = [
        "gas leak", "fire", "electrocution", "death", "accident",
        "electric shock", "short circuit", "live wire", "emergency"
    ]

    medium_keywords = [
        "street light", "water", "garbage", "drainage", "road",
        "pothole", "sewage", "leakage", "tap leakage", "tap", "pipeline",
        "overflow", "power cut", "electricity", "transformer"
    ]

    if any(word in text for word in high_keywords):
        return "High"

    if any(word in text for word in medium_keywords):
        return "Medium"

    if len(text.split()) > 2 and category in ["water", "garbage", "road", "street light", "safety"]:
        return "Medium"

    return "Low"

# ---------------- DEPARTMENT ASSIGNMENT ----------------
def assign_department(complaint_text, category):
    text = complaint_text.lower()
    category = category.lower()

    # 1. Strong text-based emergency rules first
    if any(word in text for word in [
        "gas leak", "fire", "accident", "electrocution",
        "electric shock", "live wire", "emergency"
    ]):
        return "Emergency Department"

    # 2. Strong text-based department rules
    elif any(word in text for word in [
        "water", "drainage", "tap leakage", "tap", "pipeline",
        "sewage", "overflow", "leakage"
    ]):
        return "Water Department"

    elif any(word in text for word in [
        "garbage", "waste", "dustbin", "sanitation"
    ]):
        return "Sanitation Department"

    elif any(word in text for word in [
        "street light", "electricity", "power", "transformer",
        "short circuit"
    ]):
        return "Electricity Department"

    elif any(word in text for word in [
        "road", "pothole", "street damage", "road crack"
    ]):
        return "Roads Department"

    # 3. If text is unclear, use category as fallback
    if category == "water":
        return "Water Department"
    elif category == "garbage":
        return "Sanitation Department"
    elif category == "street light":
        return "Electricity Department"
    elif category == "road":
        return "Roads Department"
    elif category == "safety":
        return "Emergency Department"

    return "General Department"

# ---------------- CREATE TABLE ----------------
def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint TEXT,
            category TEXT,
            priority TEXT DEFAULT 'Low',
            department TEXT DEFAULT 'General Department',
            created_at TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)
    conn.commit()
    conn.close()

# ---------------- FLASK APP ----------------
app = Flask(__name__)
CORS(app)

# Create table when server starts
create_table()

@app.route('/')
def home():
    return jsonify({"message": "Backend Working"})

# ---------------- SUBMIT COMPLAINT ----------------
@app.route('/submit-complaint', methods=['POST'])
def submit_complaint():
    data = request.get_json()

    complaint_text = data.get("complaint")
    category = data.get("category")

    if not complaint_text or not category:
        return jsonify({"error": "Complaint or category missing"}), 400

    priority = predict_priority(complaint_text, category)
    department = assign_department(complaint_text, category)
    created_at = datetime.now().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO complaints (complaint, category, status, priority, department, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (complaint_text, category, "Pending", priority, department, created_at))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "complaint": complaint_text,
        "category": category,
        "priority": priority,
        "department": department
    })

# ---------------- GET ALL COMPLAINTS ----------------
@app.route('/get-complaints', methods=['GET'])
def get_complaints():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, complaint, category, status, priority, department, created_at
    FROM complaints
    ORDER BY
        CASE priority
            WHEN 'High' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'Low' THEN 3
            ELSE 4
        END,
        created_at DESC
""")
    rows = cursor.fetchall()
    conn.close()

    complaints = []
    for row in rows:
        complaints.append({
            "id": row["id"],
            "complaint": row["complaint"],
            "category": row["category"],
            "status": row["status"],
            "priority": row["priority"],
            "department": row["department"],
            "created_at": row["created_at"]
        })

    return jsonify(complaints)

# ---------------- UPDATE STATUS ----------------
@app.route('/update-status/<int:complaint_id>', methods=['PUT'])
def update_status(complaint_id):
    data = request.get_json()
    new_status = data.get("status")

    if new_status not in ["Pending", "In Progress", "Resolved"]:
        return jsonify({"error": "Invalid status"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE complaints SET status = ? WHERE id = ?",
        (new_status, complaint_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Status updated"})

# ---------------- COMPLAINTS COUNT ----------------
@app.route('/complaints-count', methods=['GET'])
def complaints_count():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM complaints")
    count = cursor.fetchone()[0]
    conn.close()

    return jsonify({"total_complaints": count})

# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(debug=True)