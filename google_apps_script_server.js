/**
 * ==============================================================================
 * LOCKSLIDE STUDIO - MÁY CHỦ BẢN QUYỀN GOOGLE SHEETS CHO MACBOOK & WINDOWS (MIỄN PHÍ 100%)
 * ==============================================================================
 * HƯỚNG DẪN TRIỂN KHAI NHANH (CHỈ MẤT 1 PHÚT):
 * 
 * Bước 1: Mở trình duyệt trên máy Mac/PC, truy cập https://sheets.new để tạo một trang tính Google mới.
 * Bước 2: Vào menu "Tiện ích mở rộng" (Extensions) -> Chọn "Apps Script".
 * Bước 3: Xóa hết code cũ trong Apps Script, dán toàn bộ nội dung file này vào.
 * Bước 4: Nhấn nút "Triển khai" (Deploy) ở góc trên bên phải -> Chọn "Tùy chọn triển khai mới" (New deployment).
 *         - Loại: Chọn "Ứng dụng web" (Web app).
 *         - Mô tả: LockSlide Server
 *         - Thực thi dưới dạng (Execute as): "Tôi" (Me).
 *         - Ai có quyền truy cập (Who has access): "Bất kỳ ai" (Anyone).
 * Bước 5: Nhấn "Triển khai" (Deploy) -> Cấp quyền cho Script nếu Google hỏi -> Copy đường dẫn URL 
 *         (Có dạng: https://script.google.com/macros/s/AKfycb.../exec).
 * Bước 6: Dán link URL này vào ô "MÁY CHỦ BẢN QUYỀN (URL)" trên phần mềm LockSlide Studio macOS.
 * 
 * KẾT QUẢ:
 * - Mỗi bài giảng chỉ kích hoạt được ĐÚNG 1 LẦN DUY NHẤT trên 1 máy MacBook.
 * - Khách hàng có gửi file zip chưa giải nén cho người khác thì người khác mở lên cũng bị CHẶN 100%!
 * - Khách mở bài nào là tự động ghi nhận tên bài, mã máy và thời gian vào Google Sheet của bạn.
 * ==============================================================================
 */

function doGet(e) {
  return handleRequest(e);
}

function doPost(e) {
  return handleRequest(e);
}

function handleRequest(e) {
  var lock = LockService.getScriptLock();
  // Chờ tối đa 10 giây để tránh xung đột khi nhiều máy mở cùng lúc
  try {
    lock.waitLock(10000);
  } catch (ex) {
    return jsonResponse({ status: "ERROR", message: "Hệ thống đang bận, vui lòng thử lại sau vài giây." });
  }

  try {
    var p = e.parameter || {};
    var action = (p.action || "activate").trim().toLowerCase();
    var license_id = (p.license_id || "").trim().toUpperCase();
    var hwid = (p.hwid || "").trim().toUpperCase();
    var title = (p.title || "Bài giảng PowerPoint").trim();

    if (!license_id || !hwid) {
      return jsonResponse({ status: "ERROR", message: "Thiếu mã License hoặc mã máy HWID." });
    }

    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = sheet.getDataRange().getValues();

    // Khởi tạo tiêu đề cột nếu sheet còn trống
    if (data.length === 0 || data[0][0] !== "MÃ LICENSE") {
      sheet.clear();
      sheet.appendRow([
        "MÃ LICENSE",
        "TÊN BÀI GIẢNG",
        "MÃ MÁY ĐÃ GHIM (HWID)",
        "TRẠNG THÁI",
        "NGÀY KÍCH HOẠT",
        "LẦN TRUY CẬP CUỐI"
      ]);
      sheet.getRange(1, 1, 1, 6).setFontWeight("bold").setBackground("#0F172A").setFontColor("#38BDF8");
      sheet.setFrozenRows(1);
      data = sheet.getDataRange().getValues();
    }

    var rowIndex = -1;
    for (var i = 1; i < data.length; i++) {
      if (String(data[i][0]).trim().toUpperCase() === license_id) {
        rowIndex = i + 1; // Hàng thực tế trên Google Sheet (1-based)
        break;
      }
    }

    var nowStr = Utilities.formatDate(new Date(), "GMT+7", "yyyy-MM-dd HH:mm:ss");

    // XỬ LÝ KÍCH HOẠT BẢN QUYỀN (1 LẦN DUY NHẤT)
    if (rowIndex === -1) {
      // 1. Lần đầu tiên bài giảng này được mở trên toàn cầu:
      // Ghim cứng vĩnh viễn vào mã máy này!
      sheet.appendRow([license_id, title, hwid, "ACTIVATED", nowStr, nowStr]);
      return jsonResponse({
        status: "SUCCESS",
        message: "Kích hoạt bản quyền thành công!",
        bound_hwid: hwid
      });
    } else {
      // 2. Bài giảng này đã từng có máy mở trước đó:
      var rowData = data[rowIndex - 1];
      var boundHwid = String(rowData[2] || "").trim().toUpperCase();
      var currentStatus = String(rowData[3] || "").trim().toUpperCase();

      // Cập nhật thời gian truy cập gần nhất
      sheet.getRange(rowIndex, 6).setValue(nowStr);

      // Nếu bạn đổi trạng thái trên Sheet thành "REVOKED" hoặc "LOCKED" để khóa từ xa:
      if (currentStatus === "REVOKED" || currentStatus === "LOCKED") {
        return jsonResponse({
          status: "REJECTED",
          message: "Bản quyền bài giảng này đã bị thu hồi hoặc tạm khóa!",
          bound_hwid: boundHwid
        });
      }

      if (!boundHwid || boundHwid === "CHỜ MỞ") {
        // Chưa có mã máy ghim -> Ghim máy hiện tại
        sheet.getRange(rowIndex, 3).setValue(hwid);
        sheet.getRange(rowIndex, 4).setValue("ACTIVATED");
        sheet.getRange(rowIndex, 5).setValue(nowStr);
        return jsonResponse({
          status: "SUCCESS",
          message: "Kích hoạt bản quyền thành công!",
          bound_hwid: hwid
        });
      } else if (boundHwid === hwid) {
        // Đúng là máy tính đã kích hoạt bài này trước đó
        return jsonResponse({
          status: "SUCCESS",
          message: "Bản quyền hợp lệ!",
          bound_hwid: hwid
        });
      } else {
        // Mã máy KHÁC với máy đã kích hoạt trước đó -> CHẶN TUYỆT ĐỐI!
        return jsonResponse({
          status: "REJECTED",
          message: "Lượt mở của bài giảng này đã được sử dụng hết trên một máy MacBook khác!\nMỗi bài giảng chỉ mở được trên đúng 1 máy tính duy nhất.",
          bound_hwid: boundHwid
        });
      }
    }
  } catch (err) {
    return jsonResponse({ status: "ERROR", message: "Lỗi xử lý server: " + String(err) });
  } finally {
    lock.releaseLock();
  }
}

function jsonResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
