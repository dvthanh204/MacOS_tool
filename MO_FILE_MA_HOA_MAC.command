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
    echo "[LỖI] Chưa có Python 3 trên máy Mac."
    exit 1
fi

if ! "$PYTHON_BIN" -c "import cryptography" &>/dev/null; then
    echo "[THÔNG BÁO] Cài đặt thư viện mã hóa bảo mật..."
    "$PYTHON_BIN" -m pip install cryptography --user 2>/dev/null || "$PYTHON_BIN" -m pip install cryptography --break-system-packages 2>/dev/null || true
fi

"$PYTHON_BIN" editor_player_mac.py "$1"
