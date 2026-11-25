"""
Module: mac_packager.py
Bộ đóng gói phân phối bài giảng bảo mật LockSlide cho người dùng MacBook (macOS)
- Tạo cấu trúc thư mục phân phối chuẩn macOS
- Sinh file Mo_[Tên_Bài].command với quyền thực thi (chmod +x)
- Tùy chọn đóng gói ra file .zip bảo lưu toàn bộ POSIX attributes cho macOS
"""

import os
import sys
import shutil
import zipfile

def create_mac_runner_script(presentation_filename: str) -> str:
    """
    Tạo script .command trên macOS để học viên nhấp đúp là mở bài giảng ngay lập tức.
    Tự động tìm kiếm môi trường Python 3 trên máy Mac (Homebrew, Framework, System).
    """
    return f"""#!/bin/bash
# ==============================================================================
# LOCKSLIDE STUDIO // TRÌNH MỞ BÀI GIẢNG BẢO MẬT TRÊN MACBOOK
# Tự động ghim mã máy lần đầu (TOFU) - Cho phép Chỉnh sửa & Lưu (Cmd+S)
# ==============================================================================
DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )"
cd "$DIR"

echo "================================================================"
echo "   LOCKSLIDE SECURE PRESENTATION - MACBOOK RUNNER"
echo "  Đang khởi động trình mở bài giảng bảo mật..."
echo "================================================================"

# Tìm kiếm Python 3 trên hệ thống macOS
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
    osascript -e 'display alert "Thiếu Môi Trường Python" message "Để mở bài giảng bảo mật trên macOS, vui lòng cài đặt Python 3 từ python.org hoặc Homebrew." as critical'
    exit 1
fi

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
    - editor_player_mac.py, crypto_engine_mac.py, ribbon_policy_mac.py
    - LAY_MA_MAY.command
    - File .zip bảo lưu quyền thực thi macOS
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

    zip_path = None
    if create_zip:
        zip_filename = f"{base_name}_MacOS_Package.zip"
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

    return {
        "enc_path": enc_path,
        "cmd_path": cmd_path,
        "zip_path": zip_path,
        "output_dir": output_dir
    }
