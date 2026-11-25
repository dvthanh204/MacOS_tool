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


@app.route("/")
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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bảng Điều Khiển Bản Quyền LockSlide Studio macOS</title>
        <style>
            * { box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0A0E17; color: #F8FAFC; padding: 25px; margin: 0; }
            .container { max-width: 1160px; margin: auto; }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1E293B; padding-bottom: 16px; margin-bottom: 24px; }
            h1 { color: #38BDF8; margin: 0; font-size: 24px; letter-spacing: 0.5px; }
            p.sub { color: #94A3B8; margin: 5px 0 0 0; font-size: 13px; }
            .card { background: #0E1524; border: 1px solid #1E293B; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.4); }
            table { width: 100%; border-collapse: collapse; text-align: left; }
            th, td { padding: 14px 18px; border-bottom: 1px solid #1A2333; font-size: 13px; }
            th { background: #111A2E; color: #00F0FF; font-weight: 700; letter-spacing: 0.5px; }
            tr:hover { background: #131E33; }
            .badge { padding: 5px 10px; border-radius: 6px; font-weight: bold; font-size: 11px; display: inline-block; }
            .badge-active { background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid #059669; }
            .badge-pending { background: rgba(245, 158, 11, 0.2); color: #FBBF24; border: 1px solid #D97706; }
            .badge-revoked { background: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid #DC2626; }
            .hwid { font-family: 'SF Mono', Menlo, Consolas, monospace; color: #38BDF8; font-weight: bold; }
            .btn { background: #1E293B; color: #F8FAFC; border: 1px solid #334155; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; text-decoration: none; display: inline-block; transition: all 0.2s; }
            .btn:hover { background: #334155; }
            .btn-danger { color: #F87171; border-color: #991B1B; background: rgba(239, 68, 68, 0.1); }
            .btn-danger:hover { background: #DC2626; color: white; }
            .btn-reset { color: #FACC15; border-color: #A16207; background: rgba(250, 204, 21, 0.1); }
            .btn-reset:hover { background: #D97706; color: white; }
            .btn-restore { color: #34D399; border-color: #059669; background: rgba(52, 211, 153, 0.1); }
            .btn-restore:hover { background: #059669; color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1> BẢNG ĐIỀU KHIỂN BẢN QUYỀN LOCKSLIDE STUDIO (MACBOOK)</h1>
                    <p class="sub">Hệ thống nhận diện & tự động ghim thiết bị Mac đầu tiên mở bài giảng (Auto-Lock on First Run)</p>
                </div>
            </div>

            <div class="card">
                <table>
                    <thead>
                        <tr>
                            <th>MÃ LICENSE</th>
                            <th>TIÊU ĐỀ BÀI GIẢNG</th>
                            <th>MÃ MÁY ĐÃ GHIM (MAC HWID)</th>
                            <th>TRẠNG THÁI</th>
                            <th>NGÀY TẠO</th>
                            <th>KÍCH HOẠT LÚC</th>
                            <th>THAO TÁC</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for r in rows %}
                        <tr>
                            <td style="font-family: 'SF Mono', Menlo, Consolas, monospace; font-weight: bold; color: #38BDF8;">{{ r[0] }}</td>
                            <td>{{ r[1] }}</td>
                            <td class="hwid">{{ r[2] if r[2] else '— Chưa mở —' }}</td>
                            <td>
                                {% if r[3] == 'ACTIVATED' %}
                                    <span class="badge badge-active">ĐÃ GHIM MÁY</span>
                                {% elif r[3] == 'PENDING' %}
                                    <span class="badge badge-pending">CHỜ MỞ LẦN ĐẦU</span>
                                {% else %}
                                    <span class="badge badge-revoked">ĐÃ THU HỒI</span>
                                {% endif %}
                            </td>
                            <td style="color: #94A3B8;">{{ r[4] }}</td>
                            <td style="color: #94A3B8;">{{ r[5] if r[5] else '—' }}</td>
                            <td>
                                {% if r[3] == 'REVOKED' %}
                                <form method="POST" action="/api/restore" style="display:inline;">
                                    <input type="hidden" name="license_id" value="{{ r[0] }}">
                                    <button type="submit" class="btn btn-restore" title="Khôi phục quyền mở bài giảng">Khôi phục</button>
                                </form>
                                {% else %}
                                {% if r[2] %}
                                <form method="POST" action="/api/reset" style="display:inline;">
                                    <input type="hidden" name="license_id" value="{{ r[0] }}">
                                    <button type="submit" class="btn btn-reset" title="Cho phép khách đổi sang máy Mac khác">Đổi máy</button>
                                </form>
                                {% endif %}
                                <form method="POST" action="/api/revoke" style="display:inline;">
                                    <input type="hidden" name="license_id" value="{{ r[0] }}">
                                    <button type="submit" class="btn btn-danger" title="Thu hồi bản quyền - Chặn mở bài">Thu hồi</button>
                                </form>
                                {% endif %}
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="7" style="text-align: center; color: #64748B; padding: 30px;">Chưa có tài liệu nào được mã hóa trong hệ thống.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, rows=rows)


@app.route("/api/verify_or_bind", methods=["POST"])
def verify_or_bind():
    """
    API cốt lõi: Xác thực hoặc Tự động ghim thiết bị (TOFU - Trust On First Use)
    """
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"status": "error", "message": "Dữ liệu JSON không hợp lệ"}), 400

    license_id = data.get("license_id", "").strip().upper()
    hwid = data.get("hwid", "").strip().upper()
    title = data.get("title", "").strip()
    client_ip = request.remote_addr

    if not license_id or not hwid:
        return jsonify({"status": "error", "message": "Thiếu mã License hoặc mã máy HWID"}), 400

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
                    "status": "error",
                    "message": "Bản quyền bài giảng này đã bị thu hồi bởi tác giả! Không thể truy cập."
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
                    "status": "success",
                    "message": "Đã tự động ghim bản quyền bài giảng vào thiết bị này!",
                    "license_id": license_id,
                    "bound_hwid": hwid
                })

            # Trường hợp 2: Đã kích hoạt trước đó -> Kiểm tra có đúng mã máy không
            if bound_hwid.replace("-", "").upper() == hwid.replace("-", "").upper():
                cursor.execute("UPDATE licenses SET last_ip = ? WHERE license_id = ?", (client_ip, license_id))
                conn.commit()
                return jsonify({
                    "status": "success",
                    "message": "Bản quyền hợp lệ! Cho phép mở bài giảng.",
                    "license_id": license_id,
                    "bound_hwid": bound_hwid
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": (
                        f"BẢN QUYỀN ĐÃ ĐƯỢC KÍCH HOẠT TRÊN THIẾT BỊ KHÁC!\n\n"
                        f"Mã máy hợp lệ: {bound_hwid}\n"
                        f"Mã máy của bạn: {hwid}\n"
                        f"Hệ thống không cho phép chia sẻ file cho người khác."
                    )
                }), 403


@app.route("/api/revoke", methods=["POST"])
def revoke_license():
    license_id = (request.form.get("license_id") or (request.json and request.json.get("license_id")) or "").strip().upper()
    if not license_id:
        return jsonify({"status": "error", "message": "Thiếu license_id"}), 400

    with _db_lock:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE licenses SET status = 'REVOKED' WHERE license_id = ?", (license_id,))
            conn.commit()

    if request.form:
        from flask import redirect
        return redirect("/")
    return jsonify({"status": "success", "message": f"Đã thu hồi bản quyền {license_id}"})


@app.route("/api/reset", methods=["POST"])
def reset_license():
    """Cho phép khách đổi sang máy khác (xóa bound_hwid để máy mới ghim lại)"""
    license_id = (request.form.get("license_id") or (request.json and request.json.get("license_id")) or "").strip().upper()
    if not license_id:
        return jsonify({"status": "error", "message": "Thiếu license_id"}), 400

    with _db_lock:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE licenses SET bound_hwid = NULL, status = 'PENDING', activated_at = NULL WHERE license_id = ?", (license_id,))
            conn.commit()

    if request.form:
        from flask import redirect
        return redirect("/")
    return jsonify({"status": "success", "message": f"Đã reset thiết bị cho {license_id}. Khách có thể mở trên máy Mac mới."})


@app.route("/api/restore", methods=["POST"])
def restore_license():
    license_id = (request.form.get("license_id") or (request.json and request.json.get("license_id")) or "").strip().upper()
    if not license_id:
        return jsonify({"status": "error", "message": "Thiếu license_id"}), 400

    with _db_lock:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT bound_hwid FROM licenses WHERE license_id = ?", (license_id,))
            row = cursor.fetchone()
            new_status = "ACTIVATED" if row and row[0] else "PENDING"
            cursor.execute("UPDATE licenses SET status = ? WHERE license_id = ?", (new_status, license_id))
            conn.commit()

    if request.form:
        from flask import redirect
        return redirect("/")
    return jsonify({"status": "success", "message": f"Đã khôi phục bản quyền {license_id}"})


def start_server_in_background(host="0.0.0.0", port=5000):
    t = threading.Thread(target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False), daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[*] LockSlide Server đang chạy tại http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
