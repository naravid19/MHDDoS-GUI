#!/bin/bash
# ==============================================================================
# MHDDoS-GUI - Advanced Installer for Linux (v1.6.4)
# ==============================================================================

# Terminal Colors
G='\033[92m'
Y='\033[93m'
R='\033[91m'
B='\033[96m'
W='\033[97m'
M='\033[95m'
X='\033[0m'
BOLD='\033[1m'

clear
echo -e "${BOLD}${M}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          MHDDoS-GUI Professional Installer               ║"
echo "║                    v1.6.4 (Linux)                        ║"
echo "╚══════════════════════════════════════════════════════════╝${X}"
echo ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 1: Pre-flight Checks
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo -e "${BOLD}${W}[*] Checking Pre-requisites...${X}"

# Check Python3
if ! command -v python3 &> /dev/null; then
    echo -e "${R}[ERROR] python3 is not installed or not in your PATH. Please install Python 3.11+.${X}"
    exit 1
fi

# Verify Python version >= 3.11
python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"
if [ $? -ne 0 ]; then
    echo -e "${R}[ERROR] Python version 3.11+ is required. Found:${X}"
    python3 --version
    exit 1
fi
echo -e "${G}[ok] Python 3.11+ detected.${X}"

# Check Git
if ! command -v git &> /dev/null; then
    echo -e "${Y}[WARNING] Git is not installed. Git dependency check might fail for PyRoxy.${X}"
else
    echo -e "${G}[ok] Git detected.${X}"
fi

# Check Python3 venv package (common issue on Ubuntu/Debian)
python3 -c "import venv" &> /dev/null
if [ $? -ne 0 ]; then
    echo -e "${R}[ERROR] Python3 'venv' module is missing. Please install it (e.g. sudo apt install python3-venv).${X}"
    exit 1
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 2: Virtual Environment Setup
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo -e "${BOLD}${W}[*] Setting up Python Virtual Environment (.venv)...${X}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo -e "${R}[ERROR] Failed to create virtual environment.${X}"
        exit 1
    fi
    echo -e "${G}[ok] Virtual environment created successfully.${X}"
else
    echo -e "${G}[ok] Existing virtual environment found.${X}"
fi

# Activate Virtual Environment
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${R}[ERROR] Failed to activate virtual environment.${X}"
    exit 1
fi
echo -e "${G}[ok] Virtual environment activated.${X}"

# Upgrade Pip
echo "[*] Upgrading pip..."
python3 -m pip install --upgrade pip &> /dev/null

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 3: Package Installations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo -e "${BOLD}${W}[*] Installing requirements from requirements.txt...${X}"
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${R}[ERROR] Failed to install standard python requirements.${X}"
    exit 1
fi
echo -e "${G}[ok] Core packages installed.${X}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 4: Local Resource Setup (Camoufox & Browser Engines)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo -e "${BOLD}${W}[*] Configuring advanced browser engines...${X}"

# Local Camoufox installation
if [ -d "resource/camoufox/pythonlib" ]; then
    echo "[*] Installing local Camoufox resource from resource/camoufox/pythonlib..."
    pip install -e "resource/camoufox/pythonlib[geoip]"
    if [ $? -ne 0 ]; then
        echo -e "${R}[ERROR] Local Camoufox installation failed.${X}"
        exit 1
    fi
    echo -e "${G}[ok] Local Camoufox package configured.${X}"
else
    echo -e "${Y}[WARNING] Local Camoufox path 'resource/camoufox/pythonlib' not found. Installing from Pip...${X}"
    pip install "camoufox[geoip]>=0.5.2"
fi

# Download Camoufox Browser binary
echo "[*] Fetching Camoufox anti-detect browser binaries..."
python3 -m camoufox fetch
if [ $? -ne 0 ]; then
    echo -e "${R}[ERROR] Failed to download Camoufox browser binaries.${X}"
    exit 1
fi
echo -e "${G}[ok] Camoufox browser binaries downloaded.${X}"

# Download Playwright Chromium binary
echo "[*] Fetching Playwright Chromium binaries..."
playwright install chromium
if [ $? -ne 0 ]; then
    echo -e "${R}[ERROR] Failed to download Playwright Chromium.${X}"
    exit 1
fi
echo -e "${G}[ok] Playwright Chromium binaries downloaded.${X}"

# Make scripts executable
chmod +x web_gui.py desktop_gui.py worker.py 2>/dev/null

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Step 5: Verification & Launch Guide
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo ""
echo -e "${BOLD}${G}╔══════════════════════════════════════════════════════════╗"
echo -e "║         INSTALLATION COMPLETED SUCCESSFULLY!             ║"
echo -e "╚══════════════════════════════════════════════════════════╝${X}"
echo ""
echo "  To launch the application:"
echo ""
echo -e "  ${BOLD}${B}1. Web Dashboard (Recommended):${X}"
echo "     python3 web_gui.py --force"
echo ""
echo -e "  ${BOLD}${B}2. Standalone Desktop GUI:${X}"
echo "     python3 desktop_gui.py"
echo ""
echo -e "  ${BOLD}${B}3. Distributed Worker Node:${X}"
echo "     python3 worker.py --master http://YOUR_MASTER_IP:8000 --token SECRET"
echo ""
echo -e "${BOLD}${Y}[Note]${X} Keep this virtual environment activated by running ${BOLD}source .venv/bin/activate${X} in your terminal before launching commands."
echo ""
