"""
Module: mac_packager.py
Bộ đóng gói phân phối bài giảng bảo mật LockSlide cho người dùng MacBook (macOS)
- Tạo cấu trúc thư mục phân phối chuẩn macOS
- Sinh file Mo_[Tên_Bài].command với quyền thực thi (chmod +x)
- Sinh file hướng dẫn mở bài HUONG_DAN_MO_BAI.txt
- Tự động nén thành file .zip độc lập, bảo lưu quyền thực thi Unix (0755) cho macOS
"""

import os
import sys
import shutil
import zipfile

def create_mac_runner_script(presentation_filename: str) -> str:
    """
    Tạo script .command trên macOS để học viên nhấp đúp là mở bài giảng ngay lập tức.
    Tương thích tối đa với macOS 14 (Sonoma) và macOS 15 (Sequoia):
    - Tự động gỡ cờ cách ly Apple Gatekeeper (xattr -cr)
    - Tự động nhận diện Python 3 và cài đặt thư viện cryptography nếu máy Mac chưa có
    """
    return f"""#!/bin/bash
# ==============================================================================
# LOCKSLIDE STUDIO // TRÌNH MỞ BÀI GIẢNG BẢO MẬT TRÊN MACBOOK (macOS 14 & 15)
# Tự động ghim mã máy lần đầu (TOFU) - Cho phép Chỉnh sửa & Lưu (Cmd+S)
# ==============================================================================
DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )"
cd "$DIR"

echo "================================================================"
echo "   LOCKSLIDE SECURE PRESENTATION - MACBOOK RUNNER"
echo "  Hỗ trợ tối ưu macOS Sonoma (14) & macOS Sequoia (15)"
echo "================================================================"

# 1. Gỡ bỏ thuộc tính cách ly Gatekeeper (com.apple.quarantine) trên macOS 14 & 15
xattr -cr "$DIR" 2>/dev/null || true

# 2. Tìm kiếm Python 3 trên hệ thống macOS
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif [ -f "/opt/homebrew/bin/python3" ]; then
    PYTHON_BIN="/opt/homebrew/bin/python3"
elif [ -f "/usr/local/bin/python3" ]; then
    PYTHON_BIN="/usr/local/bin/python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[LỖI] Không tìm thấy Python 3 trên máy Mac này."
    osascript -e 'display alert "Thiếu Môi Trường Python" message "Để mở bài giảng bảo mật trên MacBook, vui lòng cài đặt Python 3 từ python.org hoặc Homebrew." as critical'
    exit 1
fi

# 3. Đảm bảo thư viện bảo mật cryptography đã sẵn sàng
if ! "$PYTHON_BIN" -c "import cryptography" &>/dev/null; then
    echo "[THÔNG BÁO] Đang thiết lập thư viện mã hóa bảo mật lần đầu..."
    "$PYTHON_BIN" -m pip install cryptography --user 2>/dev/null || "$PYTHON_BIN" -m pip install cryptography --break-system-packages 2>/dev/null || true
fi

# 4. Khởi chạy trình mở bài giảng bảo mật
"$PYTHON_BIN" editor_player_mac.py "{presentation_filename}"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "[THÔNG BÁO] Trình mở bài giảng đã kết thúc (Mã: $EXIT_CODE)."
    read -p "Nhấn phím Enter để đóng cửa sổ này..."
fi
"""


def package_for_mac(
    output_dir: str,
    base_name: str,
    payload_bytes: bytes,
    app_root_dir: str = None,
    create_zip: bool = True
) -> dict:
    """
    Đóng gói gói học liệu hoàn chỉnh cho MacBook:
    - [Tên]_PROTECTED.encppt
    - Mo_[Tên].command
    - editor_player_mac.py, crypto_engine_mac.py, ribbon_policy_mac.py, client_hwid_tool_mac.py
    - LAY_MA_MAY_MAC.command
    - HUONG_DAN_MO_BAI.txt
    - File .zip bảo lưu quyền thực thi macOS (POSIX 0755)
    """
    if app_root_dir is None:
        app_root_dir = os.path.dirname(os.path.abspath(__file__))

    os.makedirs(output_dir, exist_ok=True)

    enc_filename = f"{base_name}_PROTECTED.encppt"
    enc_path = os.path.join(output_dir, enc_filename)
    with open(enc_path, "wb") as f:
        f.write(payload_bytes)

    # Sinh file Mo_...command
    cmd_filename = f"Mo_{base_name}.command"
    cmd_path = os.path.join(output_dir, cmd_filename)
    cmd_content = create_mac_runner_script(enc_filename)
    with open(cmd_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(cmd_content)

    # Cấp quyền thực thi nếu chạy trên macOS/Linux
    if sys.platform != "win32":
        try:
            os.chmod(cmd_path, 0o755)
        except Exception:
            pass

    # Copy các module runtime cần thiết
    modules = ["editor_player_mac.py", "crypto_engine_mac.py", "ribbon_policy_mac.py", "client_hwid_tool_mac.py"]
    for m in modules:
        src = os.path.join(app_root_dir, m)
        if os.path.exists(src):
            dst = os.path.join(output_dir, m)
            shutil.copy2(src, dst)

    # Tạo file LAY_MA_MAY.command đi kèm trong thư mục
    hwid_cmd = os.path.join(output_dir, "LAY_MA_MAY_MAC.command")
    hwid_script = """#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
python3 client_hwid_tool_mac.py || python client_hwid_tool_mac.py
"""
    with open(hwid_cmd, "w", encoding="utf-8", newline="\n") as f:
        f.write(hwid_script)

    if sys.platform != "win32":
        try:
            os.chmod(hwid_cmd, 0o755)
        except Exception:
            pass

    # Tạo file hướng dẫn cho khách hàng MacBook
    readme_text = f"""================================================================================
       HƯỚNG DẪN MỞ & SỬ DỤNG BÀI GIẢNG BẢO MẬT TRÊN MACBOOK: {base_name}
================================================================================

1. CÁCH MỞ BÀI GIẢNG TRÊN MACBOOK:
   - Nhấp đúp vào file "Mo_{base_name}.command" để khởi chạy.
   - Nếu macOS hỏi quyền mở file lần đầu: Nhấp chuột phải (hoặc giữ phím Control và click)
     vào file "Mo_{base_name}.command" -> Chọn "Open" (Mở) -> Bấm "Open".

2. QUY ĐỊNH BẢN QUYỀN THIẾT BỊ (TOFU AUTO-LOCK):
   - Bài giảng sẽ TỰ ĐỘNG KHÓA VÀ GHIM CỐ ĐỊNH VÀO MÁY MAC NÀY ngay lần mở đầu tiên.
   - Nếu copy chuyển sang máy Mac hoặc PC khác, bài giảng sẽ KHÔNG THỂ MỞ ĐƯỢC!

3. QUYỀN CHỈNH SỬA & BẢO VỆ:
   - Bạn có thể gõ sửa nội dung, dán hình ảnh/văn bản và bấm Lưu (Cmd+S) bình thường.
   - Mọi thay đổi khi lưu sẽ tự động được mã hóa an toàn vào bài giảng.
   - Chức năng Save As và Copy bị chặn để bảo vệ bản quyền tài liệu.
================================================================================
"""
    readme_path = os.path.join(output_dir, "HUONG_DAN_MO_BAI.txt")
    with open(readme_path, "w", encoding="utf-8") as f_rm:
        f_rm.write(readme_text)

    zip_path = None
    if create_zip:
        zip_filename = f"{base_name}.zip"
        zip_path = os.path.join(os.path.dirname(output_dir), zip_filename)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            folder_prefix = f"{base_name}/"
            # Thư mục gốc
            z_dir = zipfile.ZipInfo(folder_prefix)
            z_dir.create_system = 3  # Unix
            z_dir.external_attr = (0o40755) << 16  # drwxr-xr-x
            zf.writestr(z_dir, "")

            for root, _, files in os.walk(output_dir):
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, output_dir).replace("\\", "/")
                    arcname = folder_prefix + rel_p
                    z_info = zipfile.ZipInfo.from_file(full_p, arcname)
                    z_info.create_system = 3  # Unix
                    if file.endswith((".command", ".sh")):
                        z_info.external_attr = (0o100755) << 16  # -rwxr-xr-x (executable)
                    else:
                        z_info.external_attr = (0o100644) << 16  # -rw-r--r--
                    with open(full_p, "rb") as fp:
                        zf.writestr(z_info, fp.read())

        # Đồng thời tạo file {base_name}_MacOS_Package.zip để tương thích hoàn toàn
        pkg_zip_path = os.path.join(os.path.dirname(output_dir), f"{base_name}_MacOS_Package.zip")
        try:
            shutil.copy2(zip_path, pkg_zip_path)
        except Exception:
            pass

    return {
        "enc_path": enc_path,
        "cmd_path": cmd_path,
        "zip_path": zip_path,
        "output_dir": output_dir
    }
