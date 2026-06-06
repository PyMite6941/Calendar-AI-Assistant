if [ ollama list | grep -q "llama3.1" && echo "Model pulled" ]; then
    echo "Do you wish to use Llama 3.1? Y/n"
    read $choice
    if [ $choice = "Y" ] || [ $choice = "y" ]; then
        echo "Using Ollama for local LLMs."
        python backend/tools/config_editing.py --set local_model True
    else
        echo "Then hook up API keys in the settings menu."
        python backend/tools/config_editing.py --set local_model False
    fi
else
    echo "Do you want to install Ollama model Llama 3.1? Y/n"
    read $choice
    OS=$(uname -s)
    if [ $choice = "Y" ] || [ $choice = "y" ]; then
        ollama pull llama3.1:8b
        python backend/tools/config_editing.py --set local_model True
    else
        echo "Then hook up API keys in the settings menu."
        python backend/tools/config_editing.py --set local_model False
    fi
fi
python -m venv .venv
if [ $OS = "Linux" ] || [ $OS = "Darwin" ]; then
    source .venv/Scripts/activate.bat
else if [ $OS = "Windows" ]; then
    .venv/Scripts/Activate.ps1
else
    echo "Unsupported operating system. Please activate the virtual environment manually."
    exit 1
fi
echo "What is your name?"
read $name
echo "Setup complete! Activating run.py ..."
python run.py
