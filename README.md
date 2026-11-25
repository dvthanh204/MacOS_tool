# LOCKSLIDE STUDIO MACOS v2.5 - HỆ THỐNG MÃ HÓA & BẢO MẬT POWERPOINT DÀNH CHO MACBOOK

Hệ thống được phát triển chuyên biệt dành cho người dùng **MacBook (macOS)**, chuyển giao và kế thừa 100% chuẩn logic bảo mật của **hash_win**:
**MỞ BÀI GIẢNG TRÊN MACBOOK VẪN CHỈNH SỬA VÀ LƯU ĐƯỢC (EDITABLE MODE + AUTO-SAVE SYNC)**, đồng thời **CẤM TUYỆT ĐỐI SAVE AS LƯU FILE MỚI** và **CHẶN SAO CHÉP (COPY/CUT) DỮ LIỆU RA NGOÀI**.

---

## 🌟 CÁC TÍNH NĂNG BẢO MẬT CỐT LÕI (CHUẨN HASH_WIN TRÊN MACOS)

1. **CHO PHÉP CHỈNH SỬA TRỰC TIẾP TRÊN POWERPOINT FOR MAC (EDITABLE MODE):**
   - Bài giảng mở trực tiếp trong ứng dụng **Microsoft PowerPoint for Mac** ở chế độ thiết kế (slide design mode) đầy đủ.
   - Học viên/Giáo viên có thể gõ nội dung, đổi font chữ, thêm bớt slide, chèn hình ảnh, dán dữ liệu (`Cmd+V`).

2. **LƯU ĐƯỢC NỘI DUNG ĐÃ SỬA (REAL-TIME AUTO-SAVE SYNC):**
   - Khi người dùng nhấn `Cmd+S` hoặc bấm nút Lưu trong PowerPoint for Mac, luồng chạy ngầm bắt thay đổi ngay lập tức.
   - Tự động mã hóa lại (re-encrypt) toàn bộ nội dung mới với thuật toán **AES-256-GCM** và ghi đè đồng bộ thẳng vào file mã hóa gốc (`.encppt`).
   - Khi đóng bài giảng, tiến trình On-Exit Sync quét lần cuối để đảm bảo mọi thao tác lưu trước khi thoát đều được ghi nhận 100%.
   - Lần sau mở lại: Toàn bộ nội dung đã chỉnh sửa vẫn được bảo lưu trọn vẹn!

3. **CẤM TUYỆT ĐỐI SAVE AS LƯU FILE MỚI (BẢO VỆ CHỐNG LỘ LỌT FILE NGUỒN):**
   - **OpenXML Fluent UI Ribbon Policy:** Tiêm cấu hình vô hiệu hóa các lệnh `FileSaveAs`, `FileSaveCopyAs`, `FileSaveACopy`, `SaveACopy`, `ExportMenu`, `FilePrint` trong cả `customUI14.xml` và `customUI.xml`.
   - **Backstage Policy:** Ẩn hoàn toàn các thẻ nhạy cảm trong menu File: `TabSave`, `TabSaveACopy`, `TabShare`, `TabExport`, `TabPrint`.
   - **Tối ưu hóa macOS:** Tự động loại bỏ các định nghĩa nhúng font Windows (`embeddedFontLst`) gây cảnh báo khó chịu khi mở trên PowerPoint for Mac.

4. **CHẶN SAO CHÉP (COPY/CUT) DỮ LIỆU:**
   - Vô hiệu hóa lệnh `Copy`, `Cut`, `SlideCopy` trên thanh công cụ Ribbon và context menu chuột phải.
   - Cho phép `Cmd+V` (Dán) để người dùng đưa dữ liệu của họ vào bài giảng.

5. **TỰ ĐỘNG GHIM THIẾT BỊ LẦN ĐẦU (FIRST-RUN AUTO-LOCK / TOFU TRÊN MAC):**
   - Định danh phần cứng duy nhất của MacBook dựa trên: **Apple Hardware UUID** + **Mac Serial Number** (`IOPlatformUUID` + `IOPlatformSerialNumber`).
   - Tác giả không cần hỏi trước mã máy của khách hàng.
   - Khi khách mở file lần đầu trên Mac, hệ thống tự động bắt mã máy Mac và khóa cứng bài giảng vào máy tính đó.
   - **Chống chuyển tiếp 100%**: Nếu khách đem gửi file cho người khác -> Máy Mac thứ 2 sẽ bị từ chối truy cập ngay lập tức!
   - Hỗ trợ lưu cache kích hoạt cục bộ (`~/Library/Application Support/LockSlideSecure/`) cho phép mở Offline sau lần đầu đã ghim.

6. **THU HỒI TỪ XA TỨC THÌ (REMOTE KILL-SWITCH):**
   - Quản trị viên chỉ cần nhấn **"Thu hồi"** trên giao diện Studio hoặc Web Dashboard bất cứ lúc nào.
   - Bài giảng trên máy Mac của khách lập tức bị khóa.
   - Quản trị viên có thể nhấn **"Khôi phục"** hoặc **"Đổi máy"** (cho phép khách chuyển sang máy Mac mới).

---

## 📁 CẤU TRÚC THƯ MỤC DỰ ÁN HASH_MAC

```
hash_mac/
├── app_mac.py                   # Giao diện chính Studio mã hóa cho Mac (PyQt5 Dark Tech Theme)
├── crypto_engine_mac.py         # Động cơ mã hóa AES-256-GCM, định danh Mac HWID, Auto-Lock & Re-encrypt
├── ribbon_policy_mac.py         # Bộ tiêm cấu hình Ribbon XML & dọn dẹp font tối ưu cho PowerPoint for Mac
├── editor_player_mac.py         # Trình mở bài giảng bảo mật trên MacBook, Auto-Save Sync & dọn dẹp RAM/Disk
├── license_server.py            # Máy chủ Flask + SQLite quản lý ghim máy Mac, thu hồi từ xa & Web Dashboard
├── client_hwid_tool_mac.py      # Công cụ 1-click cho người dùng Mac lấy mã máy HWID
├── mac_packager.py              # Đóng gói xuất trọn bộ cho Mac: .encppt, Mo_...command, .zip bảo lưu quyền POSIX
├── test_suite_mac.py            # Bộ kiểm thử tự động 10/10 bài test kiểm chứng toàn diện tính năng trên Mac
├── CHAY_APP_MAC.bat             # Khởi động Studio trên Windows để xuất file cho Mac
├── CHAY_APP_MAC.command         # Khởi động Studio trực tiếp trên macOS
├── LAY_MA_MAY_MAC.command       # Script lấy mã máy Mac cho khách hàng
├── MO_FILE_MA_HOA_MAC.command   # Script mở file mã hóa trên Mac
└── result_mac/                  # Thư mục xuất bài giảng phân phối cho MacBook
```

---

## 🚀 HƯỚNG DẪN SỬ DỤNG

### 1. Khởi động Giao diện Studio:
- **Nếu chạy trên Windows để xuất file cho khách Mac:** Chạy `CHAY_APP_MAC.bat` (hoặc `python app_mac.py`).
- **Nếu chạy trực tiếp trên máy Mac:** Nhấp đúp `CHAY_APP_MAC.command` (hoặc `python3 app_mac.py`).

### 2. Mã hóa bài giảng:
1. Kéo thả file PowerPoint (`.pptx`, `.ppt`) vào khung nhận diện màu xanh neon.
2. Kiểm tra các tùy chọn an toàn:
   - ✅ **Cho phép mở sửa bài giảng (Edit)**: Đang bật
   - ✅ **Khóa 'Save As' chống lưu file mới**: Đang bật
   - ✅ **Khóa Copy / Sao chép nội dung**: Đang bật
   - ✅ **Đóng gói .zip bảo lưu quyền macOS**: Đang bật
3. Bấm nút **"BẮT ĐẦU MÃ HÓA & ĐÓNG GÓI MACBOOK"**.

### 3. Gửi cho khách hàng MacBook:
- Mở thư mục `result_mac/`.
- Lấy thư mục bài giảng hoặc file `[Tên_Bài]_MacOS_Package.zip` gửi cho khách hàng.

### 4. Mở bài giảng trên MacBook (Phía khách hàng):
- Khách hàng giải nén file zip trên máy Mac.
- Nhấp đúp file `Mo_[Tên_Bài].command` để mở bài giảng.
- Bài giảng xuất hiện trong Microsoft PowerPoint for Mac ở chế độ thiết kế đầy đủ.
- Khách hàng có thể sửa đổi nội dung và bấm `Cmd+S` để lưu lại.
- Khi đóng bài giảng, toàn bộ thay đổi đã được tự động mã hóa đồng bộ an toàn vào file gốc.
