#!/usr/bin/env bash
set -e

OS=$(uname -s)

# ── Ollama / model selection ──────────────────────────────────────────────────

if command -v ollama >/dev/null 2>&1 && ollama list 2>/dev/null | grep -q "llama3.1"; then
    printf "Llama 3.1 is already pulled. Use it? [Y/n] "
    read choice
    if [ "$choice" = "Y" ] || [ "$choice" = "y" ] || [ -z "$choice" ]; then
        echo "Using Ollama for local LLMs."
        python backend/tools/config_editing.py --key local_model --set True
    else
        echo "Hook up API keys in the settings menu."
        python backend/tools/config_editing.py --key local_model --set False
    fi
elif command -v ollama >/dev/null 2>&1; then
    printf "Ollama found but Llama 3.1 not pulled. Pull it now? [Y/n] "
    read choice
    if [ "$choice" = "Y" ] || [ "$choice" = "y" ] || [ -z "$choice" ]; then
        ollama pull llama3.1:8b
        python backend/tools/config_editing.py --key local_model --set True
    else
        echo "Hook up API keys in the settings menu."
        python backend/tools/config_editing.py --key local_model --set False
    fi
else
    echo "Ollama not found. Hook up API keys in the settings menu."
    python backend/tools/config_editing.py --key local_model --set False
fi

# ── Virtual environment ───────────────────────────────────────────────────────

python -m venv .venv

if [ "$OS" = "Linux" ] || [ "$OS" = "Darwin" ]; then
    source .venv/bin/activate
elif echo "$OS" | grep -qE "MINGW|CYGWIN|MSYS"; then
    source .venv/Scripts/activate
else
    echo "Unsupported OS: $OS. Activate the virtual environment manually."
    exit 1
fi

# ── Install dependencies ──────────────────────────────────────────────────────

pip install -r requirements.txt -q

# ── User setup ────────────────────────────────────────────────────────────────

printf "What is your name? "
read name
if [ -n "$name" ]; then
    python backend/tools/config_editing.py --key user_name --set "$name"
fi

printf "Your timezone (IANA format, e.g. America/New_York, Asia/Bangkok) [blank to skip]: "
read timezone
if [ -n "$timezone" ]; then
    python backend/tools/config_editing.py --key timezone --set "$timezone"
fi

echo "Setup complete! Starting the app..."
python run.py
