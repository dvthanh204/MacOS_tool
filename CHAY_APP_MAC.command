#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
xattr -cr "$DIR" 2>/dev/null || true

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
    osascript -e 'display alert "Thiếu Python 3" message "Để chạy LockSlide Studio macOS, vui lòng cài đặt Python 3 từ python.org hoặc Homebrew." as critical'
    exit 1
fi

"$PYTHON_BIN" app_mac.py
