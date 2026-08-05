#!/bin/bash
# install.sh
echo "[+] Installing Discord Stealth Reporter"
pkg update -y
pkg install python -y
pip install aiohttp
chmod +x main.py
echo "[+] Done. Run: python main.py"
