# LOCKSLIDE STUDIO MACOS v3.0 - HỆ THỐNG MÃ HÓA & ĐÓNG GÓI BÀI GIẢNG POWERPOINT ĐỘC LẬP CHO MACBOOK (.ZIP)

Hệ thống được phát triển chuyên biệt dành cho người dùng **MacBook (macOS Sonoma 14 & Sequoia 15)**, kế thừa và đồng bộ 100% chuẩn tính năng của **hash_win**:
- **100% NGOẠI TUYẾN HOẶC CLOUD GOOGLE SHEETS MIỄN PHÍ:** Hỗ trợ kích hoạt 1 lần duy nhất qua Google Sheets hoặc chạy hoàn toàn Offline không cần mạng.
- **MỖI BÀI GIẢNG XUẤT RA 1 FILE .ZIP ĐỘC LẬP:** Dễ dàng gửi cho khách hàng, bên trong có sẵn file chạy 1-click `.command` dành riêng cho macOS.
- **TỰ ĐỘNG GHIM BẢN QUYỀN VÀO MÁY MAC KHÁCH (AUTO-LOCK TOFU):** Khi khách mở lần đầu, bài giảng tự động khóa cứng vào mã máy Mac (IOPlatformUUID + Serial). Tự động đồng bộ ghim luôn vào file nén `.zip` gốc để chống chia sẻ.
- **CHỈNH SỬA & LƯU NỘI DUNG BÌNH THƯỜNG TRÊN POWERPOINT FOR MAC (Cmd+S):** Thoải mái sửa slide, chèn ảnh, paste text và lưu bài.
- **CẤM TUYỆT ĐỐI SAVE AS & CHẶN COPY:** Vô hiệu hóa tính năng lưu file mới và sao chép nội dung ra ngoài.

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
   - Khóa phím tắt sao chép khi làm việc trên bài giảng, ngăn ngừa sao chép nội dung giáo án ra ngoài.

5. **TỰ ĐỘNG GHIM THIẾT BỊ LẦN ĐẦU (FIRST-RUN AUTO-LOCK / TOFU):**
   - Tác giả chỉ cần mã hóa bài giảng và gửi file nén `.zip` cho khách dùng Mac, không cần hỏi trước mã máy tính của khách.
   - Khi khách nhấp đúp file `Mo_[Tên].command` lần đầu: Hệ thống tự động thu thập ID phần cứng (Hardware ID: Apple Hardware UUID + Mac Serial Number) và khóa cứng bài giảng vào máy Mac đó.
   - **Đồng bộ vào file .zip gốc:** Hệ thống tự động cập nhật bản quyền ngược lại file `.zip` gốc trên máy khách. Nếu khách gửi cả file `.zip` cho người khác thì máy thứ 2 cũng **BỊ CHẶN 100%**!

6. **MÁY CHỦ BẢN QUYỀN GOOGLE SHEETS (MIỄN PHÍ 100%):**
   - Tích hợp sẵn mẫu Google Apps Script (`google_apps_script_server.js`).
   - Tác giả chỉ cần 1 phút tạo Google Sheet và dán code để có ngay máy chủ bản quyền đám mây.
   - Quản lý tập trung mọi lượt mở: Tên bài giảng, mã máy Mac (HWID), ngày giờ kích hoạt.
   - Hỗ trợ đổi trạng thái thành `REVOKED` trên Google Sheet để **khóa bài giảng từ xa** bất cứ lúc nào!

---

## 🚀 HƯỚNG DẪN SỬ DỤNG

### 1. Khởi động Giao diện Quản trị Studio:
- **Trên MacBook:** Nhấp đúp file `CHAY_APP_MAC.command` (hoặc `CHAY_LOCKSLIDE_STUDIO_MAC.command`).
- **Trên Windows / Linux:** Chạy file `CHAY_APP_MAC.bat` hoặc lệnh `python app_mac.py`.

### 2. Thiết lập máy chủ Google Sheets (Khuyên dùng):
1. Bấm nút **"📋 Code & Hướng Dẫn Google Sheets (Miễn Phí)"** trên giao diện.
2. Bấm **"🌐 Mở Google Sheets (sheets.new)"** để tạo 1 bảng tính Google mới.
3. Vào **Tiện ích mở rộng (Extensions)** -> **Apps Script** -> Dán code đã sao chép.
4. Bấm **Triển khai (Deploy)** -> **Tùy chọn triển khai mới (New deployment)** -> Chọn **Ứng dụng web (Web app)** -> Thực thi dưới dạng **Tôi**, Ai có quyền truy cập: **Bất kỳ ai**.
5. Copy link URL dán vào ô **MÁY CHỦ BẢN QUYỀN**.

### 3. Mã hóa bài giảng:
1. Kéo thả một hoặc nhiều file PowerPoint (`.pptx`, `.pptm`, `.ppt`) vào khung nhận diện màu xanh neon.
2. Kiểm tra các tùy chọn an toàn:
   - ✅ **Cho phép sửa & lưu (Cmd+S)**: Đang bật
   - ✅ **Cấm 'Save As' & 'Export'**: Đang bật
   - ✅ **Cấm 'Copy' (Cmd+C)**: Đang bật
3. Bấm nút **"BẮT ĐẦU MÃ HÓA & ĐÓNG GÓI .ZIP"**.

### 4. Gửi cho khách hàng:
- Vào thư mục `result_mac`, lấy file nén `[Tên_Bài].zip` gửi cho học viên.
- Học viên giải nén và nhấp đúp file `Mo_[Tên_Bài].command` để mở bài giảng ngay lập tức!
- Nếu cần lấy mã máy Mac độc lập, học viên chạy file `LAY_MA_MAY_MAC.command`.

---

## 📂 CẤU TRÚC HỆ THỐNG MACBOOK

```
hash_mac/
├── app_mac.py                       # Giao diện chính LockSlide Studio macOS (PyQt5)
├── crypto_engine_mac.py             # Lõi mã hóa AES-256-GCM, Mac HWID & Auto-Lock TOFU
├── editor_player_mac.py             # Trình mở PowerPoint for Mac, Editable & Auto-Save Sync
├── mac_packager.py                  # Module đóng gói trọn gói macOS & nén .ZIP độc lập
├── ribbon_policy_mac.py             # OpenXML Fluent UI Ribbon Policy cho Office for Mac
├── client_hwid_tool_mac.py          # Tool lấy mã máy Mac độc lập (GUI + CLI)
├── google_apps_script_server.js     # Script máy chủ Google Sheets miễn phí 100%
├── config.json                      # Cấu hình URL máy chủ bản quyền
├── test_suite_mac.py                # Bộ test tự động kiểm thử toàn diện
├── CHAY_APP_MAC.command             # File 1-click khởi động Studio trên MacBook
├── CHAY_LOCKSLIDE_STUDIO_MAC.command# Shortcut 1-click tương thích tên gọi hash_win
├── LAY_MA_MAY_MAC.command           # File 1-click lấy mã máy Mac cho khách
├── MO_FILE_MA_HOA_MAC.command       # File 1-click mở file mã hóa trực tiếp
└── result_mac/                      # Thư mục chứa các file .zip xuất bản thành phẩm
```
