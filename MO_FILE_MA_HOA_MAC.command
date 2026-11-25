#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
python3 editor_player_mac.py "$1" || python editor_player_mac.py "$1"
