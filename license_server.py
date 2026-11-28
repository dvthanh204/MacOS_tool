"""
Module: license_server.py
Máy chủ quản lý bản quyền Auto-Lock & Thu hồi từ xa (Flask + SQLite) cho macOS & Windows
Tương thích hoàn toàn với kiến trúc của LockSlide Studio:
- Nhận diện và tự động ghim thiết bị Mac đầu tiên mở bài giảng (First-Run Auto-Lock / TOFU)
- Chặn tuyệt đối máy tính thứ 2 nếu khách hàng chuyển tiếp file cho người khác
- Thu hồi bản quyền tức thì (Remote Kill-Switch / Revocation)
- Cho phép khách đổi sang máy khác (Device Reset)
- Khôi phục bản quyền sau khi đã thu hồi (Restore)
- Cung cấp giao diện Web Dashboard quản lý trực quan
- Hỗ trợ cả giao thức GET (chuẩn Google Apps Script) và POST JSON (/api/verify_or_bind)
"""

import os
import sys
import sqlite3
import datetime
import threading
from flask import Flask, request, jsonify, render_template_string

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
DB_FILE = os.path.join(get_app_dir(), "licenses.db")
_db_lock = threading.Lock()


def init_db():
    with _db_lock:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    license_id TEXT PRIMARY KEY,
                    title TEXT,
                    bound_hwid TEXT,
                    status TEXT DEFAULT 'PENDING',
                    created_at TEXT,
                    activated_at TEXT,
                    last_ip TEXT
                )
            """)
            conn.commit()

init_db()


@app.route("/", methods=["GET", "POST"])
def dashboard_or_api():
    """Nếu request chứa tham số bản quyền (chuẩn Google Apps Script), xử lý kích hoạt. Ngược lại hiển thị Dashboard."""
    if request.args.get("action") or request.args.get("license_id"):
        return verify_or_bind()
    return dashboard()


def dashboard():
    """Giao diện Web Dashboard quản lý bản quyền bài giảng"""
    with _db_lock:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT license_id, title, bound_hwid, status, created_at, activated_at, last_ip FROM licenses ORDER BY created_at DESC")
            rows = cursor.fetchall()

    html = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <title>LockSlide Studio - Bảng Điều Khiển Bản Quyền</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0A0E17; color: #E2E8F0; margin: 0; padding: 24px; }
            h1 { color: #38BDF8; font-size: 20px; font-weight: 800; letter-spacing: 1px; }
            table { width: 100%; border-collapse: collapse; margin-top: 16px; background-color: #0E1524; border-radius: 8px; overflow: hidden; border: 1px solid #1E293B; }
            th { background-color: #111827; color: #94A3B8; text-align: left; padding: 12px; font-size: 11px; text-transform: uppercase; }
            td { padding: 12px; border-bottom: 1px solid #1E293B; font-size: 12px; }
            tr:hover { background-color: #161F30; }
            .badge-act { background-color: rgba(16, 185, 129, 0.2); color: #34D399; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
            .badge-pen { background-color: rgba(245, 158, 11, 0.2); color: #FBBF24; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
            .badge-rev { background-color: rgba(239, 68, 68, 0.2); color: #F87171; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
            .btn { padding: 6px 12px; border-radius: 6px; border: none; font-size: 11px; font-weight: bold; cursor: pointer; text-decoration: none; margin-right: 4px; }
            .btn-rev { background-color: #EF4444; color: white; }
            .btn-res { background-color: #3B82F6; color: white; }
            .btn-rst { background-color: #10B981; color: white; }
        </style>
    </head>
    <body>
        <h1> LOCKSLIDE STUDIO // QUẢN TRỊ BẢN QUYỀN TRÊN MACOS & WINDOWS</h1>
        <table>
            <thead>
                <tr>
                    <th>Mã License</th>
                    <th>Tên Bài Giảng</th>
                    <th>Mã Máy Đã Ghim (HWID)</th>
                    <th>Trạng Thái</th>
                    <th>Ngày Tạo</th>
                    <th>Ngày Kích Hoạt</th>
                    <th>IP Gần Nhất</th>
                    <th>Hành Động</th>
                </tr>
            </thead>
            <tbody>
                {% for r in rows %}
                <tr>
                    <td style="font-family: monospace; color: #38BDF8; font-weight: bold;">{{ r[0] }}</td>
                    <td>{{ r[1] }}</td>
                    <td style="font-family: monospace; color: #E2E8F0;">{{ r[2] or 'Chưa kích hoạt' }}</td>
                    <td>
                        {% if r[3] == 'ACTIVATED' %}<span class="badge-act">ACTIVATED</span>
                        {% elif r[3] == 'PENDING' %}<span class="badge-pen">PENDING</span>
                        {% else %}<span class="badge-rev">{{ r[3] }}</span>{% endif %}
                    </td>
                    <td>{{ r[4] }}</td>
                    <td>{{ r[5] or '-' }}</td>
                    <td>{{ r[6] or '-' }}</td>
                    <td>
                        <a href="/action/revoke?id={{ r[0] }}" class="btn btn-rev">Thu hồi</a>
                        <a href="/action/reset?id={{ r[0] }}" class="btn btn-res">Đổi máy</a>
                        <a href="/action/restore?id={{ r[0] }}" class="btn btn-rst">Khôi phục</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </body>
    </html>
    """
    return render_template_string(html, rows=rows)


@app.route("/api/verify_or_bind", methods=["GET", "POST"])
def verify_or_bind():
    """
    API cốt lõi: Xác thực hoặc Tự động ghim thiết bị (TOFU - Trust On First Use)
    Hỗ trợ cả POST JSON và GET query parameters (tương thích Google Apps Script).
    """
    data = {}
    if request.method == "POST":
        try:
            data = request.get_json(force=True, silent=True) or {}
        except Exception:
            data = {}
    if not data:
        data = request.args.to_dict()

    license_id = data.get("license_id", "").strip().upper()
    hwid = data.get("hwid", "").strip().upper()
    title = data.get("title", "").strip()
    client_ip = request.remote_addr

    if not license_id or not hwid:
        return jsonify({"status": "ERROR", "message": "Thiếu mã License hoặc mã máy HWID"}), 400

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with _db_lock:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT bound_hwid, status, title FROM licenses WHERE license_id = ?", (license_id,))
            row = cursor.fetchone()

            if not row:
                # Nếu chưa có mã trong DB -> Tự động thêm với trạng thái PENDING
                cursor.execute("""
                    INSERT INTO licenses (license_id, title, status, created_at)
                    VALUES (?, ?, 'PENDING', ?)
                """, (license_id, title, now_str))
                bound_hwid = None
                status = "PENDING"
            else:
                bound_hwid, status, existing_title = row

            if status == "REVOKED":
                return jsonify({
                    "status": "REJECTED",
                    "message": "Bản quyền bài giảng này đã bị thu hồi bởi tác giả! Không thể truy cập.",
                    "bound_hwid": bound_hwid or ""
                }), 403

            # Trường hợp 1: Mở lần đầu tiên (PENDING) -> Tự động ghim vào máy tính này
            if status == "PENDING" or not bound_hwid:
                cursor.execute("""
                    UPDATE licenses
                    SET bound_hwid = ?, status = 'ACTIVATED', activated_at = ?, last_ip = ?
                    WHERE license_id = ?
                """, (hwid, now_str, client_ip, license_id))
                conn.commit()
                return jsonify({
                    "status": "SUCCESS",
                    "message": "Đã tự động ghim bản quyền bài giảng vào thiết bị này!",
                    "license_id": license_id,
                    "bound_hwid": hwid
                })

            # Trường hợp 2: Đã kích hoạt trước đó -> Kiểm tra có đúng mã máy không
            if bound_hwid.replace("-", "").upper() == hwid.replace("-", "").upper():
                cursor.execute("UPDATE licenses SET last_ip = ? WHERE license_id = ?", (client_ip, license_id))
                conn.commit()
                return jsonify({
                    "status": "SUCCESS",
                    "message": "Bản quyền hợp lệ!",
                    "license_id": license_id,
                    "bound_hwid": bound_hwid
                })
            else:
                # BỊ TỪ CHỐI: Máy thứ 2 cố tình mở
                return jsonify({
                    "status": "REJECTED",
                    "message": "Lượt mở của bài giảng này đã được sử dụng hết trên một máy MacBook khác!",
                    "bound_hwid": bound_hwid,
                    "attempted_hwid": hwid
                }), 403


@app.route("/action/revoke")
def action_revoke():
    lic_id = request.args.get("id", "").strip().upper()
    if lic_id:
        with _db_lock:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("UPDATE licenses SET status = 'REVOKED' WHERE license_id = ?", (lic_id,))
    return "<script>location.href='/';</script>"


@app.route("/action/reset")
def action_reset():
    lic_id = request.args.get("id", "").strip().upper()
    if lic_id:
        with _db_lock:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("UPDATE licenses SET bound_hwid = NULL, status = 'PENDING', activated_at = NULL WHERE license_id = ?", (lic_id,))
    return "<script>location.href='/';</script>"


@app.route("/action/restore")
def action_restore():
    lic_id = request.args.get("id", "").strip().upper()
    if lic_id:
        with _db_lock:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("UPDATE licenses SET status = 'ACTIVATED' WHERE license_id = ?", (lic_id,))
    return "<script>location.href='/';</script>"


def start_server_in_background(host="127.0.0.1", port=5000):
    t = threading.Thread(target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False), daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
