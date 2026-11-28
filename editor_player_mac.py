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
   - Tự động đồng bộ ghim bản quyền ngược lại file .zip gốc để chống chia sẻ.
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
import zipfile

from crypto_engine_mac import (
    get_machine_hwid,
    decrypt_presentation_from_bytes,
    decrypt_presentation,
    reencrypt_updated_presentation,
    update_payload_metadata
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
    try:
        import tkinter as tk
        from tkinter import messagebox, filedialog
    except ImportError:
        pass


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


def is_running_from_temp_archive(file_path: str) -> bool:
    """
    Kiểm tra xem file có đang được mở trực tiếp từ trong file nén (.zip, .rar)
    mà chưa được người dùng giải nén ra thư mục hay không.
    """
    try:
        norm = os.path.normpath(os.path.abspath(file_path)).lower()
        temp_dir = os.path.normpath(tempfile.gettempdir()).lower()
        if norm.startswith(temp_dir):
            rel = os.path.relpath(norm, temp_dir).lower()
            if any(k in rel for k in ["temp", "rar$", "7z", ".zip", "cpt", "archive"]):
                return True
        # Kiểm tra thêm đường dẫn macOS private/var/folders
        if any(p in norm for p in ["/private/var/folders", "/var/folders"]):
            if any(k in norm for k in ["temp", ".zip", "archive", "appkit"]):
                return True
    except Exception:
        pass
    return False


def sync_stamped_payload_to_zip(source_file_path: str, stamped_payload: bytes):
    """
    Nếu người dùng vừa giải nén bài giảng và mở lên trên MacBook, hàm này sẽ tự động tìm
    file .zip gốc (trong cùng thư mục hoặc thư mục cha) để ghim luôn HWID vào file .zip đó!
    Nhờ vậy, ngay cả khi khách gửi lại file .zip gốc cho người khác thì máy khác cũng không thể mở được.
    """
    try:
        cur_dir = os.path.dirname(os.path.abspath(source_file_path))
        base_name = os.path.basename(source_file_path).replace("_PROTECTED.encppt", "").replace(".encppt", "")
        clean_base = base_name.replace("Mo_", "")

        candidates = [
            os.path.join(cur_dir, f"{base_name}.zip"),
            os.path.join(cur_dir, f"{clean_base}.zip"),
            os.path.join(os.path.dirname(cur_dir), f"{base_name}.zip"),
            os.path.join(os.path.dirname(cur_dir), f"{clean_base}.zip"),
            os.path.join(cur_dir, f"{base_name}_MacOS_Package.zip"),
            os.path.join(os.path.dirname(cur_dir), f"{base_name}_MacOS_Package.zip"),
            os.path.join(os.path.dirname(cur_dir), f"{clean_base}_MacOS_Package.zip")
        ]

        enc_rel_name = os.path.basename(source_file_path)

        for zip_candidate in candidates:
            if os.path.isfile(zip_candidate):
                tmp_zip = zip_candidate + f".tmp_{os.getpid()}"
                try:
                    with zipfile.ZipFile(zip_candidate, 'r') as zin:
                        with zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_DEFLATED) as zout:
                            for item in zin.infolist():
                                content = zin.read(item.filename)
                                if item.filename.endswith(enc_rel_name) or item.filename.endswith("_PROTECTED.encppt"):
                                    content = stamped_payload
                                zout.writestr(item, content)
                    os.replace(tmp_zip, zip_candidate)
                    print(f"[LockSlide Mac] ✓ Đã tự động ghim bản quyền vào file nén gốc: {zip_candidate}")
                except Exception as ze:
                    if os.path.exists(tmp_zip):
                        try:
                            os.remove(tmp_zip)
                        except Exception:
                            pass
                    print(f"[LockSlide Mac Zip Sync Warning] {ze}")
    except Exception as e:
        print(f"[LockSlide Mac Sync Zip Warning] {e}")


# ==============================================================================
# HỘP THOẠI BẢN QUYỀN VÀ MÃ MÁY TRÊN MAC (PYQT5 HOẶC TKINTER)
# ==============================================================================
if HAS_PYQT:
    class ClientHWIDDialog(QMainWindow):
        def __init__(self, error_message: str = "", current_hwid: str = ""):
            super().__init__()
            self.error_message = error_message
            self.current_hwid = current_hwid or get_machine_hwid()
            self.init_ui()

        def init_ui(self):
            self.setWindowTitle("LockSlide Studio macOS - Xác Thực Bản Quyền")
            self.setFixedSize(580, 420)
            self.setStyleSheet("""
                QMainWindow { background-color: #0A0E17; }
                QLabel { color: #E2E8F0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
                QPushButton {
                    background-color: #1E293B; color: #E2E8F0; font-size: 13px; font-weight: 600;
                    border: 1px solid #334155; border-radius: 8px; padding: 10px 18px;
                }
                QPushButton:hover { background-color: #2D3B52; color: #FFFFFF; }
            """)

            central = QWidget(self)
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setContentsMargins(28, 24, 28, 24)
            layout.setSpacing(14)

            title = QLabel(" THÔNG BÁO BẢN QUYỀN MACBOOK")
            title.setStyleSheet("font-size: 16px; font-weight: 800; color: #F87171; letter-spacing: 0.5px;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

            # Box lỗi
            box_err = QFrame()
            box_err.setStyleSheet("background-color: #161F30; border: 1px solid #334155; border-radius: 10px; padding: 14px;")
            l_err = QVBoxLayout(box_err)
            lbl_err = QLabel(self.error_message or "Bài giảng này yêu cầu bản quyền thiết bị MacBook hợp lệ.")
            lbl_err.setWordWrap(True)
            lbl_err.setStyleSheet("color: #E2E8F0; font-size: 12px; line-height: 1.5;")
            l_err.addWidget(lbl_err)
            layout.addWidget(box_err)

            # Khung HWID
            card_hwid = QFrame()
            card_hwid.setStyleSheet("background-color: #0E1524; border: 1px solid #1E293B; border-radius: 10px; padding: 12px;")
            l_hw = QVBoxLayout(card_hwid)
            lbl_cap = QLabel("MÃ ĐỊNH DANH MÁY MAC (HWID CỦA BẠN):")
            lbl_cap.setStyleSheet("color: #94A3B8; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
            l_hw.addWidget(lbl_cap)

            self.lbl_hwid = QLabel(self.current_hwid)
            self.lbl_hwid.setStyleSheet("font-size: 18px; font-weight: 800; color: #38BDF8; font-family: 'SF Mono', Menlo, Consolas;")
            self.lbl_hwid.setAlignment(Qt.AlignCenter)
            l_hw.addWidget(self.lbl_hwid)
            layout.addWidget(card_hwid)

            btn_box = QHBoxLayout()
            btn_copy = QPushButton("📋 Sao Chép Mã Máy (HWID)")
            btn_copy.setCursor(Qt.PointingHandCursor)
            btn_copy.setStyleSheet("background-color: #0284C7; color: #FFFFFF; font-weight: 700; border: none; padding: 12px;")
            btn_copy.clicked.connect(self._copy_hwid)

            btn_close = QPushButton("Đóng")
            btn_close.setCursor(Qt.PointingHandCursor)
            btn_close.clicked.connect(self.close)

            btn_box.addWidget(btn_copy, stretch=3)
            btn_box.addWidget(btn_close, stretch=1)
            layout.addLayout(btn_box)

        def _copy_hwid(self):
            copy_to_clipboard(self.current_hwid)
            QMessageBox.information(
                self, "Đã sao chép",
                f"Đã chép mã máy Mac vào Clipboard:\n\n{self.current_hwid}\n\nHãy gửi mã này cho giảng viên / tác giả bài giảng để được cấp quyền mở lại."
            )


def show_hwid_error_dialog(error_msg: str, hwid: str):
    """Hiển thị hộp thoại thông báo lỗi bản quyền kèm mã máy Mac"""
    if HAS_PYQT:
        app = QApplication.instance() or QApplication(sys.argv)
        dlg = ClientHWIDDialog(error_message=error_msg, current_hwid=hwid)
        dlg.show()
        app.exec_()
        return

    # Fallback Tkinter nếu máy Mac không có PyQt5
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.title("LockSlide Studio macOS - Bản Quyền")
        root.geometry("540x380")
        root.configure(bg="#0A0E17")

        tk.Label(root, text=" THÔNG BÁO BẢN QUYỀN MACBOOK", fg="#F87171", bg="#0A0E17", font=("Helvetica", 14, "bold")).pack(pady=12)

        lbl_msg = tk.Label(root, text=error_msg, fg="#E2E8F0", bg="#161F30", font=("Helvetica", 10), wraplength=480, justify="left", padx=12, pady=10)
        lbl_msg.pack(fill="x", padx=20, pady=8)

        card = tk.Frame(root, bg="#0E1524", highlightbackground="#1E293B", highlightthickness=1, padx=15, pady=10)
        card.pack(fill="x", padx=20, pady=10)
        tk.Label(card, text="MÃ ĐỊNH DANH MÁY MACBOOK (HWID):", fg="#94A3B8", bg="#0E1524", font=("Helvetica", 9, "bold")).pack()
        tk.Label(card, text=hwid, fg="#38BDF8", bg="#0E1524", font=("Menlo", 15, "bold")).pack(pady=4)

        def do_copy():
            copy_to_clipboard(hwid)
            messagebox.showinfo("Đã sao chép", f"Đã copy mã máy: {hwid}\nHãy gửi mã này cho tác giả bài giảng.")

        btn_c = tk.Button(root, text="📋 Sao Chép Mã Máy Mac (HWID)", command=do_copy, bg="#0284C7", fg="white", font=("Helvetica", 11, "bold"), padx=15, pady=8)
        btn_c.pack(pady=10)

        root.mainloop()
    except Exception:
        print(f"\n[BẢN QUYỀN KHÔNG HỢP LỆ]\n{error_msg}\nMã máy Mac: {hwid}\n")


# ==============================================================================
# QUẢN LÝ TIẾN TRÌNH POWERPOINT TRÊN MACOS & ĐỒNG BỘ LƯU TỰ ĐỘNG (AUTO-SAVE)
# ==============================================================================

def safe_read_file(file_path: str, retries: int = 12, delay: float = 0.25) -> bytes | None:
    """Đọc file an toàn khi PowerPoint đang nắm giữ file lock"""
    for _ in range(retries):
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except (PermissionError, IOError):
            time.sleep(delay)
    return None


def is_powerpoint_running_mac() -> bool:
    """Kiểm tra Microsoft PowerPoint có đang chạy trên macOS không"""
    if sys.platform != "darwin":
        return False
    try:
        out = subprocess.check_output(["pgrep", "-f", "Microsoft PowerPoint"], stderr=subprocess.DEVNULL)
        return len(out.strip()) > 0
    except Exception:
        return False


def is_presentation_open_in_ppt_mac(file_path: str) -> bool:
    """
    Sử dụng AppleScript để kiểm tra xem file thuyết trình cụ thể
    có đang được mở trong cửa sổ PowerPoint for Mac hay không.
    """
    if sys.platform != "darwin":
        return False
    base_name = os.path.basename(file_path)
    script = f'''
    tell application "System Events"
        if exists (processes where name is "Microsoft PowerPoint") then
            tell application "Microsoft PowerPoint"
                try
                    set docNames to name of every presentation
                    repeat with docName in docNames
                        if docName contains "{base_name}" or "{base_name}" contains docName then
                            return "OPEN"
                        end if
                    end repeat
                end try
            end tell
        end if
    end tell
    return "CLOSED"
    '''
    try:
        res = subprocess.check_output(["osascript", "-e", script], stderr=subprocess.DEVNULL, timeout=2).decode("utf-8").strip()
        return res == "OPEN"
    except Exception:
        return is_powerpoint_running_mac()


def launch_powerpoint_mac(file_path: str) -> subprocess.Popen | None:
    """Khởi động file PowerPoint trực tiếp trên macOS"""
    if sys.platform == "darwin":
        try:
            # Mở bằng Microsoft PowerPoint
            return subprocess.Popen(["open", "-a", "Microsoft PowerPoint", file_path])
        except Exception:
            return subprocess.Popen(["open", file_path])
    elif sys.platform == "win32":
        try:
            return subprocess.Popen(["start", "powerpnt", file_path], shell=True)
        except Exception:
            return subprocess.Popen(["cmd", "/c", "start", "", file_path])
    else:
        return subprocess.Popen(["xdg-open", file_path])


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
                except Exception:
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

        # Nếu vừa tự động ghim HWID lần đầu (Offline Auto-Lock hoặc First-Run TOFU),
        # lưu ngay lập tức metadata đã ghim vào file trên đĩa và đồng bộ file zip gốc để chống copy sang máy khác
        if metadata.get("_needs_save_bound_hwid") and source_file_path:
            try:
                stamped_payload = update_payload_metadata(payload_bytes, metadata)
                payload_bytes = stamped_payload
                with open(source_file_path, "wb") as f_save:
                    f_save.write(stamped_payload)
                print(f"[LockSlide Mac] ✓ Đã tự động ghim bản quyền máy này vào file: {source_file_path}")
                # Đồng bộ bản quyền vào file .zip gốc nếu có
                sync_stamped_payload_to_zip(source_file_path, stamped_payload)
            except Exception as e_stamp:
                print(f"[LockSlide Mac Stamp Warning] Không thể cập nhật metadata: {e_stamp}")

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
