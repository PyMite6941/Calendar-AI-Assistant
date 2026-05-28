echo "Do you want to install Ollama models? Y/n"
read $choice
OS=$(uname -s)
if [ $choice = "Y" ] || [ $choice = "y" ]; then
    ollama pull llama3.1:8b
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
python run.py