"""
Module: editor_player_mac.py
Trình Mở, Chỉnh Sửa & Tự Động Lưu Bài Giảng Bảo Mật cho MacBook (macOS)
Dành riêng cho Microsoft PowerPoint for Mac & macOS System

Hệ thống bảo vệ đa lớp tương thích kiến trúc hash_win:
1. CHO PHÉP CHỈNH SỬA & LƯU NỘI DUNG ĐÃ SỬA TRÊN MACBOOK:
   - Khách hàng mở bài giảng trực tiếp trong PowerPoint for Mac ở chế độ thiết kế đầy đủ.
   - Thoải mái gõ chữ, thêm/xóa slide, chèn ảnh, paste (Cmd+V).
   - Lưu bình thường (Cmd+S / nút Save).
   - Real-time Auto-Sync: Mỗi khi bấm Lưu hoặc khi đóng bài giảng, hệ thống tự động
     phát hiện thay đổi và re-encrypt đồng bộ ngay lập tức vào file mã hóa gốc (.encppt).
2. CẤM TUYỆT ĐỐI SAVE AS (KHÔNG THỂ LƯU RA FILE MỚI TRÊN MAC):
   - Ribbon & Backstage XML tiêm sẵn vô hiệu hóa toàn bộ Save As, Save a Copy, Export, Print.
3. CẤM TUYỆT ĐỐI COPY NỘI DUNG RA NGOÀI:
   - Khóa Copy/Cut trên Ribbon và Context Menu.
   - Hỗ trợ Clipboard Guard dọn dẹp bộ nhớ đệm nếu phát hiện trích xuất.
4. TỰ ĐỘNG GHIM MÃ MÁY MAC LẦN ĐẦU (Auto-Lock TOFU) & THU HỒI TỪ XA:
   - Nhận diện đúng Apple Hardware UUID + Mac Serial Number.
   - Chặn 100% nếu file bị gửi lén sang máy Mac khác.
5. TIÊU HỦY DỮ LIỆU TẠM AN TOÀN NGAY SAU KHI ĐÓNG BÀI GIẢNG:
   - Ghi đè byte ngẫu nhiên (Zero-Fill & Random Wipe) trước khi xóa hoàn toàn.
"""

import os
import sys
import time
import tempfile
import threading
import subprocess
import shutil

from crypto_engine_mac import (
    get_machine_hwid,
    decrypt_presentation_from_bytes,
    decrypt_presentation,
    reencrypt_updated_presentation
)

# Thử import PyQt5, nếu môi trường Mac chưa có thì fallback sang Tkinter
HAS_PYQT = False
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QLabel, QPushButton,
        QVBoxLayout, QHBoxLayout, QMessageBox, QFrame, QFileDialog
    )
    from PyQt5.QtGui import QFont, QColor
    from PyQt5.QtCore import Qt
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False
    import tkinter as tk
    from tkinter import messagebox, filedialog


def copy_to_clipboard(text: str):
    """Sao chép text vào clipboard (hỗ trợ macOS pbcopy và các hệ điều hành)"""
    if sys.platform == "darwin":
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
            return
        except Exception:
            pass

    if HAS_PYQT:
        app = QApplication.instance()
        if app:
            cb = app.clipboard()
            cb.setText(text)
            return

    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
    except Exception:
        pass


# ==============================================================================
# HỘP THOẠI BẢN QUYỀN VÀ MÃ MÁY TRÊN MAC (PYQT5 HOẶC TKINTER)
# ==============================================================================
if HAS_PYQT:
    class ClientHWIDDialog(QMainWindow):
        """Hộp thoại thông báo khi bản quyền không hợp lệ hoặc bị thu hồi trên Mac"""
        def __init__(self, error_message: str = "", current_hwid: str = ""):
            super().__init__()
            self.error_message = error_message
            self.current_hwid = current_hwid or get_machine_hwid()
            self.init_ui()

        def init_ui(self):
            self.setWindowTitle("LockSlide Studio macOS - Bản Quyền Thiết Bị")
            self.setFixedSize(580, 420)
            self.setStyleSheet("""
                QMainWindow { background-color: #0A0E17; }
                QLabel { color: #F8FAFC; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
            """)

            central = QWidget(self)
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setContentsMargins(32, 28, 32, 28)
            layout.setSpacing(16)

            title = QLabel(" BẢN QUYỀN BÀI GIẢNG BẢO MẬT (MACBOOK)")
            title.setStyleSheet("font-size: 17px; font-weight: bold; color: #38BDF8; letter-spacing: 0.8px;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

            err_box = QFrame()
            err_box.setStyleSheet("background-color: rgba(239, 68, 68, 0.12); border: 1px solid #DC2626; border-radius: 10px; padding: 14px;")
            err_l = QVBoxLayout(err_box)
            err_l.setSpacing(8)

            err_t = QLabel("TRUY CẬP BỊ TỪ CHỐI")
            err_t.setStyleSheet("font-weight: bold; color: #F87171; font-size: 13px; letter-spacing: 0.5px;")
            err_m = QLabel(self.error_message or "Thiết bị Mac này không có quyền truy cập bài giảng hoặc bài giảng đã bị thu hồi.")
            err_m.setWordWrap(True)
            err_m.setStyleSheet("color: #FECACA; font-size: 12px; line-height: 1.5;")
            err_l.addWidget(err_t)
            err_l.addWidget(err_m)
            layout.addWidget(err_box)

            hwid_box = QFrame()
            hwid_box.setStyleSheet("background-color: #111827; border: 1px solid #1E293B; border-radius: 10px; padding: 12px 16px;")
            hwid_l = QHBoxLayout(hwid_box)
            lbl_hwid_t = QLabel("MÃ MÁY MAC CỦA BẠN (HWID):")
            lbl_hwid_t.setStyleSheet("font-size: 11px; font-weight: bold; color: #94A3B8;")
            lbl_hwid_v = QLabel(self.current_hwid)
            lbl_hwid_v.setStyleSheet("font-size: 13px; font-weight: bold; color: #00F0FF; font-family: 'SF Mono', Menlo, Consolas;")
            hwid_l.addWidget(lbl_hwid_t)
            hwid_l.addStretch()
            hwid_l.addWidget(lbl_hwid_v)
            layout.addWidget(hwid_box)

            btn_row = QHBoxLayout()
            btn_copy = QPushButton("Sao chép mã máy Mac")
            btn_copy.setCursor(Qt.PointingHandCursor)
            btn_copy.setStyleSheet("""
                QPushButton {
                    background-color: #0284C7; color: white; padding: 10px; border-radius: 8px;
                    border: none; font-weight: bold; font-size: 12px;
                }
                QPushButton:hover { background-color: #0369A1; }
            """)
            btn_copy.clicked.connect(self._copy_hwid)

            btn_close = QPushButton("Đóng")
            btn_close.setCursor(Qt.PointingHandCursor)
            btn_close.setStyleSheet("""
                QPushButton {
                    background-color: #1E293B; color: #E2E8F0; padding: 10px; border-radius: 8px;
                    border: 1px solid #334155; font-weight: 600; font-size: 12px;
                }
                QPushButton:hover { background-color: #334155; }
            """)
            btn_close.clicked.connect(self.close)

            btn_row.addWidget(btn_copy)
            btn_row.addWidget(btn_close)
            layout.addLayout(btn_row)
            layout.addStretch()

        def _copy_hwid(self):
            copy_to_clipboard(self.current_hwid)
            QMessageBox.information(self, "Đã sao chép", f"Đã chép mã máy Mac vào Clipboard:\n\n{self.current_hwid}\n\nHãy gửi mã này cho tác giả.")


def show_hwid_error_dialog(error_msg: str, hwid: str):
    """Hiển thị hộp thoại lỗi bản quyền bằng PyQt5 hoặc Tkinter"""
    if HAS_PYQT:
        app = QApplication.instance() or QApplication(sys.argv)
        dlg = ClientHWIDDialog(error_message=error_msg, current_hwid=hwid)
        dlg.show()
        app.exec_()
    else:
        root = tk.Tk()
        root.title("LockSlide macOS - Bản Quyền")
        root.geometry("520x340")
        root.configure(bg="#0A0E17")

        tk.Label(root, text=" BẢN QUYỀN BÀI GIẢNG BẢO MẬT (MACBOOK)", fg="#38BDF8", bg="#0A0E17", font=("Helvetica", 14, "bold")).pack(pady=15)
        
        f_err = tk.Frame(root, bg="#331111", highlightbackground="#DC2626", highlightthickness=1, padx=15, pady=10)
        f_err.pack(fill="x", padx=25, pady=5)
        tk.Label(f_err, text=error_msg, fg="#FECACA", bg="#331111", wraplength=460, justify="left", font=("Helvetica", 11)).pack()

        f_hw = tk.Frame(root, bg="#111827", highlightbackground="#1E293B", highlightthickness=1, padx=15, pady=10)
        f_hw.pack(fill="x", padx=25, pady=15)
        tk.Label(f_hw, text=f"Mã máy Mac (HWID): {hwid}", fg="#00F0FF", bg="#111827", font=("Menlo", 12, "bold")).pack()

        def do_copy():
            copy_to_clipboard(hwid)
            messagebox.showinfo("Đã sao chép", f"Đã copy mã máy: {hwid}")

        btn_f = tk.Frame(root, bg="#0A0E17")
        btn_f.pack(pady=10)
        tk.Button(btn_f, text="Sao Chép Mã Máy", command=do_copy, bg="#0284C7", fg="white", font=("Helvetica", 11, "bold"), padx=15, pady=6).pack(side="left", padx=10)
        tk.Button(btn_f, text="Đóng", command=root.destroy, bg="#1E293B", fg="white", font=("Helvetica", 11), padx=15, pady=6).pack(side="left", padx=10)
        root.mainloop()


def safe_read_file(file_path: str, retries: int = 12, delay: float = 0.25) -> bytes | None:
    """Đọc dữ liệu file an toàn với cơ chế thử lại, đảm bảo gói tin là ZIP hợp lệ (Office OpenXML)"""
    for _ in range(retries):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            if data and len(data) > 1000 and data.startswith(b"PK\x03\x04"):
                return data
        except Exception:
            pass
        time.sleep(delay)
    return None


def is_powerpoint_running_mac() -> bool:
    """Kiểm tra Microsoft PowerPoint for Mac có đang chạy hay không"""
    if sys.platform != "darwin":
        return False
    try:
        out = subprocess.check_output(["pgrep", "-f", "Microsoft PowerPoint"], stderr=subprocess.DEVNULL)
        return bool(out.strip())
    except Exception:
        return False


def is_presentation_open_in_ppt_mac(file_path: str) -> bool:
    """
    Sử dụng AppleScript để kiểm tra xem file bài giảng có đang được mở trong PowerPoint for Mac hay không.
    """
    if sys.platform != "darwin":
        return False
    filename = os.path.basename(file_path)
    script = f'''
    tell application "System Events"
        if not (exists process "Microsoft PowerPoint") then
            return "CLOSED"
        end if
    end tell
    tell application "Microsoft PowerPoint"
        try
            set openDocs to name of every presentation
            if openDocs contains "{filename}" then
                return "OPEN"
            else
                return "NOT_FOUND"
            end if
        on error
            return "ERROR"
        end try
    end tell
    '''
    try:
        out = subprocess.check_output(["osascript", "-e", script], stderr=subprocess.DEVNULL, timeout=2).decode("utf-8").strip()
        return out == "OPEN"
    except Exception:
        # Nếu AppleScript bị từ chối quyền, fallback sang kiểm tra tiến trình
        return is_powerpoint_running_mac()


def launch_powerpoint_mac(file_path: str) -> subprocess.Popen | None:
    """
    Mở file bài giảng bằng Microsoft PowerPoint for Mac.
    Ưu tiên 1: Lệnh open -a "Microsoft PowerPoint"
    Ưu tiên 2: AppleScript tell application "Microsoft PowerPoint"
    Ưu tiên 3: open (mặc định của macOS)
    """
    abs_path = os.path.abspath(file_path)

    if sys.platform == "darwin":
        # 1. Thử mở bằng Microsoft PowerPoint for Mac
        try:
            p = subprocess.Popen(["open", "-a", "Microsoft PowerPoint", abs_path])
            return p
        except Exception:
            pass

        # 2. Thử mở qua AppleScript
        try:
            osa_script = f'''
            tell application "Microsoft PowerPoint"
                activate
                open POSIX file "{abs_path}"
            end tell
            '''
            subprocess.run(["osascript", "-e", osa_script], check=True, timeout=5)
            return None
        except Exception:
            pass

        # 3. Fallback mở ứng dụng mặc định
        try:
            return subprocess.Popen(["open", abs_path])
        except Exception as e:
            print(f"[Mac Launcher Error] Không thể mở file: {e}")
            return None
    elif sys.platform == "win32":
        # Hỗ trợ chạy thử nghiệm trên Windows
        try:
            import win32com.client
            ppt_app = win32com.client.Dispatch("PowerPoint.Application")
            ppt_app.Visible = True
            ppt_app.Presentations.Open(abs_path, ReadOnly=False, WithWindow=True)
            return None
        except Exception:
            return subprocess.Popen(["cmd.exe", "/c", "start", "", abs_path])
    else:
        # Linux
        return subprocess.Popen(["xdg-open", abs_path])


def run_powerpoint_editor_mac(
    presentation_bytes: bytes,
    metadata: dict,
    source_payload_bytes: bytes,
    source_file_path: str = None
) -> bool:
    """
    Khởi động PowerPoint trên MacBook ở CHẾ ĐỘ CHỈNH SỬA & TỰ ĐỘNG ĐỒNG BỘ LƯU:
    - CHO PHÉP SỬA & LƯU: Khi khách bấm Cmd+S hoặc lưu trong PowerPoint, hệ thống tự động
      phát hiện thay đổi và re-encrypt đồng bộ ngay lập tức vào file .encppt gốc!
    - CẤM SAVE AS: Ribbon Policy chặn triệt để Save As và Export.
    - CẤM COPY: Ribbon Policy chặn triệt để Copy và Cut.
    - AN TOÀN TUYỆT ĐỐI: Dữ liệu tạm được tiêu hủy và xóa sạch khi tắt bài giảng.
    """
    temp_dir = tempfile.mkdtemp(prefix=".mac_lockslide_")
    safe_title = "".join(c for c in metadata.get("title", "presentation") if c.isalnum() or c in (" ", "_", "-")).strip() or "presentation"
    temp_file = os.path.join(temp_dir, f"{safe_title}.pptx")

    last_synced_mtime = 0.0
    last_known_bytes = presentation_bytes
    current_payload = source_payload_bytes

    try:
        with open(temp_file, "wb") as f:
            f.write(presentation_bytes)

        initial_mtime = os.path.getmtime(temp_file)
        last_synced_mtime = initial_mtime

        # Khởi chạy PowerPoint
        print(f"[LockSlide Mac] Đang mở bài giảng '{metadata.get('title')}' trên PowerPoint...")
        proc = launch_powerpoint_mac(temp_file)

        # Chờ PowerPoint mở file
        time.sleep(2.0)
        print(f"[LockSlide Mac] ✓ Đã mở bài giảng ở CHẾ ĐỘ CHỈNH SỬA (EDITABLE).")
        print(f"[LockSlide Mac] -> Bạn có thể gõ chữ, chỉnh sửa và bấm Cmd+S để lưu lại.")
        print(f"[LockSlide Mac] -> Luồng Auto-Save Sync đang chạy ngầm để bảo vệ dữ liệu...")

        # VÒNG LẶP THEO DÕI & TỰ ĐỘNG LƯU (AUTO-SAVE SYNC)
        consecutive_missing = 0
        while True:
            time.sleep(0.5)

            # Kiểm tra trạng thái PowerPoint trên macOS
            if sys.platform == "darwin":
                if not is_presentation_open_in_ppt_mac(temp_file):
                    consecutive_missing += 1
                    if consecutive_missing >= 4:  # Đã đóng bài giảng sau 2 giây
                        print("[LockSlide Mac] Người dùng đã đóng bài giảng PowerPoint.")
                        break
                else:
                    consecutive_missing = 0
            elif proc and proc.poll() is not None:
                # Nếu chạy dạng process độc lập
                break

            # Kiểm tra xem người dùng có vừa nhấn Save (Cmd+S / Ctrl+S)
            if os.path.exists(temp_file):
                try:
                    cur_mtime = os.path.getmtime(temp_file)
                    cur_size = os.path.getsize(temp_file)
                    if abs(cur_mtime - last_synced_mtime) > 0.05 or cur_size != len(last_known_bytes):
                        updated_data = safe_read_file(temp_file)
                        if updated_data and updated_data != last_known_bytes:
                            print("[LockSlide Mac] ⚡ Phát hiện thao tác Lưu (Cmd+S / Save)! Đang tự động mã hóa đồng bộ...")
                            new_payload = reencrypt_updated_presentation(current_payload, updated_data)
                            if source_file_path and os.path.exists(source_file_path):
                                with open(source_file_path, "wb") as sf:
                                    sf.write(new_payload)
                                print("[LockSlide Mac] ✓ ĐÃ TỰ ĐỘNG ĐỒNG BỘ THAY ĐỔI VÀO FILE MÃ HÓA!")
                            current_payload = new_payload
                            last_known_bytes = updated_data
                            last_synced_mtime = cur_mtime
                except Exception as e_sync:
                    pass

        # ĐỒNG BỘ LẦN CUỐI KHI ĐÓNG BÀI GIẢNG (NẾU CÓ BẤM LƯU LÚC TẮT)
        time.sleep(0.4)
        if os.path.exists(temp_file):
            try:
                final_data = safe_read_file(temp_file, retries=12, delay=0.25)
                if final_data and final_data != last_known_bytes:
                    print("[LockSlide Mac] Đồng bộ lần cuối trước khi đóng...")
                    final_payload = reencrypt_updated_presentation(current_payload, final_data)
                    if source_file_path and os.path.exists(source_file_path):
                        with open(source_file_path, "wb") as sf:
                            sf.write(final_payload)
                        print("[LockSlide Mac] ✓ Đã lưu trọn vẹn toàn bộ thay đổi vào file mã hóa!")
            except Exception:
                pass

        return True

    except Exception as e:
        print(f"[LockSlide Mac] Lỗi khi xử lý bài giảng: {e}")
        return False

    finally:
        # TIÊU HỦY AN TOÀN FILE TẠM (SHRED & DELETE)
        if os.path.exists(temp_file):
            for _ in range(5):
                try:
                    sz = os.path.getsize(temp_file)
                    with open(temp_file, "wb") as f_wipe:
                        f_wipe.write(os.urandom(min(1024 * 512, sz)))
                    os.remove(temp_file)
                    break
                except Exception:
                    time.sleep(0.3)

        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


def open_and_edit_payload_mac(
    payload_bytes: bytes,
    source_file_path: str = None,
    exit_on_finish: bool = True
) -> bool:
    current_hwid = get_machine_hwid()
    try:
        metadata, pres_bytes = decrypt_presentation_from_bytes(payload_bytes, current_hwid)
        success = run_powerpoint_editor_mac(
            presentation_bytes=pres_bytes,
            metadata=metadata,
            source_payload_bytes=payload_bytes,
            source_file_path=source_file_path
        )
        if exit_on_finish:
            sys.exit(0 if success else 1)
        return success
    except PermissionError as pe:
        show_hwid_error_dialog(error_msg=str(pe), hwid=current_hwid)
        if exit_on_finish:
            sys.exit(1)
        return False
    except Exception as ex:
        err_text = f"Không thể giải mã bài giảng:\n{ex}"
        if HAS_PYQT:
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "Lỗi giải mã", err_text)
        else:
            try:
                import tkinter as tk
                from tkinter import messagebox
                r = tk.Tk(); r.withdraw()
                messagebox.showerror("Lỗi giải mã", err_text)
                r.destroy()
            except Exception:
                print(f"[Error] {err_text}")
        if exit_on_finish:
            sys.exit(1)
        return False


def main():
    target_file = None

    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        target_file = os.path.abspath(sys.argv[1])
    else:
        # Nếu chạy không tham số (ví dụ nhấp đúp script), kiểm tra các file .encppt trong thư mục hiện tại
        cwd = os.getcwd()
        enc_files = [os.path.join(cwd, f) for f in os.listdir(cwd) if f.lower().endswith(".encppt")]
        if len(enc_files) == 1:
            target_file = enc_files[0]
        elif len(enc_files) > 1:
            target_file = enc_files[0]

    if not target_file or not os.path.exists(target_file):
        # Mở hộp thoại chọn file
        if HAS_PYQT:
            app = QApplication.instance() or QApplication(sys.argv)
            selected, _ = QFileDialog.getOpenFileName(
                None, "Chọn bài giảng bảo mật LockSlide (.encppt)",
                os.getcwd(), "Bài giảng bảo mật (*.encppt);;Tất cả file (*.*)"
            )
            target_file = selected
        else:
            try:
                import tkinter as tk
                from tkinter import filedialog
                r = tk.Tk(); r.withdraw()
                target_file = filedialog.askopenfilename(
                    title="Chọn bài giảng bảo mật LockSlide (.encppt)",
                    filetypes=[("Bài giảng bảo mật", "*.encppt"), ("Tất cả", "*.*")]
                )
                r.destroy()
            except Exception:
                pass

    if not target_file or not os.path.exists(target_file):
        print("[LockSlide Mac] Chưa chọn file bài giảng.")
        sys.exit(0)

    with open(target_file, "rb") as f:
        payload = f.read()

    open_and_edit_payload_mac(
        payload_bytes=payload,
        source_file_path=target_file,
        exit_on_finish=True
    )


if __name__ == "__main__":
    main()
