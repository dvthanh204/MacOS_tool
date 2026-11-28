"""
LockSlide Studio macOS v3.0 - Hệ Thống Mã Hóa & Đóng Gói Bài Giảng PowerPoint Độc Lập Cho MacBook (.ZIP)
Đặc điểm:
- 100% Ngoại tuyến (Offline), không cần máy chủ, không cần mạng LAN hay Internet.
- Hỗ trợ Google Sheets (Apps Script) làm máy chủ bản quyền đám mây miễn phí 100%.
- Mỗi bài giảng được xuất thành 1 file nén (.zip) riêng biệt để gửi cho khách hàng MacBook.
- Tự động ghim cứng vào ID máy Mac khách ngay lần mở đầu tiên (Auto-Lock TOFU).
- Chuyển sang máy tính khác KHÔNG THỂ MỞ ĐƯỢC!
- Khách hàng vẫn có thể chỉnh sửa và Lưu bài (Cmd+S) bình thường trong PowerPoint for Mac.
- Cấm tuyệt đối chức năng Save As và Copy để bảo vệ 100% bản quyền tác giả.
"""

import sys
import os
import json
import webbrowser
import random
import datetime
import math
import shutil
import zipfile
import tempfile
import subprocess

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFileDialog, QDialog, QFrame,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QProgressBar, QCheckBox, QMessageBox
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty

import crypto_engine_mac
import mac_packager

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()
RESULT_DIR = os.path.join(APP_DIR, "result_mac")
os.makedirs(RESULT_DIR, exist_ok=True)

def generate_license_code() -> str:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return f"MAC-{''.join(random.choices(chars, k=6))}"


# ==============================================================================
# WIDGET ANIMATION: KHUNG KÉO THẢ FILE CÔNG NGHỆ
# ==============================================================================
class TechDropZone(QFrame):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._glow_progress = 0.0
        self.anim = QPropertyAnimation(self, b"glowProgress")
        self.anim.setDuration(350)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.init_ui()

    @pyqtProperty(float)
    def glowProgress(self):
        return self._glow_progress

    @glowProgress.setter
    def glowProgress(self, val):
        self._glow_progress = val
        self.update_style()

    def update_style(self):
        alpha = int(40 + 80 * self._glow_progress)
        border_col = f"rgba(56, 189, 248, {0.3 + 0.7 * self._glow_progress})"
        bg_col = f"rgba(14, 21, 36, {0.6 + 0.4 * self._glow_progress})"
        self.setStyleSheet(f"""
            TechDropZone {{
                border: 2px dashed {border_col};
                border-radius: 12px;
                background-color: {bg_col};
            }}
        """)

    def init_ui(self):
        self.setFixedHeight(120)
        self.update_style()
        l = QVBoxLayout(self)
        l.setAlignment(Qt.AlignCenter)
        l.setSpacing(6)

        icon_lbl = QLabel("📂")
        icon_lbl.setStyleSheet("font-size: 26px; background: transparent; border: none;")
        icon_lbl.setAlignment(Qt.AlignCenter)

        title_lbl = QLabel("KÉO THẢ CÁC FILE POWERPOINT (.PPTX, .PPTM) VÀO ĐÂY")
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 800; color: #38BDF8; letter-spacing: 0.8px; background: transparent; border: none;")
        title_lbl.setAlignment(Qt.AlignCenter)

        sub_lbl = QLabel("Hỗ trợ chọn cùng lúc nhiều file — Tự động đóng gói độc lập (.ZIP) cho MacBook")
        sub_lbl.setStyleSheet("font-size: 11px; color: #64748B; background: transparent; border: none;")
        sub_lbl.setAlignment(Qt.AlignCenter)

        l.addWidget(icon_lbl)
        l.addWidget(title_lbl)
        l.addWidget(sub_lbl)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.anim.stop()
            self.anim.setEndValue(1.0)
            self.anim.start()

    def dragLeaveEvent(self, event):
        self.anim.stop()
        self.anim.setEndValue(0.0)
        self.anim.start()

    def dropEvent(self, event):
        self.anim.stop()
        self.anim.setEndValue(0.0)
        self.anim.start()
        file_paths = []
        for url in event.mimeData().urls():
            fp = url.toLocalFile()
            if os.path.isfile(fp) and fp.lower().endswith((".pptx", ".pptm", ".ppt")):
                file_paths.append(fp)
        if file_paths:
            self.files_dropped.emit(file_paths)


# ==============================================================================
# WIDGET ANIMATION: THANH TIẾN TRÌNH MƯỢT MÀ
# ==============================================================================
class SmoothProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animated_val = 0.0
        self.anim = QPropertyAnimation(self, b"animatedValue")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)

    @pyqtProperty(float)
    def animatedValue(self):
        return self._animated_val

    @animatedValue.setter
    def animatedValue(self, val):
        self._animated_val = val
        super().setValue(int(val))

    def setValueSmooth(self, target_val):
        self.anim.stop()
        self.anim.setStartValue(self._animated_val)
        self.anim.setEndValue(float(target_val))
        self.anim.start()


# ==============================================================================
# HỘP THOẠI THÔNG BÁO HOÀN TẤT CÔNG NGHỆ
# ==============================================================================
class TechNotificationDialog(QDialog):
    def __init__(self, title_text: str, content_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thông Báo Hệ Thống")
        self.setFixedSize(540, 360)
        self.setStyleSheet("""
            QDialog { background-color: #0E1524; color: #E2E8F0; }
            QLabel { color: #E2E8F0; font-size: 12px; }
            QPushButton {
                background-color: #1E293B; color: #E2E8F0; font-size: 12px; font-weight: 600;
                border: 1px solid #334155; border-radius: 8px; padding: 8px 16px;
            }
            QPushButton:hover { background-color: #2D3B52; color: #FFFFFF; }
        """)
        l = QVBoxLayout(self)
        l.setContentsMargins(24, 20, 24, 20)
        l.setSpacing(14)

        t_lbl = QLabel(title_text)
        t_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #38BDF8; letter-spacing: 0.5px;")
        t_lbl.setAlignment(Qt.AlignCenter)
        l.addWidget(t_lbl)

        card = QFrame()
        card.setStyleSheet("background-color: #111827; border: 1px solid #1E293B; border-radius: 10px; padding: 12px;")
        cl = QVBoxLayout(card)
        c_lbl = QLabel(content_text)
        c_lbl.setWordWrap(True)
        c_lbl.setStyleSheet("font-size: 12px; line-height: 1.5; color: #CBD5E1;")
        cl.addWidget(c_lbl)
        l.addWidget(card)

        btn_row = QHBoxLayout()
        btn_close = QPushButton("Xác Nhận & Đóng")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("background-color: #0284C7; color: white; font-weight: 700; border: none; padding: 10px 20px;")
        btn_close.clicked.connect(self.accept)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        btn_row.addStretch()
        l.addLayout(btn_row)


# ==============================================================================
# HỘP THOẠI HƯỚNG DẪN CÀI ĐẶT GOOGLE SHEETS
# ==============================================================================
class GoogleSheetsGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hướng Dẫn Tạo Máy Chủ Google Sheets Cho MacBook")
        self.setFixedSize(620, 500)
        self.setStyleSheet("""
            QDialog { background-color: #0E1524; color: #E2E8F0; }
            QLabel { color: #E2E8F0; font-size: 12px; }
            QPushButton {
                background-color: #1E293B; color: #E2E8F0; font-size: 12px; font-weight: 600;
                border: 1px solid #334155; border-radius: 8px; padding: 8px 16px;
            }
            QPushButton:hover { background-color: #2D3B52; color: #FFFFFF; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl_title = QLabel("HƯỚNG DẪN DÙNG GOOGLE SHEETS LÀM MÁY CHỦ BẢN QUYỀN")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #38BDF8; letter-spacing: 0.5px;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        guide_text = (
            "<p style='color: #34D399; font-weight: bold;'>🌟 Lợi ích khi dùng Google Sheets (Khuyên dùng):</p>"
            "• Hoàn toàn <b>MIỄN PHÍ 100%</b>, không cần mua máy chủ hay VPS.<br>"
            "• Đảm bảo mỗi bài giảng <b>chỉ mở được đúng 1 lần duy nhất</b> trên 1 máy MacBook.<br>"
            "• Khách hàng có chia sẻ file zip chưa giải nén cho người khác thì người khác <b>bị chặn 100%</b>!<br>"
            "• Khách mở lần đầu chỉ cần 1-2 giây có mạng để xác thực, sau đó ngắt mạng dùng Offline vĩnh viễn.<br><br>"
            "<p style='color: #FACC15; font-weight: bold;'>📋 Các bước thiết lập nhanh (Chỉ mất 1 phút):</p>"
            "<b>Bước 1:</b> Nhấn nút <b>'🌐 Mở Google Sheets (sheets.new)'</b> bên dưới để tạo 1 bảng tính mới.<br>"
            "<b>Bước 2:</b> Trên thanh menu, chọn <b>Tiện ích mở rộng (Extensions)</b> -> <b>Apps Script</b>.<br>"
            "<b>Bước 3:</b> Nhấn nút <b>'📋 Sao Chép Mã Apps Script'</b> bên dưới, xóa code cũ và dán vào Apps Script.<br>"
            "<b>Bước 4:</b> Nhấn nút <b>Triển khai (Deploy)</b> ở góc trên bên phải -> <b>Tùy chọn triển khai mới (New deployment)</b>:<br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;• Loại: Chọn <b>Ứng dụng web (Web app)</b>.<br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;• Thực thi dưới dạng: <b>Tôi (Me)</b>.<br>"
            "&nbsp;&nbsp;&nbsp;&nbsp;• Ai có quyền truy cập: <b>Bất kỳ ai (Anyone)</b>.<br>"
            "<b>Bước 5:</b> Copy link Web App (dạng <code>https://script.google.com/macros/s/.../exec</code>) dán vào ô <b>MÁY CHỦ BẢN QUYỀN (URL)</b>."
        )
        lbl_guide = QLabel(guide_text)
        lbl_guide.setTextFormat(Qt.RichText)
        lbl_guide.setWordWrap(True)
        lbl_guide.setStyleSheet("line-height: 1.4;")
        layout.addWidget(lbl_guide)

        btn_row = QHBoxLayout()
        btn_open_sheets = QPushButton("🌐 Mở Google Sheets (sheets.new)")
        btn_open_sheets.setCursor(Qt.PointingHandCursor)
        btn_open_sheets.setStyleSheet("background-color: #0369A1; color: white; font-weight: bold; padding: 10px 16px;")
        btn_open_sheets.clicked.connect(lambda: webbrowser.open("https://sheets.new"))

        btn_copy_code = QPushButton("📋 Sao Chép Toàn Bộ Mã Apps Script")
        btn_copy_code.setCursor(Qt.PointingHandCursor)
        btn_copy_code.setStyleSheet("background-color: #059669; color: white; font-weight: bold; padding: 10px 16px;")
        btn_copy_code.clicked.connect(self.copy_script_code)

        btn_row.addWidget(btn_open_sheets)
        btn_row.addWidget(btn_copy_code)
        layout.addLayout(btn_row)

        btn_close = QPushButton("Đóng Hướng Dẫn")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def copy_script_code(self):
        js_file = os.path.join(get_app_dir(), "google_apps_script_server.js")
        code = ""
        if os.path.exists(js_file):
            try:
                with open(js_file, "r", encoding="utf-8") as f:
                    code = f.read()
            except Exception:
                pass
        if not code:
            code = "// Vui lòng mở file google_apps_script_server.js trong thư mục để sao chép."
        clipboard = QApplication.clipboard()
        clipboard.setText(code)
        QMessageBox.information(
            self, "Đã sao chép",
            "Đã sao chép toàn bộ mã JavaScript vào bộ nhớ tạm!\nBây giờ bạn chỉ cần dán (Cmd+V / Ctrl+V) vào Google Apps Script."
        )


# ==============================================================================
# WORKER LUỒNG MÃ HÓA & ĐÓNG GÓI ZIP CHO MACBOOK
# ==============================================================================
class BatchEncodeWorkerMac(QThread):
    row_status_signal = pyqtSignal(int, str, str)  # row, text, color_hex
    overall_progress_signal = pyqtSignal(int, int, str)  # current, total, text
    finished_signal = pyqtSignal(int, int)  # success, failed

    def __init__(self, file_items, result_dir, allow_edit=True, block_save_as=True, block_copy=True, bound_hwid="", server_url=""):
        super().__init__()
        self.file_items = file_items
        self.result_dir = result_dir
        self.allow_edit = allow_edit
        self.block_save_as = block_save_as
        self.block_copy = block_copy
        self.bound_hwid = bound_hwid
        self.server_url = server_url

    def run(self):
        total = len(self.file_items)
        success = 0
        failed = 0

        for idx, item in enumerate(self.file_items):
            file_path = item["path"]
            title = item["title"]
            lic_id = item["license_id"]
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            clean_name = "".join(c for c in base_name if c not in '<>:"/\\|?*').strip()
            if not clean_name:
                clean_name = f"BaiGiang_Mac_{idx+1}"

            self.row_status_signal.emit(idx, "Đang xử lý...", "#FACC15")
            self.overall_progress_signal.emit(idx + 1, total, f"Đang mã hóa ({idx + 1}/{total}): {os.path.basename(file_path)}")

            # Tạo thư mục tạm để chuẩn bị các file trước khi nén zip
            temp_staging_dir = tempfile.mkdtemp(prefix="lockslide_mac_pkg_")
            pkg_folder = os.path.join(temp_staging_dir, clean_name)
            os.makedirs(pkg_folder, exist_ok=True)

            try:
                # 1. Đọc byte PowerPoint bản gốc
                with open(file_path, "rb") as f_in:
                    pres_bytes = f_in.read()

                # 2. Xây dựng payload bảo mật Auto-Lock cho MacBook
                self.row_status_signal.emit(idx, "Đang mã hóa AES-256...", "#38BDF8")
                payload = crypto_engine_mac.build_autolock_payload(
                    presentation_bytes=pres_bytes,
                    license_id=lic_id,
                    server_url=self.server_url,
                    title=title,
                    allow_edit=self.allow_edit,
                    block_save_as=self.block_save_as,
                    block_copy=self.block_copy,
                    expiry_date="",
                    watermark_text="",
                    bound_hwid=self.bound_hwid,
                    offline_fallback=True,
                    target_os="MACOS"
                )

                # 3. Đóng gói trọn bộ macOS (file mã hóa, Mo_...command, script runtime, readme)
                self.row_status_signal.emit(idx, "Đang đóng gói macOS...", "#818CF8")
                mac_packager.package_for_mac(
                    output_dir=pkg_folder,
                    base_name=clean_name,
                    payload_bytes=payload,
                    app_root_dir=APP_DIR,
                    create_zip=False
                )

                # 4. Nén toàn bộ vào file .zip duy nhất với Unix attributes (0755 cho .command)
                final_zip = os.path.join(self.result_dir, f"{clean_name}.zip")
                if os.path.exists(final_zip) and idx > 0 and any(it["path"] != file_path for it in self.file_items[:idx]):
                    final_zip = os.path.join(self.result_dir, f"{clean_name}_{idx+1}.zip")

                self.row_status_signal.emit(idx, "Đang nén tập tin .zip...", "#06B6D4")
                with zipfile.ZipFile(final_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                    folder_prefix = f"{clean_name}/"
                    z_dir = zipfile.ZipInfo(folder_prefix)
                    z_dir.create_system = 3  # Unix
                    z_dir.external_attr = (0o40755) << 16
                    zf.writestr(z_dir, "")

                    for root_d, _, files in os.walk(pkg_folder):
                        for f_name in files:
                            abs_f = os.path.join(root_d, f_name)
                            rel_arc = folder_prefix + os.path.relpath(abs_f, pkg_folder).replace("\\", "/")
                            z_info = zipfile.ZipInfo.from_file(abs_f, rel_arc)
                            z_info.create_system = 3
                            if f_name.endswith((".command", ".sh")):
                                z_info.external_attr = (0o100755) << 16  # chmod +x
                            else:
                                z_info.external_attr = (0o100644) << 16
                            with open(abs_f, "rb") as fp:
                                zf.writestr(z_info, fp.read())

                # Xóa thư mục tạm
                shutil.rmtree(temp_staging_dir, ignore_errors=True)

                self.row_status_signal.emit(idx, "Hoàn tất (.ZIP)", "#34D399")
                success += 1
            except Exception as e:
                shutil.rmtree(temp_staging_dir, ignore_errors=True)
                err_msg = str(e).split("\n")[0]
                self.row_status_signal.emit(idx, f"Lỗi: {err_msg[:24]}", "#F87171")
                failed += 1

        self.finished_signal.emit(success, failed)


# ==============================================================================
# CỬA SỔ CHÍNH: GIAO DIỆN TINH GỌN, CHUYÊN NGHIỆP CHO MACBOOK
# ==============================================================================
class LockSlideStudioMacApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_dir = get_app_dir()
        self.base_dir = self.app_dir

        self.setAcceptDrops(True)
        self.queued_files = []

        self.init_ui()
        self.load_config()

    def init_ui(self):
        self.setWindowTitle("LockSlide Studio macOS - Hệ Thống Mã Hóa & Đóng Gói Bài Giảng PowerPoint (.ZIP)")
        self.resize(800, 600)
        self.setMinimumSize(740, 520)

        # Tech Dark Neon Stylesheet
        self.setStyleSheet("""
            QMainWindow { background-color: #080C14; }
            QWidget { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Tahoma, sans-serif; color: #E2E8F0; }
            QLabel { color: #E2E8F0; font-size: 12px; }
            QLineEdit {
                background-color: #0E1524; color: #38BDF8; border: 1px solid #1E293B;
                border-radius: 8px; padding: 8px 12px; font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #0284C7; }
            QTableWidget {
                background-color: #0E1524; border: 1px solid #1E293B; border-radius: 10px;
                gridline-color: #1A2234; selection-background-color: #1E293B;
                selection-color: #38BDF8; font-size: 11px;
            }
            QHeaderView::section {
                background-color: #111827; color: #64748B; font-weight: 700;
                font-size: 10px; border: none; padding: 6px; letter-spacing: 0.5px;
            }
            QPushButton {
                background-color: #1E293B; color: #E2E8F0; font-size: 12px; font-weight: 600;
                border: 1px solid #334155; border-radius: 8px; padding: 8px 16px;
            }
            QPushButton:hover { background-color: #2D3B52; color: #FFFFFF; }
            QCheckBox { font-size: 12px; color: #CBD5E1; spacing: 6px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #334155; background-color: #0E1524; }
            QCheckBox::indicator:checked { background-color: #0284C7; border-color: #38BDF8; }
        """)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # ----------------------------------------------------------------------
        # 1. TIÊU ĐỀ CHÍNH
        # ----------------------------------------------------------------------
        header_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        lbl_app = QLabel(" LOCKSLIDE // MÃ HÓA & ĐÓNG GÓI BÀI GIẢNG CHO MACBOOK")
        lbl_app.setStyleSheet("font-size: 17px; font-weight: 900; color: #38BDF8; letter-spacing: 1.2px;")

        lbl_sub = QLabel("Tự động ghim cứng vào ID máy Mac khi mở lần đầu — Chống chia sẻ — Xuất file nén .ZIP độc lập")
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 400;")
        title_box.addWidget(lbl_app)
        title_box.addWidget(lbl_sub)
        header_bar.addLayout(title_box)
        header_bar.addStretch()

        badge = QLabel("100% OFFLINE AUTO-LOCK")
        badge.setStyleSheet("background-color: rgba(16, 185, 129, 0.15); color: #34D399; font-weight: 800; font-size: 11px; border: 1px solid #059669; border-radius: 12px; padding: 4px 12px;")
        header_bar.addWidget(badge)
        main_layout.addLayout(header_bar)

        # ----------------------------------------------------------------------
        # 2. KHUNG KÉO THẢ & DANH SÁCH FILE
        # ----------------------------------------------------------------------
        card_queue = QFrame()
        card_queue.setStyleSheet("background-color: #0E1524; border: 1px solid #1E293B; border-radius: 14px;")
        l_queue = QVBoxLayout(card_queue)
        l_queue.setContentsMargins(16, 14, 16, 14)
        l_queue.setSpacing(10)

        self.drop_zone = TechDropZone()
        self.drop_zone.files_dropped.connect(self.add_files_to_queue)
        l_queue.addWidget(self.drop_zone)

        queue_actions = QHBoxLayout()
        queue_actions.setSpacing(8)

        btn_browse = QPushButton("Chọn File PowerPoint...")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.setStyleSheet("background-color: #0284C7; color: #FFFFFF; font-weight: 700; border: none;")
        btn_browse.clicked.connect(self.browse_multiple_files)

        btn_remove = QPushButton("Xóa file đã chọn")
        btn_remove.clicked.connect(self.remove_selected_file)

        btn_clear = QPushButton("Xóa tất cả danh sách")
        btn_clear.clicked.connect(self.clear_all_files)

        self.lbl_queue_count = QLabel("0 FILE ĐÃ SẴN SÀNG")
        self.lbl_queue_count.setStyleSheet("font-size: 11px; font-weight: 700; color: #06B6D4; margin-left: 10px;")

        queue_actions.addWidget(btn_browse)
        queue_actions.addWidget(btn_remove)
        queue_actions.addWidget(btn_clear)
        queue_actions.addWidget(self.lbl_queue_count)
        queue_actions.addStretch()
        l_queue.addLayout(queue_actions)

        self.table_queue = QTableWidget()
        self.table_queue.setColumnCount(5)
        self.table_queue.setHorizontalHeaderLabels(["STT", "TÊN FILE POWERPOINT", "DUNG LƯỢNG", "MÃ LICENSE", "TRẠNG THÁI"])
        self.table_queue.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_queue.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_queue.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_queue.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_queue.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_queue.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_queue.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_queue.verticalHeader().setVisible(False)
        l_queue.addWidget(self.table_queue)

        main_layout.addWidget(card_queue, stretch=3)

        # ----------------------------------------------------------------------
        # 3. THANH HÀNH ĐỘNG MÃ HÓA & CẤU HÌNH BẢO MẬT
        # ----------------------------------------------------------------------
        action_card = QFrame()
        action_card.setStyleSheet("background-color: #0E1524; border: 1px solid #1E293B; border-radius: 14px;")
        l_action = QVBoxLayout(action_card)
        l_action.setContentsMargins(16, 14, 16, 14)
        l_action.setSpacing(10)

        # Dòng máy chủ kích hoạt 1 lần duy nhất (Google Sheets / Cloud URL)
        server_row = QHBoxLayout()
        server_row.setSpacing(10)

        lbl_server = QLabel("MÁY CHỦ BẢN QUYỀN:")
        lbl_server.setStyleSheet("font-size: 11px; font-weight: 700; color: #06B6D4;")
        self.txt_server_url = QLineEdit()
        self.txt_server_url.setPlaceholderText("Dán URL Google Apps Script để kích hoạt 1 lần duy nhất (chống chia sẻ file zip chưa giải nén)")
        self.txt_server_url.setStyleSheet("background-color: #111827; color: #38BDF8; font-family: 'SF Mono', Menlo, Consolas; font-size: 11px;")

        btn_guide = QPushButton("📋 Code & Hướng Dẫn Google Sheets (Miễn Phí)")
        btn_guide.setCursor(Qt.PointingHandCursor)
        btn_guide.setStyleSheet("background-color: #1E293B; color: #FACC15; font-size: 11px; font-weight: 700; border: 1px solid #EAB308; padding: 6px 12px;")
        btn_guide.clicked.connect(self.show_google_sheets_guide)

        server_row.addWidget(lbl_server)
        server_row.addWidget(self.txt_server_url, stretch=3)
        server_row.addWidget(btn_guide, stretch=0)
        l_action.addLayout(server_row)

        # Dòng tùy chọn quyền hạn & Mã máy khách
        cfg_row = QHBoxLayout()
        cfg_row.setSpacing(12)

        lbl_hwid = QLabel("MÃ MÁY MAC (HWID):")
        lbl_hwid.setStyleSheet("font-size: 11px; font-weight: 700; color: #38BDF8;")
        self.txt_target_hwid = QLineEdit()
        self.txt_target_hwid.setPlaceholderText("Để trống: Khách tự kích hoạt 1 lần (hoặc nhập mã máy để khóa cứng offline không cần mạng)")
        self.txt_target_hwid.setStyleSheet("background-color: #111827; color: #FACC15; font-family: 'SF Mono', Menlo, Consolas; font-size: 11px;")

        self.chk_allow_edit = QCheckBox("Cho phép sửa & lưu (Cmd+S)")
        self.chk_allow_edit.setChecked(True)
        self.chk_allow_edit.setStyleSheet("color: #34D399; font-weight: bold;")

        self.chk_block_save_as = QCheckBox("Cấm 'Save As' & 'Export'")
        self.chk_block_save_as.setChecked(True)
        self.chk_block_save_as.setStyleSheet("color: #38BDF8; font-weight: bold;")

        self.chk_block_copy = QCheckBox("Cấm 'Copy' (Cmd+C)")
        self.chk_block_copy.setChecked(True)
        self.chk_block_copy.setStyleSheet("color: #F87171; font-weight: bold;")

        cfg_row.addWidget(lbl_hwid)
        cfg_row.addWidget(self.txt_target_hwid, stretch=2)
        cfg_row.addWidget(self.chk_allow_edit)
        cfg_row.addWidget(self.chk_block_save_as)
        cfg_row.addWidget(self.chk_block_copy)
        l_action.addLayout(cfg_row)

        # Nút bấm hành động
        act_row = QHBoxLayout()
        act_row.setSpacing(10)

        self.btn_encode = QPushButton("BẮT ĐẦU MÃ HÓA & ĐÓNG GÓI .ZIP (0 FILE)")
        self.btn_encode.setCursor(Qt.PointingHandCursor)
        self.btn_encode.setEnabled(False)
        self.btn_encode.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #06B6D4);
                color: #FFFFFF; font-size: 13px; font-weight: 800;
                padding: 12px 20px; border-radius: 10px; border: none; letter-spacing: 0.8px;
            }
            QPushButton:hover { background: #0369A1; }
            QPushButton:disabled { background: #1E293B; color: #475569; }
        """)
        self.btn_encode.clicked.connect(self.start_batch_encoding)

        self.btn_open_result = QPushButton("Mở thư mục Result (.zip)")
        self.btn_open_result.setCursor(Qt.PointingHandCursor)
        self.btn_open_result.clicked.connect(self.open_result_dir)

        btn_test_open = QPushButton("Mở file mã hóa để kiểm tra")
        btn_test_open.setCursor(Qt.PointingHandCursor)
        btn_test_open.setStyleSheet("background-color: #1E293B; color: #34D399; font-weight: 700; border: 1px solid #059669;")
        btn_test_open.clicked.connect(self.open_encrypted_to_edit)

        act_row.addWidget(self.btn_encode, stretch=3)
        act_row.addWidget(self.btn_open_result, stretch=1)
        act_row.addWidget(btn_test_open, stretch=1)
        l_action.addLayout(act_row)

        self.smooth_progress = SmoothProgressBar()
        self.smooth_progress.setFixedHeight(6)
        self.smooth_progress.setTextVisible(False)
        self.smooth_progress.setStyleSheet("""
            QProgressBar { background-color: #111827; border: 1px solid #1E293B; border-radius: 3px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #00F0FF); border-radius: 2px; }
        """)
        self.smooth_progress.hide()
        l_action.addWidget(self.smooth_progress)

        self.lbl_status = QLabel("Hệ thống sẵn sàng xử lý. Mỗi bài giảng sẽ xuất ra 1 file nén .zip độc lập cho MacBook.")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 500;")
        l_action.addWidget(self.lbl_status)

        main_layout.addWidget(action_card, stretch=0)

    def show_google_sheets_guide(self):
        dlg = GoogleSheetsGuideDialog(self)
        dlg.exec_()

    def load_config(self):
        cfg_path = os.path.join(self.app_dir, "config.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.txt_server_url.setText(cfg.get("server_url", ""))
            except Exception:
                pass

    def save_config(self):
        cfg_path = os.path.join(self.app_dir, "config.json")
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"server_url": self.txt_server_url.text().strip()}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def open_result_dir(self):
        if sys.platform == "darwin":
            subprocess.Popen(["open", RESULT_DIR])
        elif sys.platform == "win32":
            os.startfile(RESULT_DIR)
        else:
            subprocess.Popen(["xdg-open", RESULT_DIR])

    # --------------------------------------------------------------------------
    # THAO TÁC FILE & HÀNG ĐỢI
    # --------------------------------------------------------------------------
    def browse_multiple_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn file PowerPoint", "", "File PowerPoint (*.pptx *.pptm *.ppt)"
        )
        if files:
            self.add_files_to_queue(files)

    def add_files_to_queue(self, file_paths):
        existing = {item["path"] for item in self.queued_files}
        for fp in file_paths:
            if fp not in existing:
                base = os.path.splitext(os.path.basename(fp))[0]
                size_mb = os.path.getsize(fp) / (1024 * 1024)
                size_str = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{os.path.getsize(fp) / 1024:.0f} KB"
                self.queued_files.append({
                    "path": fp,
                    "name": os.path.basename(fp),
                    "size": size_str,
                    "title": base,
                    "license_id": generate_license_code(),
                    "status": "Chờ mã hóa"
                })
        self.update_queue_table()

    def remove_selected_file(self):
        selected_rows = sorted(set(index.row() for index in self.table_queue.selectedIndexes()), reverse=True)
        for row in selected_rows:
            if 0 <= row < len(self.queued_files):
                del self.queued_files[row]
        self.update_queue_table()

    def clear_all_files(self):
        self.queued_files.clear()
        self.update_queue_table()

    def update_queue_table(self):
        self.table_queue.setRowCount(len(self.queued_files))
        for i, item in enumerate(self.queued_files):
            stt = QTableWidgetItem(f"{i + 1:02d}")
            stt.setTextAlignment(Qt.AlignCenter)
            stt.setForeground(QColor("#64748B"))
            self.table_queue.setItem(i, 0, stt)

            self.table_queue.setItem(i, 1, QTableWidgetItem(item["name"]))

            sz = QTableWidgetItem(item["size"])
            sz.setTextAlignment(Qt.AlignCenter)
            sz.setForeground(QColor("#94A3B8"))
            self.table_queue.setItem(i, 2, sz)

            lic_item = QTableWidgetItem(item["license_id"])
            lic_item.setForeground(QColor("#38BDF8"))
            lic_item.setFont(QFont("SF Mono", 10, QFont.Bold))
            lic_item.setTextAlignment(Qt.AlignCenter)
            self.table_queue.setItem(i, 3, lic_item)

            st_item = QTableWidgetItem(item.get("status", "Chờ mã hóa"))
            st_item.setTextAlignment(Qt.AlignCenter)
            st_item.setForeground(QColor("#94A3B8"))
            self.table_queue.setItem(i, 4, st_item)

        count = len(self.queued_files)
        self.lbl_queue_count.setText(f"{count} FILE ĐÃ SẴN SÀNG")
        self.btn_encode.setText(f"BẮT ĐẦU MÃ HÓA & ĐÓNG GÓI .ZIP ({count} FILE)")
        self.btn_encode.setEnabled(count > 0)

    # --------------------------------------------------------------------------
    # THỰC THI MÃ HÓA BATCH
    # --------------------------------------------------------------------------
    def start_batch_encoding(self):
        if not self.queued_files:
            return

        target_hwid = self.txt_target_hwid.text().strip().upper()
        server_url = self.txt_server_url.text().strip()
        allow_edit = self.chk_allow_edit.isChecked()
        block_save_as = self.chk_block_save_as.isChecked()
        block_copy = self.chk_block_copy.isChecked()

        if not server_url and not target_hwid:
            res = QMessageBox.question(
                self,
                "Khuyến nghị bảo mật cho MacBook",
                "Bạn chưa nhập link Google Sheets (để kích hoạt 1 lần duy nhất) và cũng chưa nhập mã máy Mac khách.\n\n"
                "• Nếu không dùng Google Sheets: Khách hàng nếu chia sẻ file .zip chưa giải nén thì máy khác vẫn có thể mở được.\n"
                "• Để chống chia sẻ tuyệt đối: Bạn chỉ cần dán link Google Sheets (hoàn toàn miễn phí, cài đặt 1 phút).\n\n"
                "Bạn có muốn mở hướng dẫn cài đặt Google Sheets ngay không?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            if res == QMessageBox.Yes:
                self.show_google_sheets_guide()
                return
            elif res == QMessageBox.Cancel:
                return

        self.save_config()

        self.btn_encode.setEnabled(False)
        self.smooth_progress.setMaximum(len(self.queued_files))
        self.smooth_progress.setValue(0)
        self.smooth_progress.show()

        self.worker = BatchEncodeWorkerMac(
            file_items=self.queued_files,
            result_dir=RESULT_DIR,
            allow_edit=allow_edit,
            block_save_as=block_save_as,
            block_copy=block_copy,
            bound_hwid=target_hwid,
            server_url=server_url
        )
        self.worker.row_status_signal.connect(self.on_row_status_update)
        self.worker.overall_progress_signal.connect(self.on_overall_progress_update)
        self.worker.finished_signal.connect(self.on_batch_finished)
        self.worker.start()

    def on_row_status_update(self, row, text, color_hex):
        if row < self.table_queue.rowCount():
            item = QTableWidgetItem(text)
            item.setForeground(QColor(color_hex))
            item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            item.setTextAlignment(Qt.AlignCenter)
            self.table_queue.setItem(row, 4, item)

    def on_overall_progress_update(self, current, total, text):
        self.smooth_progress.setValueSmooth(current)
        self.lbl_status.setText(f"TIẾN TRÌNH // {current}/{total} FILE : {text}")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #38BDF8; font-weight: 700;")

    def on_batch_finished(self, success_count, fail_count):
        self.btn_encode.setEnabled(True)
        self.smooth_progress.hide()
        self.lbl_status.setText(f"HOÀN TẤT // Đã xuất {success_count} file .zip cho MacBook, {fail_count} file thất bại.")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #34D399; font-weight: 700;")

        msg_body = (
            f"Hệ thống đã mã hóa và đóng gói thành công {success_count} bài giảng cho MacBook!\n\n"
            f"Mỗi bài giảng đã được đóng gói thành 1 TẬP NÉN (.ZIP) riêng biệt tại:\n"
            f"{RESULT_DIR}\n\n"
            f"Đặc tính bảo vệ tuyệt đối trên macOS:\n"
            f"• Bạn chỉ cần gửi file .zip của bài giảng đó cho khách hàng dùng Mac.\n"
            f"• Khách hàng giải nén và nhấp đúp file 'Mo_[Tên].command' để mở bài giảng.\n"
            f"• Bài giảng sẽ TỰ ĐỘNG KHÓA VÀ GHIM CỐ ĐỊNH VÀO MÁY MAC ĐÓ ngay lần mở đầu tiên.\n"
            f"• Nếu khách copy chuyển sang bất kỳ máy tính nào khác -> KHÔNG THỂ MỞ ĐƯỢC!\n"
            f"• Khách hàng vẫn có thể gõ sửa bài và bấm Lưu (Cmd+S) bình thường.\n"
            f"• Chặn tuyệt đối Save As và Copy để bảo vệ 100% bản quyền tài liệu."
        )
        dlg = TechNotificationDialog("XUẤT BẢN FILE NÉN THÀNH CÔNG", msg_body, self)
        dlg.exec_()

    def open_encrypted_to_edit(self):
        """Mở nhanh một bài giảng mã hóa để kiểm tra hoặc chỉnh sửa"""
        f, _ = QFileDialog.getOpenFileName(
            self, "Chọn bài giảng mã hóa cần mở", RESULT_DIR, "Bài giảng bảo mật (*.encppt *.zip);;Tất cả file (*.*)"
        )
        if f and os.path.exists(f):
            subprocess.Popen([sys.executable, os.path.join(self.app_dir, "editor_player_mac.py"), f])


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LockSlide Studio macOS")
    win = LockSlideStudioMacApp()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
