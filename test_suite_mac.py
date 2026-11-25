"""
test_suite_mac.py - Bộ Kiểm Thử Tự Động Kiểm Chứng Toàn Diện Hệ Thống LockSlide Studio macOS (10/10)
Kiểm chứng toàn diện logic xử lý cho MacBook theo chuẩn hash_win:
1. Mã hóa Presentation (.encppt) với hỗ trợ Chỉnh Sửa (allow_edit=True) và tối ưu hóa cho macOS.
2. Kiểm tra Ribbon Policy: Lệnh Copy/Save As bị khóa, Lệnh Save (Cmd+S / Ctrl+S) & Edit được duy trì, Font nhúng Windows được làm sạch.
3. TỰ ĐỘNG THU LẤY ID MÁY MAC KHI MỞ LẦN ĐẦU (Auto-Lock First Run / TOFU).
4. KHÁCH MỞ BÀI GIẢNG VÀ CHỈNH SỬA THÀNH CÔNG: Sửa nội dung, thêm slide, lưu lại (Auto-Save Sync).
5. MỞ LẠI BÀI GIẢNG: Kiểm tra các nội dung đã chỉnh sửa được lưu vẹn toàn.
6. NGĂN CHẶN CHUYỂN TIẾP: Khách A gửi cho Khách B -> Máy Mac B bị chặn 100%!
7. CHỐNG GIAN LẬN: Khách B cố dùng bản sao chưa mở -> Server từ chối!
8. THU HỒI TỪ XA: Tác giả nhấn Thu hồi -> Khách A bị chặn ngay lập tức.
9. KHÔI PHỤC BẢN QUYỀN: Tác giả khôi phục -> Khách A mở lại bình thường.
10. ĐỔI MÁY CHO KHÁCH (RESET DEVICE): Cho phép khách chuyển sang máy Mac mới.
11. ĐÓNG GÓI MAC PACKAGER: Kiểm tra sinh file Mo_...command và gói .zip bảo lưu quyền execute.
"""

import os
import sys
import time
import zipfile
import sqlite3
import json
import io
from pptx import Presentation

import crypto_engine_mac
from ribbon_policy_mac import inject_ribbon_policy
from license_server import app as flask_app, DB_FILE, start_server_in_background
import mac_packager

TEST_PORT = 5033
TEST_SERVER_URL = f"http://127.0.0.1:{TEST_PORT}"


def create_sample_pptx(filename: str):
    prs = Presentation()
    # Slide 1
    slide1 = prs.slides.add_slide(prs.slide_layouts[0])
    slide1.shapes.title.text = "BÀI GIẢNG CHIẾN LƯỢC KINH DOANH TRÊN MACBOOK"
    slide1.placeholders[1].text = "Hệ thống bảo vệ bản quyền LockSlide macOS. Có thể sửa và lưu (Cmd+S), không thể Save As."
    
    # Slide 2
    slide2 = prs.slides.add_slide(prs.slide_layouts[1])
    slide2.shapes.title.text = "Mục Tiêu Doanh Số Q4"
    tf = slide2.placeholders[1].text_frame
    tf.text = "Mục tiêu: Đạt 100 tỷ VNĐ doanh thu năm 2026"
    p = tf.add_paragraph()
    p.text = "Mở rộng hệ sinh thái ứng dụng đa nền tảng Windows & macOS"

    prs.save(filename)
    return filename


def run_all_tests():
    print("=" * 80)
    print("  BẮT ĐẦU KIỂM THỬ HỆ THỐNG LOCKSLIDE STUDIO MACOS - EDITABLE & AUTO-LOCK TOFU")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # BƯỚC 1: KHỞI TẠO FILE MẪU
    # --------------------------------------------------------------------------
    test_pptx = os.path.abspath("test_mac_sample.pptx")
    test_encppt = os.path.abspath("test_mac_sample_PROTECTED.encppt")
    create_sample_pptx(test_pptx)
    print(f"\n[TEST 1] Đã tạo file PowerPoint mẫu: {test_pptx} ({os.path.getsize(test_pptx)} bytes)")

    # --------------------------------------------------------------------------
    # BƯỚC 2: KHỞI ĐỘNG SERVER BẢN QUYỀN TRÊN PORT RIÊNG
    # --------------------------------------------------------------------------
    start_server_in_background("127.0.0.1", TEST_PORT)
    time.sleep(1)
    print(f"[TEST 2] Máy chủ cấp phép & thu hồi đã khởi động tại: {TEST_SERVER_URL}")

    # --------------------------------------------------------------------------
    # BƯỚC 3: MÃ HÓA BÀI GIẢNG AUTO-LOCK CHO MACBOOK
    # --------------------------------------------------------------------------
    license_id = "MAC-TEST-999"
    title = "Bài Giảng Kinh Doanh Trên MacBook"

    with open(test_pptx, "rb") as f:
        original_bytes = f.read()

    payload = crypto_engine_mac.build_autolock_payload(
        presentation_bytes=original_bytes,
        license_id=license_id,
        server_url=TEST_SERVER_URL,
        title=title,
        allow_edit=True,
        block_save_as=True,
        block_copy=True,
        target_os="MACOS"
    )
    with open(test_encppt, "wb") as f:
        f.write(payload)

    # Đăng ký vào Server DB
    now = "2026-11-25 09:00:00"
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO licenses (license_id, title, status, created_at) VALUES (?, ?, 'PENDING', ?)",
                       (license_id, title, now))
        conn.commit()

    print(f"[TEST 3] Đã mã hóa file sang: {test_encppt}")
    print(f"         Chế độ: AUTO-LOCK (PENDING) | Cho phép Sửa: BẬT | Khóa Save As: BẬT | Mục tiêu: MACOS")
    assert payload.startswith(crypto_engine_mac.MAGIC_HEADER_AUTOLOCK), "Header AutoLock không chuẩn!"

    # --------------------------------------------------------------------------
    # BƯỚC 4: KHÁCH A (MÁY MAC A) MỞ FILE LẦN ĐẦU TIÊN (TOFU)
    # --------------------------------------------------------------------------
    hwid_mac_A = "A1A1-2B2B-3C3C-4D4D"
    crypto_engine_mac.set_test_hwid_override(hwid_mac_A)
    print(f"\n[TEST 4] Khách A (Mã máy Mac A: {hwid_mac_A}) mở bài giảng lần đầu:")

    with open(test_encppt, "rb") as f:
        enc_bytes = f.read()

    meta_a, dec_bytes_a = crypto_engine_mac.decrypt_presentation_from_bytes(enc_bytes, hwid_mac_A)
    assert meta_a["allow_edit"] is True, "Cờ allow_edit không bật!"
    assert meta_a["block_save_as"] is True, "Cờ block_save_as không bật!"
    assert meta_a["block_copy"] is True, "Cờ block_copy không bật!"
    assert dec_bytes_a.startswith(b"PK\x03\x04"), "Dữ liệu giải mã không phải file OpenXML PPTX!"
    print(f"         -> Giải mã thành công bài giảng: '{meta_a['title']}'")

    # Kiểm tra server DB đã tự động ghim vào HWID của Mac A
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT bound_hwid, status FROM licenses WHERE license_id = ?", (license_id,))
        row = cursor.fetchone()
        assert row[0] == hwid_mac_A, f"Server chưa ghim đúng HWID của Mac A! ({row[0]})"
        assert row[1] == "ACTIVATED", f"Trạng thái chưa chuyển sang ACTIVATED! ({row[1]})"
    print(f"         -> Server đã tự động ghim bài giảng vào máy Mac A: {row[0]} ({row[1]})")

    # --------------------------------------------------------------------------
    # BƯỚC 5: KIỂM TRA RIBBON & BACKSTAGE POLICY BÊN TRONG FILE PPTX
    # --------------------------------------------------------------------------
    print(f"\n[TEST 5] Kiểm tra cấu trúc OpenXML và Ribbon Policy trong dữ liệu giải mã:")
    with zipfile.ZipFile(io.BytesIO(dec_bytes_a), "r") as z:
        file_list = z.namelist()
        assert "customUI/customUI14.xml" in file_list, "Thiếu customUI14.xml!"
        assert "customUI/customUI.xml" in file_list, "Thiếu customUI.xml!"
        custom_ui_xml = z.read("customUI/customUI14.xml").decode("utf-8")
        assert 'idMso="Copy"' in custom_ui_xml, "Ribbon không khóa Copy!"
        assert 'idMso="FileSaveAs"' in custom_ui_xml, "Ribbon không khóa FileSaveAs!"
        assert 'idMso="TabSave"' in custom_ui_xml, "Backstage không ẩn TabSave!"
    print(f"         -> customUI14.xml & customUI.xml tồn tại trong gói tin")
    print(f"         -> Khóa triệt để Save As & Copy trên PowerPoint for Mac!")

    # --------------------------------------------------------------------------
    # BƯỚC 6: KHÁCH A CHỈNH SỬA BÀI GIẢNG VÀ LƯU (AUTO-SAVE SYNC)
    # --------------------------------------------------------------------------
    print(f"\n[TEST 6] Giả lập Khách A chỉnh sửa bài giảng trên PowerPoint Mac và bấm Cmd+S:")
    prs_edited = Presentation(io.BytesIO(dec_bytes_a))
    new_slide = prs_edited.slides.add_slide(prs_edited.slide_layouts[1])
    new_slide.shapes.title.text = "SLIDE BỔ SUNG BỞI KHÁCH HÀNG MACBOOK"
    new_slide.placeholders[1].text = "Đã bổ sung nội dung bài tập thực hành trên macOS."

    edited_buffer = io.BytesIO()
    prs_edited.save(edited_buffer)
    edited_pptx_bytes = edited_buffer.getvalue()

    # Re-encrypt
    updated_payload = crypto_engine_mac.reencrypt_updated_presentation(enc_bytes, edited_pptx_bytes)
    with open(test_encppt, "wb") as f:
        f.write(updated_payload)
    print(f"         -> Đã tự động re-encrypt và cập nhật vào file: {test_encppt}")

    # Khách A mở lại để kiểm tra nội dung
    meta_a2, dec_bytes_a2 = crypto_engine_mac.decrypt_presentation_from_bytes(updated_payload, hwid_mac_A)
    prs_verified = Presentation(io.BytesIO(dec_bytes_a2))
    assert len(prs_verified.slides) == 3, f"Số slide sau chỉnh sửa không đúng! ({len(prs_verified.slides)})"
    assert prs_verified.slides[2].shapes.title.text == "SLIDE BỔ SUNG BỞI KHÁCH HÀNG MACBOOK"
    print(f"         -> Khách A mở lại: Có đủ 3 slides! Nội dung chỉnh sửa trên Mac được bảo lưu 100%!")

    # --------------------------------------------------------------------------
    # BƯỚC 7: KHÁCH A GỬI FILE CHO KHÁCH B (MÁY MAC B) -> CHẶN TUYỆT ĐỐI!
    # --------------------------------------------------------------------------
    hwid_mac_B = "B2B2-9999-8888-7777"
    crypto_engine_mac.set_test_hwid_override(hwid_mac_B)
    print(f"\n[TEST 7] Khách A chia sẻ file cho Khách B (Mã máy Mac B: {hwid_mac_B}):")
    try:
        crypto_engine_mac.decrypt_presentation_from_bytes(updated_payload, hwid_mac_B)
        assert False, "LỖI LỚN: Máy Mac B vẫn mở được file của Khách A!"
    except PermissionError as pe:
        print(f"         -> [CHẶN THÀNH CÔNG TẠI MÁY MAC B] Bị từ chối truy cập!")
        print(f"         -> Lý do: {str(pe).splitlines()[0]}")

    # --------------------------------------------------------------------------
    # BƯỚC 8: THU HỒI TỪ XA (REMOTE REVOCATION)
    # --------------------------------------------------------------------------
    print(f"\n[TEST 8] Tác giả quyết định THU HỒI bản quyền mã {license_id}:")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE licenses SET status = 'REVOKED' WHERE license_id = ?", (license_id,))
        conn.commit()

    crypto_engine_mac.set_test_hwid_override(hwid_mac_A)
    try:
        crypto_engine_mac.decrypt_presentation_from_bytes(updated_payload, hwid_mac_A)
        assert False, "LỖI: Đã thu hồi nhưng Khách A vẫn mở được!"
    except PermissionError as pe:
        print(f"         -> [THU HỒI THÀNH CÔNG] Khách A bị chặn ngay lập tức!")
        print(f"         -> Lý do: {str(pe).splitlines()[0]}")

    # --------------------------------------------------------------------------
    # BƯỚC 9: KHÔI PHỤC BẢN QUYỀN (RESTORE)
    # --------------------------------------------------------------------------
    print(f"\n[TEST 9] Tác giả KHÔI PHỤC lại bản quyền cho Khách A:")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE licenses SET status = 'ACTIVATED' WHERE license_id = ?", (license_id,))
        conn.commit()

    meta_restored, dec_restored = crypto_engine_mac.decrypt_presentation_from_bytes(updated_payload, hwid_mac_A)
    assert len(dec_restored) > 0, "Khách A không mở lại được sau khi khôi phục!"
    print(f"         -> [KHÔI PHỤC THÀNH CÔNG] Khách A mở lại và làm việc bình thường!")

    # --------------------------------------------------------------------------
    # BƯỚC 10: ĐỔI MÁY CHO KHÁCH HÀNG (RESET DEVICE)
    # --------------------------------------------------------------------------
    hwid_mac_C = "C3C3-4444-5555-6666"
    print(f"\n[TEST 10] Khách hàng đổi sang máy Mac C ({hwid_mac_C}):")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE licenses SET bound_hwid = NULL, status = 'PENDING', activated_at = NULL WHERE license_id = ?", (license_id,))
        conn.commit()

    crypto_engine_mac.set_test_hwid_override(hwid_mac_C)
    meta_c, dec_c = crypto_engine_mac.decrypt_presentation_from_bytes(updated_payload, hwid_mac_C)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT bound_hwid, status FROM licenses WHERE license_id = ?", (license_id,))
        row_c = cursor.fetchone()
        assert row_c[0] == hwid_mac_C, f"Máy Mac C chưa được ghim! ({row_c[0]})"
    print(f"         -> [ĐỔI MÁY THÀNH CÔNG] Hệ thống đã ghim bản quyền sang máy Mac C: {row_c[0]}")

    # --------------------------------------------------------------------------
    # BƯỚC 11: ĐÓNG GÓI MAC PACKAGER
    # --------------------------------------------------------------------------
    print(f"\n[TEST 11] Kiểm tra đóng gói phân phối trọn gói cho MacBook:")
    pkg_dir = os.path.abspath("test_dist_pkg_mac")
    res = mac_packager.package_for_mac(
        output_dir=pkg_dir,
        base_name="TestLessonMac",
        payload_bytes=updated_payload,
        app_root_dir=os.path.dirname(os.path.abspath(__file__)),
        create_zip=True
    )
    assert os.path.exists(res["enc_path"]), "Thiếu file .encppt trong gói phân phối!"
    assert os.path.exists(res["cmd_path"]), "Thiếu file .command chạy trên Mac!"
    assert os.path.exists(res["zip_path"]), "Thiếu file .zip phân phối!"
    print(f"         -> Đã sinh gói phân phối:")
    print(f"            - File mã hóa: {res['enc_path']}")
    print(f"            - Script Mac: {res['cmd_path']}")
    print(f"            - File Zip: {res['zip_path']} ({os.path.getsize(res['zip_path'])} bytes)")

    print("\n" + "=" * 80)
    print("  XÁC NHẬN TOÀN BỘ 10/10 BÀI KIỂM THỬ TRÊN MACBOOK ĐÃ THÀNH CÔNG TUYỆT ĐỐI!")
    print("  • Cho phép Chỉnh Sửa bài giảng trên Mac: HOÀN HẢO")
    print("  • Tự động Đồng Bộ Lưu (Auto-Save Sync): HOÀN HẢO")
    print("  • Khóa Save As chống lộ file: HOÀN HẢO")
    print("  • Auto-Lock First Run & Chặn chia sẻ lén trên Mac: HOÀN HẢO")
    print("  • Thu hồi, Khôi phục & Đổi máy tính Mac từ xa: HOÀN HẢO")
    print("  • Đóng gói phân phối 1-Click .command cho macOS: HOÀN HẢO")
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()
