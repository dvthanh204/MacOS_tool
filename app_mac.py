"""
LockSlide Studio macOS v2.5 - Hệ Thống Mã Hóa & Quản Lý Bản Quyền Bài Giảng PowerPoint Cho MacBook
Hỗ trợ mở bài giảng ở CHẾ ĐỘ CHỈNH SỬA (Editable Mode) & Tự Động Lưu (Auto-Save Sync)
Thiết Kế Hiện Đại, Tech Neon Dark Theme, Animation Công Nghệ, Tối ưu 100% cho MacBook (macOS)
"""

import sys
import os
import random
import datetime
import sqlite3
import threading
import math

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFileDialog, QDialog, QFrame,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QProgressBar, QCheckBox, QComboBox, QMessageBox
)
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QPen, QLinearGradient
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty

import crypto_engine_mac
from license_server import app as flask_app, DB_FILE, start_server_in_background
from ribbon_policy_mac import inject_ribbon_policy
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
# WIDGET ANIMATION CÔNG NGHỆ: PULSING STATUS RADAR DOT
# ==============================================================================
class PulsingStatusDot(QWidget):
    """Điểm tròn phát sáng nhịp thở (Breathing/Pulse) theo phong cách Radar Công Nghệ"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self._glow_alpha = 180
        self._step = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_pulse)
        self.timer.start(40)

    def _animate_pulse(self):
        self._step += 0.08
        self._glow_alpha = int(170 + 85 * math.sin(self._step))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        halo_color = QColor(16, 185, 129, int(self._glow_alpha * 0.45))
        painter.setBrush(QBrush(halo_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(1, 1, 12, 12)

        core_color = QColor(52, 211, 153, min(255, self._glow_alpha + 30))
        painter.setBrush(QBrush(core_color))
        painter.drawEllipse(3, 3, 8, 8)


# ==============================================================================
# WIDGET ANIMATION CÔNG NGHỆ: KHUNG KÉO THẢ HIỆU ỨNG GLOW
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
        return getattr(self, '_glow_progress', 0.0)

    @glowProgress.setter
    def glowProgress(self, val):
        self._glow_progress = float(val)
        r = int(51 + (6 - 51) * val)
        g = int(65 + (182 - 65) * val)
        b = int(85 + (212 - 85) * val)
        bg_alpha = int(10 + 25 * val)
        self.setStyleSheet(f"""
            TechDropZone {{
                background-color: rgba(6, 182, 212, {bg_alpha / 255.0:.3f});
                border: 2px dashed rgb({r}, {g}, {b});
                border-radius: 12px;
            }}
        """)

    def init_ui(self):
        self.glowProgress = 0.0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignCenter)

        self.lbl_main = QLabel(" KÉO THẢ HOẶC CHỌN FILE POWERPOINT CHO MACBOOK TẠI ĐÂY")
        self.lbl_main.setStyleSheet("font-size: 13px; font-weight: bold; color: #E2E8F0; letter-spacing: 1px;")
        self.lbl_main.setAlignment(Qt.AlignCenter)

        self.lbl_sub = QLabel("Mã hóa hàng loạt .pptx / .ppt — Xuất trọn gói Mo_[Tên].command chạy ngay trên macOS — Hỗ trợ Chỉnh sửa & Tự động lưu")
        self.lbl_sub.setStyleSheet("font-size: 11px; color: #67E8F9; margin-top: 4px;")
        self.lbl_sub.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.lbl_main)
        layout.addWidget(self.lbl_sub)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.anim.stop()
            self.anim.setStartValue(self._glow_progress)
            self.anim.setEndValue(1.0)
            self.anim.start()

    def dragLeaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._glow_progress)
        self.anim.setEndValue(0.0)
        self.anim.start()

    def dropEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._glow_progress)
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
# THANH TIẾN TRÌNH SMOOTH PROGRESS BAR
# ==============================================================================
class SmoothProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._anim_val = 0.0
        self.anim = QPropertyAnimation(self, b"animatedValue")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)

    @pyqtProperty(float)
    def animatedValue(self):
        return self._anim_val

    @animatedValue.setter
    def animatedValue(self, val):
        self._anim_val = val
        super().setValue(int(val))

    def setValueSmooth(self, target_val):
        self.anim.stop()
        self.anim.setStartValue(float(self.value()))
        self.anim.setEndValue(float(target_val))
        self.anim.start()


# ==============================================================================
# HỘP THOẠI MODAL CÔNG NGHỆ
# ==============================================================================
class TechNotificationDialog(QDialog):
    def __init__(self, title_text: str, content_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title_text)
        self.setFixedSize(540, 360)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        card = QFrame(self)
        card.setStyleSheet("""
            QFrame {
                background-color: #0E1524;
                border: 1px solid #1E293B;
                border-radius: 12px;
            }
        """)
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(28, 24, 28, 24)
        card_l.setSpacing(16)

        lbl_t = QLabel(title_text)
        lbl_t.setStyleSheet("font-size: 16px; font-weight: 800; color: #38BDF8; letter-spacing: 1px;")
        lbl_t.setAlignment(Qt.AlignCenter)
        card_l.addWidget(lbl_t)

        lbl_c = QLabel(content_text)
        lbl_c.setWordWrap(True)
        lbl_c.setStyleSheet("font-size: 12px; color: #E2E8F0; line-height: 1.5;")
        card_l.addWidget(lbl_c)

        card_l.addStretch()

        btn_ok = QPushButton("Xác nhận / Đóng")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #06B6D4);
                color: #FFFFFF; font-weight: bold; padding: 10px; border-radius: 8px; border: none; font-size: 12px;
            }
            QPushButton:hover { background: #0369A1; }
        """)
        btn_ok.clicked.connect(self.accept)
        card_l.addWidget(btn_ok)

        layout.addWidget(card)


class TechConfirmDialog(QDialog):
    def __init__(self, title_text: str, content_text: str, confirm_btn_text: str = "Xác nhận", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title_text)
        self.setFixedSize(520, 320)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        card = QFrame(self)
        card.setStyleSheet("background-color: #0E1524; border: 1px solid #1E293B; border-radius: 12px;")
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(26, 22, 26, 22)
        card_l.setSpacing(14)

        lbl_t = QLabel(title_text)
        lbl_t.setStyleSheet("font-size: 15px; font-weight: 800; color: #F87171; letter-spacing: 0.8px;")
        lbl_t.setAlignment(Qt.AlignCenter)
        card_l.addWidget(lbl_t)

        lbl_c = QLabel(content_text)
        lbl_c.setWordWrap(True)
        lbl_c.setStyleSheet("font-size: 12px; color: #CBD5E1; line-height: 1.4;")
        card_l.addWidget(lbl_c)

        card_l.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_cancel = QPushButton("Hủy bỏ")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet("background-color: #1E293B; color: #94A3B8; border: 1px solid #334155; padding: 9px; border-radius: 8px;")
        btn_cancel.clicked.connect(self.reject)

        btn_conf = QPushButton(confirm_btn_text)
        btn_conf.setCursor(Qt.PointingHandCursor)
        btn_conf.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; border: none; padding: 9px; border-radius: 8px;")
        btn_conf.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_conf)
        card_l.addLayout(btn_row)

        layout.addWidget(card)


# ==============================================================================
# WORKER LUỒNG MÃ HÓA HÀNG LOẠT CHO MAC (BATCH ENCODE THREAD)
# ==============================================================================
class BatchEncodeWorkerMac(QThread):
    row_status_signal = pyqtSignal(int, str, str)  # row, text, color_hex
    overall_progress_signal = pyqtSignal(int, int, str)  # current, total, text
    finished_signal = pyqtSignal(int, int)  # success, failed

    def __init__(self, file_items, server_url, result_dir, allow_edit=True, block_save_as=True, block_copy=True, create_zip=True):
        super().__init__()
        self.file_items = file_items
        self.server_url = server_url
        self.result_dir = result_dir
        self.allow_edit = allow_edit
        self.block_save_as = block_save_as
        self.block_copy = block_copy
        self.create_zip = create_zip

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

            folder_name = clean_name
            file_out_dir = os.path.join(self.result_dir, folder_name)
            os.makedirs(file_out_dir, exist_ok=True)

            self.row_status_signal.emit(idx, "Đang đọc dữ liệu...", "#FACC15")
            self.overall_progress_signal.emit(idx + 1, total, f"Đang mã hóa ({idx + 1}/{total}): {os.path.basename(file_path)}")

            try:
                with open(file_path, "rb") as f_in:
                    pres_bytes = f_in.read()

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
                    target_os="MACOS"
                )

                # Ghi vào SQLite Server DB
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    with sqlite3.connect(DB_FILE) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT OR REPLACE INTO licenses (license_id, title, status, created_at)
                            VALUES (?, ?, 'PENDING', ?)
                        """, (lic_id, title, now))
                        conn.commit()
                except Exception:
                    pass

                # Đóng gói cho MacBook
                self.row_status_signal.emit(idx, "Đang đóng gói macOS...", "#818CF8")
                mac_packager.package_for_mac(
                    output_dir=file_out_dir,
                    base_name=folder_name,
                    payload_bytes=payload,
                    app_root_dir=APP_DIR,
                    create_zip=self.create_zip
                )

                self.row_status_signal.emit(idx, "Hoàn tất (Sửa & Lưu Mac)", "#34D399")
                success += 1
            except Exception as e:
                err_msg = str(e).split("\n")[0]
                self.row_status_signal.emit(idx, f"Lỗi: {err_msg[:24]}", "#F87171")
                failed += 1

        self.finished_signal.emit(success, failed)


# ==============================================================================
# CỬA SỔ CHÍNH: LOCKSLIDE STUDIO MACOS APP
# ==============================================================================
class LockSlideStudioMacApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_dir = APP_DIR
        self.setAcceptDrops(True)
        self.queued_files = []

        # Khởi động máy chủ bản quyền chạy ngầm
        self.start_background_server()
        self.init_ui()

        # Timer cập nhật bảng giám sát bản quyền LIVE mỗi 3 giây
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_client_records)
        self.timer.start(3000)

    def start_background_server(self):
        start_server_in_background(host="0.0.0.0", port=5000)

    def init_ui(self):
        self.setWindowTitle("LockSlide Studio macOS // PPT Security Suite (Editable & Auto-Save)")
        self.setFixedSize(1080, 920)
        self.setStyleSheet("""
            QMainWindow { background-color: #0A0E17; }
            QLabel { color: #F8FAFC; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
            QLineEdit {
                background-color: #111827; color: #F8FAFC; border: 1px solid #1E293B;
                border-radius: 8px; padding: 7px 12px; font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #06B6D4; background-color: #131F33; }
            QPushButton {
                background-color: #1E293B; color: #F8FAFC; border: 1px solid #334155;
                border-radius: 8px; padding: 8px 16px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background-color: #334155; border: 1px solid #475569; }
            QPushButton:pressed { background-color: #0F172A; }
            QTableWidget {
                background-color: #0D131F; color: #F8FAFC; gridline-color: #1A2333;
                border: 1px solid #1E293B; border-radius: 10px; font-size: 12px;
            }
            QHeaderView::section {
                background-color: #090E17; color: #06B6D4; font-weight: 700;
                font-size: 11px; letter-spacing: 0.8px; padding: 8px 10px;
                border: none; border-bottom: 1px solid #1E293B;
            }
            QTableCornerButton::section { background-color: #090E17; border: none; }
            QTableWidget::item:selected { background-color: #1E293B; }
            QScrollBar:vertical { background: #0A0E17; width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #1E293B; border-radius: 4px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #334155; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QCheckBox { color: #E2E8F0; font-size: 12px; font-weight: 600; spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #334155; background: #111827; }
            QCheckBox::indicator:checked { background: #0284C7; border-color: #00F0FF; }
        """)

        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 18, 24, 18)
        main_layout.setSpacing(12)

        # ----------------------------------------------------------------------
        # 1. HEADER BAR: LOGO & STATUS RADAR
        # ----------------------------------------------------------------------
        header_bar = QHBoxLayout()

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_app = QLabel(" LOCKSLIDE STUDIO MAC // HỆ THỐNG MÃ HÓA BÀI GIẢNG (MACBOOK)")
        lbl_app.setStyleSheet("font-size: 18px; font-weight: 800; color: #38BDF8; letter-spacing: 1.2px;")

        lbl_sub = QLabel("Bảo mật PowerPoint trên macOS — Tự động ghim Apple HWID lần đầu (TOFU) — Cho phép Sửa & Lưu bài bình thường")
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 400;")
        title_box.addWidget(lbl_app)
        title_box.addWidget(lbl_sub)
        header_bar.addLayout(title_box)

        header_bar.addStretch()

        status_box = QHBoxLayout()
        status_box.setSpacing(8)
        self.radar_dot = PulsingStatusDot()
        self.lbl_server_status = QLabel("SERVER ONLINE (PORT 5000)")
        self.lbl_server_status.setStyleSheet("font-size: 11px; font-weight: 700; color: #34D399; letter-spacing: 0.8px;")
        status_box.addWidget(self.radar_dot)
        status_box.addWidget(self.lbl_server_status)
        header_bar.addLayout(status_box)

        main_layout.addLayout(header_bar)

        # ----------------------------------------------------------------------
        # 2. KHUNG KÉO THẢ & NÚT CHỌN FILE
        # ----------------------------------------------------------------------
        self.drop_zone = TechDropZone()
        self.drop_zone.files_dropped.connect(self.add_files_to_queue)
        self.drop_zone.setFixedHeight(85)
        main_layout.addWidget(self.drop_zone)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_select_files = QPushButton("Chọn File PowerPoint...")
        self.btn_select_files.setCursor(Qt.PointingHandCursor)
        self.btn_select_files.clicked.connect(self.open_file_dialog)

        self.btn_clear_queue = QPushButton("Xóa Danh Sách Chờ")
        self.btn_clear_queue.setCursor(Qt.PointingHandCursor)
        self.btn_clear_queue.clicked.connect(self.clear_queue)

        btn_row.addWidget(self.btn_select_files)
        btn_row.addWidget(self.btn_clear_queue)
        btn_row.addStretch()

        # Input Server URL
        lbl_srv = QLabel("Địa chỉ Server:")
        lbl_srv.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold;")
        self.txt_server_url = QLineEdit("http://127.0.0.1:5000")
        self.txt_server_url.setFixedWidth(220)
        btn_row.addWidget(lbl_srv)
        btn_row.addWidget(self.txt_server_url)

        main_layout.addLayout(btn_row)

        # ----------------------------------------------------------------------
        # 3. BẢNG DANH SÁCH FILE CHỜ MÃ HÓA
        # ----------------------------------------------------------------------
        self.table_queue = QTableWidget()
        self.table_queue.setColumnCount(4)
        self.table_queue.setHorizontalHeaderLabels(["TÊN FILE BÀI GIẢNG", "TIÊU ĐỀ", "MÃ LICENSE", "TRẠNG THÁI"])
        self.table_queue.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_queue.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table_queue.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_queue.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_queue.setColumnWidth(1, 220)
        self.table_queue.setFixedHeight(170)
        self.table_queue.setSelectionBehavior(QAbstractItemView.SelectRows)
        main_layout.addWidget(self.table_queue)

        # ----------------------------------------------------------------------
        # 4. THANH TIẾN TRÌNH & CÁC TÙY CHỌN BẢO MẬT
        # ----------------------------------------------------------------------
        self.progress_bar = SmoothProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #111827; border: none; border-radius: 3px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #00F0FF); border-radius: 3px; }
        """)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        opt_box = QFrame()
        opt_box.setStyleSheet("background-color: #0E1524; border: 1px solid #1E293B; border-radius: 10px; padding: 6px 12px;")
        opt_layout = QHBoxLayout(opt_box)
        opt_layout.setContentsMargins(8, 6, 8, 6)

        self.chk_allow_edit = QCheckBox("Cho phép mở sửa bài giảng (Edit)")
        self.chk_allow_edit.setChecked(True)
        self.chk_allow_edit.setToolTip("Khách hàng có thể gõ chữ, chỉnh sửa nội dung, dán (Cmd+V) và lưu lại (Cmd+S)")

        self.chk_block_save_as = QCheckBox("Khóa 'Save As' chống lưu file mới")
        self.chk_block_save_as.setChecked(True)
        self.chk_block_save_as.setToolTip("Ẩn và vô hiệu hóa hoàn toàn Save As, Save a Copy, Export trên PowerPoint Mac")

        self.chk_block_copy = QCheckBox("Khóa Copy / Sao chép nội dung")
        self.chk_block_copy.setChecked(True)
        self.chk_block_copy.setToolTip("Khóa Copy/Cut trên Ribbon và Context Menu")

        self.chk_create_zip = QCheckBox("Đóng gói .zip bảo lưu quyền macOS")
        self.chk_create_zip.setChecked(True)
        self.chk_create_zip.setToolTip("Tự động xuất file .zip chứa file .encppt và script Mo_...command có quyền thực thi sẵn")

        opt_layout.addWidget(self.chk_allow_edit)
        opt_layout.addWidget(self.chk_block_save_as)
        opt_layout.addWidget(self.chk_block_copy)
        opt_layout.addWidget(self.chk_create_zip)
        opt_layout.addStretch()

        self.btn_start_encode = QPushButton("⚡ BẮT ĐẦU MÃ HÓA & ĐÓNG GÓI MACBOOK")
        self.btn_start_encode.setCursor(Qt.PointingHandCursor)
        self.btn_start_encode.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #06B6D4);
                color: #FFFFFF; font-weight: 800; padding: 10px 20px; border-radius: 8px; border: none; font-size: 12px; letter-spacing: 0.5px;
            }
            QPushButton:hover { background: #0369A1; }
        """)
        self.btn_start_encode.clicked.connect(self.start_batch_encode)
        opt_layout.addWidget(self.btn_start_encode)

        main_layout.addWidget(opt_box)

        # ----------------------------------------------------------------------
        # 5. BẢNG GIÁM SÁT BẢN QUYỀN THỜI GIAN THỰC (LIVE CLIENT MONITOR)
        # ----------------------------------------------------------------------
        live_header = QHBoxLayout()
        lbl_live = QLabel("BẢNG GIÁM SÁT BẢN QUYỀN MACBOOK THỜI GIAN THỰC (AUTO-LOCK & REVOKE)")
        lbl_live.setStyleSheet("font-size: 13px; font-weight: 800; color: #38BDF8; letter-spacing: 0.8px;")
        live_header.addWidget(lbl_live)
        live_header.addStretch()

        btn_open_result = QPushButton("Mở Thư Mục Result Mac")
        btn_open_result.setCursor(Qt.PointingHandCursor)
        btn_open_result.clicked.connect(self.open_result_dir)
        live_header.addWidget(btn_open_result)

        btn_open_dash = QPushButton("Mở Web Dashboard")
        btn_open_dash.setCursor(Qt.PointingHandCursor)
        btn_open_dash.clicked.connect(self.open_web_dashboard)
        live_header.addWidget(btn_open_dash)

        main_layout.addLayout(live_header)

        self.table_clients = QTableWidget()
        self.table_clients.setColumnCount(7)
        self.table_clients.setHorizontalHeaderLabels([
            "MÃ LICENSE", "TIÊU ĐỀ BÀI GIẢNG", "MÃ MÁY ĐÃ GHIM (HWID)",
            "TRẠNG THÁI", "NGÀY TẠO", "KÍCH HOẠT LÚC", "THAO TÁC QUẢN TRỊ"
        ])
        self.table_clients.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_clients.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_clients.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_clients.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_clients.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_clients.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_clients.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table_clients.setSelectionBehavior(QAbstractItemView.SelectRows)
        main_layout.addWidget(self.table_clients)

        self.load_client_records()

    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn một hoặc nhiều bài giảng PowerPoint",
            "", "PowerPoint Files (*.pptx *.pptm *.ppt);;All Files (*.*)"
        )
        if files:
            self.add_files_to_queue(files)

    def add_files_to_queue(self, file_paths):
        for fp in file_paths:
            if fp not in [it["path"] for it in self.queued_files]:
                base_name = os.path.splitext(os.path.basename(fp))[0]
                lic_code = generate_license_code()
                self.queued_files.append({
                    "path": fp,
                    "title": base_name,
                    "license_id": lic_code
                })
        self.refresh_queue_table()

    def refresh_queue_table(self):
        self.table_queue.setRowCount(len(self.queued_files))
        for row, item in enumerate(self.queued_files):
            it_name = QTableWidgetItem(os.path.basename(item["path"]))
            it_title = QTableWidgetItem(item["title"])
            it_lic = QTableWidgetItem(item["license_id"])
            it_lic.setFont(QFont("SF Mono, Menlo, Consolas", 10, QFont.Bold))
            it_lic.setForeground(QColor("#38BDF8"))
            it_status = QTableWidgetItem("Sẵn sàng")
            it_status.setForeground(QColor("#94A3B8"))

            self.table_queue.setItem(row, 0, it_name)
            self.table_queue.setItem(row, 1, it_title)
            self.table_queue.setItem(row, 2, it_lic)
            self.table_queue.setItem(row, 3, it_status)

    def clear_queue(self):
        self.queued_files.clear()
        self.table_queue.setRowCount(0)
        self.progress_bar.setValue(0)

    def start_batch_encode(self):
        if not self.queued_files:
            TechNotificationDialog("Thông báo", "Vui lòng chọn hoặc kéo thả ít nhất 1 file PowerPoint vào danh sách!", self).exec_()
            return

        server_url = self.txt_server_url.text().strip()
        allow_edit = self.chk_allow_edit.isChecked()
        block_save_as = self.chk_block_save_as.isChecked()
        block_copy = self.chk_block_copy.isChecked()
        create_zip = self.chk_create_zip.isChecked()

        self.btn_start_encode.setEnabled(False)
        self.progress_bar.setValue(0)

        self.worker = BatchEncodeWorkerMac(
            file_items=self.queued_files,
            server_url=server_url,
            result_dir=RESULT_DIR,
            allow_edit=allow_edit,
            block_save_as=block_save_as,
            block_copy=block_copy,
            create_zip=create_zip
        )
        self.worker.row_status_signal.connect(self.on_row_status_update)
        self.worker.overall_progress_signal.connect(self.on_overall_progress)
        self.worker.finished_signal.connect(self.on_batch_finished)
        self.worker.start()

    def on_row_status_update(self, row, text, color_hex):
        item = QTableWidgetItem(text)
        item.setForeground(QColor(color_hex))
        item.setFont(QFont("Arial", 10, QFont.Bold))
        self.table_queue.setItem(row, 3, item)

    def on_overall_progress(self, current, total, text):
        pct = int((current / total) * 100)
        self.progress_bar.setValueSmooth(pct)

    def on_batch_finished(self, success, failed):
        self.btn_start_encode.setEnabled(True)
        self.load_client_records()
        msg = f"Đã hoàn thành mã hóa {success} bài giảng cho MacBook!\n\n"
        if failed > 0:
            msg += f"Có {failed} bài giảng gặp lỗi.\n\n"
        msg += f"Các gói cài đặt và file Mo_...command đã được xuất vào thư mục:\n{RESULT_DIR}\n\nBạn có thể gửi file .zip cho học viên Mac ngay bây giờ."
        TechNotificationDialog("Mã Hóa Hoàn Tất", msg, self).exec_()

    def load_client_records(self):
        if not os.path.exists(DB_FILE):
            return

        try:
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT license_id, title, bound_hwid, status, created_at, activated_at
                    FROM licenses ORDER BY created_at DESC
                """)
                rows = cursor.fetchall()

            self.table_clients.setRowCount(len(rows))
            for r_idx, r in enumerate(rows):
                lic_id, title, hwid, status, created_at, activated_at = r

                it_lic = QTableWidgetItem(lic_id)
                it_lic.setFont(QFont("SF Mono, Menlo, Consolas", 10, QFont.Bold))
                it_lic.setForeground(QColor("#38BDF8"))

                it_title = QTableWidgetItem(title or "—")
                it_hwid = QTableWidgetItem(hwid if hwid else "— Chờ mở lần đầu —")
                it_hwid.setFont(QFont("SF Mono, Menlo, Consolas", 9))
                it_hwid.setForeground(QColor("#00F0FF" if hwid else "#64748B"))

                # Status Badge
                it_status = QTableWidgetItem()
                if status == "ACTIVATED":
                    it_status.setText("ĐÃ GHIM MÁY")
                    it_status.setForeground(QColor("#34D399"))
                elif status == "REVOKED":
                    it_status.setText("ĐÃ THU HỒI")
                    it_status.setForeground(QColor("#F87171"))
                else:
                    it_status.setText("CHỜ MỞ (PENDING)")
                    it_status.setForeground(QColor("#FBBF24"))
                it_status.setFont(QFont("Arial", 9, QFont.Bold))

                it_created = QTableWidgetItem(created_at or "—")
                it_created.setForeground(QColor("#94A3B8"))

                it_activated = QTableWidgetItem(activated_at or "—")
                it_activated.setForeground(QColor("#94A3B8"))

                self.table_clients.setItem(r_idx, 0, it_lic)
                self.table_clients.setItem(r_idx, 1, it_title)
                self.table_clients.setItem(r_idx, 2, it_hwid)
                self.table_clients.setItem(r_idx, 3, it_status)
                self.table_clients.setItem(r_idx, 4, it_created)
                self.table_clients.setItem(r_idx, 5, it_activated)

                # Nút Thao Tác
                action_widget = QWidget()
                act_layout = QHBoxLayout(action_widget)
                act_layout.setContentsMargins(4, 2, 4, 2)
                act_layout.setSpacing(6)

                if status == "REVOKED":
                    btn_restore = QPushButton("Khôi phục")
                    btn_restore.setCursor(Qt.PointingHandCursor)
                    btn_restore.setStyleSheet("background-color: rgba(52, 211, 153, 0.15); color: #34D399; border: 1px solid #059669; padding: 4px 8px; border-radius: 4px; font-size: 11px;")
                    btn_restore.clicked.connect(lambda _, l=lic_id: self.action_restore(l))
                    act_layout.addWidget(btn_restore)
                else:
                    if hwid:
                        btn_reset = QPushButton("Đổi máy")
                        btn_reset.setCursor(Qt.PointingHandCursor)
                        btn_reset.setStyleSheet("background-color: rgba(250, 204, 21, 0.15); color: #FACC15; border: 1px solid #A16207; padding: 4px 8px; border-radius: 4px; font-size: 11px;")
                        btn_reset.clicked.connect(lambda _, l=lic_id: self.action_reset(l))
                        act_layout.addWidget(btn_reset)

                    btn_revoke = QPushButton("Thu hồi")
                    btn_revoke.setCursor(Qt.PointingHandCursor)
                    btn_revoke.setStyleSheet("background-color: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid #991B1B; padding: 4px 8px; border-radius: 4px; font-size: 11px;")
                    btn_revoke.clicked.connect(lambda _, l=lic_id: self.action_revoke(l))
                    act_layout.addWidget(btn_revoke)

                self.table_clients.setCellWidget(r_idx, 6, action_widget)

        except Exception as e:
            pass

    def action_revoke(self, license_id):
        dlg = TechConfirmDialog("Xác nhận thu hồi", f"Bạn có chắc muốn THU HỒI bản quyền mã:\n{license_id}?\n\nNgười dùng máy Mac này sẽ bị chặn mở bài giảng ngay lập tức!", "Thu hồi ngay", self)
        if dlg.exec_() == QDialog.Accepted:
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE licenses SET status = 'REVOKED' WHERE license_id = ?", (license_id,))
                conn.commit()
            self.load_client_records()

    def action_reset(self, license_id):
        dlg = TechConfirmDialog("Xác nhận đổi máy tính", f"Cho phép khách hàng chuyển bài giảng mã:\n{license_id} sang một máy Mac khác?\n\nMã máy cũ sẽ được gỡ bỏ và máy Mac mới mở file sẽ được ghim thay thế.", "Đổi máy tính", self)
        if dlg.exec_() == QDialog.Accepted:
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE licenses SET bound_hwid = NULL, status = 'PENDING', activated_at = NULL WHERE license_id = ?", (license_id,))
                conn.commit()
            self.load_client_records()

    def action_restore(self, license_id):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT bound_hwid FROM licenses WHERE license_id = ?", (license_id,))
            row = cursor.fetchone()
            new_st = "ACTIVATED" if row and row[0] else "PENDING"
            cursor.execute("UPDATE licenses SET status = ? WHERE license_id = ?", (new_st, license_id))
            conn.commit()
        self.load_client_records()

    def open_result_dir(self):
        if sys.platform == "darwin":
            subprocess.Popen(["open", RESULT_DIR])
        elif sys.platform == "win32":
            os.startfile(RESULT_DIR)
        else:
            subprocess.Popen(["xdg-open", RESULT_DIR])

    def open_web_dashboard(self):
        import webbrowser
        webbrowser.open("http://127.0.0.1:5000")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LockSlide Studio macOS")
    win = LockSlideStudioMacApp()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
