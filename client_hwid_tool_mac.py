"""
Module: client_hwid_tool_mac.py
Công cụ trích xuất và hiển thị mã máy Mac (HWID) dành cho học viên / khách hàng MacBook.
- Nhận diện chính xác Apple Hardware UUID + Mac Serial Number.
- Hỗ trợ giao diện đồ họa hiện đại (PyQt5 / Tkinter native macOS).
- 1-Click sao chép vào Clipboard để gửi cho tác giả.
"""

import sys
import subprocess
from crypto_engine_mac import get_machine_hwid, get_mac_hardware_uuid_and_serial

def copy_to_clipboard(text: str):
    if sys.platform == "darwin":
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
            return
        except Exception:
            pass
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.clipboard().setText(text)
            return
    except Exception:
        pass
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


def run_gui():
    hwid = get_machine_hwid()
    uuid_str, serial_str = get_mac_hardware_uuid_and_serial()

    try:
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QWidget, QLabel, QPushButton,
            QVBoxLayout, QHBoxLayout, QMessageBox, QFrame
        )
        from PyQt5.QtGui import QFont, QColor
        from PyQt5.QtCore import Qt

        app = QApplication(sys.argv)
        win = QMainWindow()
        win.setWindowTitle("LockSlide macOS - Định Danh Thiết Bị (HWID)")
        win.setFixedSize(540, 380)
        win.setStyleSheet("""
            QMainWindow { background-color: #0A0E17; }
            QLabel { color: #F8FAFC; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        """)

        central = QWidget(win)
        win.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(16)

        title = QLabel(" ĐỊNH DANH MÁY MACBOOK (HARDWARE ID)")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8; letter-spacing: 1px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("Mã máy này được dùng để cấp phép bài giảng PowerPoint bảo mật LockSlide.\nHãy sao chép và gửi mã này cho giảng viên / tác giả khóa học của bạn.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 1.4;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        card = QFrame()
        card.setStyleSheet("background-color: #0E1524; border: 1px solid #1E293B; border-radius: 12px; padding: 16px;")
        card_l = QVBoxLayout(card)
        card_l.setSpacing(10)

        lbl_code = QLabel(hwid)
        lbl_code.setStyleSheet("font-size: 20px; font-weight: 800; color: #00F0FF; font-family: 'SF Mono', Menlo, Consolas; letter-spacing: 2px;")
        lbl_code.setAlignment(Qt.AlignCenter)
        card_l.addWidget(lbl_code)

        if uuid_str or serial_str:
            detail_txt = f"Serial: {serial_str or 'N/A'} | UUID: {uuid_str[:18]}..." if uuid_str else f"Serial: {serial_str}"
            lbl_detail = QLabel(detail_txt)
            lbl_detail.setStyleSheet("color: #64748B; font-size: 11px;")
            lbl_detail.setAlignment(Qt.AlignCenter)
            card_l.addWidget(lbl_detail)

        layout.addWidget(card)

        btn_copy = QPushButton("SAO CHÉP MÃ MÁY (COPY)")
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #06B6D4);
                color: #FFFFFF; font-weight: bold; padding: 12px; border-radius: 8px; border: none; font-size: 13px; letter-spacing: 0.5px;
            }
            QPushButton:hover { background: #0369A1; }
        """)

        def on_copy():
            copy_to_clipboard(hwid)
            QMessageBox.information(win, "Thành công", f"Đã chép mã máy Mac vào Clipboard:\n\n{hwid}\n\nHãy dán (Cmd+V) gửi cho tác giả bài giảng.")

        btn_copy.clicked.connect(on_copy)
        layout.addWidget(btn_copy)
        layout.addStretch()

        win.show()
        sys.exit(app.exec_())

    except ImportError:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.title("LockSlide macOS - Định Danh Thiết Bị (HWID)")
        root.geometry("500x340")
        root.configure(bg="#0A0E17")

        tk.Label(root, text=" ĐỊNH DANH MÁY MACBOOK (HWID)", fg="#38BDF8", bg="#0A0E17", font=("Helvetica", 14, "bold")).pack(pady=15)
        
        tk.Label(
            root,
            text="Mã máy này được dùng để cấp phép bài giảng PowerPoint bảo mật.\nHãy sao chép và gửi mã này cho giảng viên / tác giả khóa học.",
            fg="#94A3B8", bg="#0A0E17", font=("Helvetica", 11), justify="center"
        ).pack(pady=5)

        card = tk.Frame(root, bg="#0E1524", highlightbackground="#1E293B", highlightthickness=1, padx=20, pady=15)
        card.pack(fill="x", padx=30, pady=15)

        tk.Label(card, text=hwid, fg="#00F0FF", bg="#0E1524", font=("Menlo", 18, "bold")).pack()

        def on_copy_tk():
            copy_to_clipboard(hwid)
            messagebox.showinfo("Đã sao chép", f"Đã copy mã máy: {hwid}\nHãy dán (Cmd+V) gửi cho tác giả.")

        btn = tk.Button(root, text="SAO CHÉP MÃ MÁY (COPY)", command=on_copy_tk, bg="#0284C7", fg="white", font=("Helvetica", 12, "bold"), padx=20, pady=10)
        btn.pack(pady=15)

        root.mainloop()


if __name__ == "__main__":
    if "--cli" in sys.argv:
        print(get_machine_hwid())
    else:
        run_gui()
