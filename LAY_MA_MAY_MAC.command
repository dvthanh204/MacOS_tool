#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
python3 client_hwid_tool_mac.py || python client_hwid_tool_mac.py
