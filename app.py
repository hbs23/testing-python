import os
import mysql.connector
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
# sengaja TIDAK pakai generate_password_hash / check_password_hash di versi vuln
# from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename  # kita sengaja nanti TIDAK pakai ini

# =========================
# VULNERABLE VERSION (UNTUK LAB / DEMO SAJA)
# =========================

load_dotenv()

app = Flask(__name__)

# batasan upload sengaja dilonggarkan
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# =========================
# Database Connection (HARD-CODED + NO ENV)
# =========================
def get_db():
    """
    VULN:
    - Hardcoded credential (bukan dari environment / secret manager)
    - Tidak pakai SSL, tidak ada timeout, dll.
    """
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", "root"),  # default root/root
        database=os.getenv("DB_NAME", "demo_app"),
    )
    return conn


# =========================
# Healthcheck (masih OK, tapi no masking error)
# =========================
@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db()
        conn.close()
        return jsonify({"status": "ok", "db": "connected"}), 200
    except Exception as e:
        # VULN: expose full exception ke client (info leakage)
        return jsonify({"status": "error", "db_error": str(e)}), 500


@app.route("/openapi.json", methods=["GET"])
def openapi_json():
    # kirim YAML tapi ZAP gak masalah, dia bisa baca YAML
    return send_from_directory(
        BASE_DIR,
        "openapi.yaml",
        mimetype="application/yaml"
    )


# =========================
# 1. LOGIN (VULN: SQLi + plaintext password)
# =========================
@app.route("/login", methods=["POST"])
def login():
    """
    Body:
    {
      "username": "admin",
      "password": "admin123"
    }

    VULN:
    - SQL Injection (username & password langsung di-embed ke query)
    - Password disimpan plaintext di DB dan dibandingkan langsung
    """
    data = request.get_json() or request.form
    username = data.get("username", "")
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"message": "username & password required"}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # VULN: raw string formatting -> SQL Injection
    query = (
        "SELECT id, username, password, email "
        "FROM users WHERE username = '%s' AND password = '%s'"
        % (username, password)
    )
    cursor.execute(query)
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return jsonify({"message": "Invalid credentials"}), 401

    # VULN: balikin sebagian data sensitif (minimal masih include username & email)
    return jsonify(
        {
            "message": "Login success (BUT INSECURE)",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                # VULN: bahkan balikin password plaintext
                "password": user["password"],
            },
        }
    )


# =========================
# 2. USER DETAIL (VULN: SQLi via path param)
# =========================
@app.route("/users/<user_id>", methods=["GET"])
def get_user(user_id):
    """
    VULN:
    - user_id diperlakukan sebagai string mentah di query
    - tidak ada auth / otorisasi
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # VULN: direct concat ke query
    query = f"SELECT id, username, email FROM users WHERE id = {user_id}"
    cursor.execute(query)
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        return jsonify(user)
    else:
        return jsonify({"message": "User not found"}), 404


# =========================
# 3. SEARCH (VULN: SQLi + reflected input)
# =========================
@app.route("/search", methods=["GET"])
def search_users():
    """
    Contoh: /search?q=admin

    VULN:
    - query parameter q langsung di-concat ke LIKE
    - hasil response meng-echo kembali input user (potensi XSS reflektif di aplikasi lain)
    """
    q = request.args.get("q", "").strip()

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # VULN: string concat -> SQL Injection
    query = "SELECT id, username, email FROM users WHERE username LIKE '%%%s%%'" % q
    cursor.execute(query)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({"query": q, "results": results})


# =========================
# 4. CHANGE PASSWORD (VULN: plaintext + no auth)
# =========================
@app.route("/change_password", methods=["POST"])
def change_password():
    """
    Body:
    {
      "user_id": 1,
      "new_password": "admin123"
    }

    VULN:
    - Password disimpan plaintext (tidak di-hash).
    - Tidak ada autentikasi (siapa saja bisa call endpoint ini).
    - user_id dipakai langsung dalam query.
    """
    data = request.get_json() or request.form
    user_id = data.get("user_id")
    new_password = data.get("new_password", "")

    if not user_id or not new_password:
        return jsonify({"message": "user_id & new_password required"}), 400

    conn = get_db()
    cursor = conn.cursor()

    # VULN: query concat + password plaintext
    query = (
        "UPDATE users SET password = '%s' WHERE id = %s"
        % (new_password, user_id)
    )
    cursor.execute(query)
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Password changed (INSECURE - PLAINTEXT)"})


# =========================
# 5. FILE UPLOAD (VULN: path traversal + no extension check)
# =========================
@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Form-data:
    - file: <file>

    VULN:
    - Tidak pakai secure_filename.
    - Tidak batasi extension (bisa upload .php, .sh, dll).
    - Menggunakan nama file langsung dari user -> potensi path traversal.
    """
    if "file" not in request.files:
        return jsonify({"message": "No file part"}), 400

    f = request.files["file"]
    if f.filename == "":
        return jsonify({"message": "No selected file"}), 400

    # VULN: tidak ada allowed extension check
    filename = f.filename  # TIDAK pakai secure_filename
    save_path = os.path.join(UPLOAD_DIR, filename)  # potensi path traversal

    f.save(save_path)

    return jsonify({"message": "File uploaded (INSECURE)", "path": save_path})


# =========================
# 6. CONFIG (VULN: expose secrets)
# =========================
@app.route("/config", methods=["GET"])
def config_info():
    """
    VULN:
    - Mengembalikan DB_USER, DB_PASS dan env lain ke client.
    """
    config = {
        "db_host": os.getenv("DB_HOST", "localhost"),
        "db_name": os.getenv("DB_NAME", "demo_app"),
        "db_user": os.getenv("DB_USER", "root"),
        "db_pass": os.getenv("DB_PASS", "root"),  # VULN: secret leak
        "app_env": os.getenv("APP_ENV", "development"),
        "all_env": dict(os.environ),  # VULN: dump semua env
    }
    return jsonify(config)


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "9500"))

    # VULN: selalu debug=True di production
    app.run(host=host, port=port, debug=True)