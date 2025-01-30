confirm() {
    local -r prompt="$1"
    local choice

    while true; do
        read -r -p "$prompt (y/n): " choice

        case "$choice" in
        y | yes | Y | Yes)
            return 0 # Return 0 for success (true)
            ;;
        n | no | N | No)
            return 1 # Return 1 for failure (false)
            ;;
        *)
            echo "Invalid input. Please enter 'y' or 'n'."
            ;;
        esac
    done
}

# Check for uv
uv --version
if [ $? != 0 ]; then
    if confirm "Would you like to install uv?"; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    else
        echo "Operation canceled."
        exit 1
    fi
else
    echo "Found uv."
fi

if [ -d ./.venv ]; then
    echo "Found .venv/"
else
    echo ".venv/ not found."
    if confirm "Would you like to create it?"; then
        uv venv
    else
        echo "Operation canceled."
        exit 1
    fi
fi

source .venv/bin/activate
echo "Virtual environment activated."

if confirm "Install requirements?"; then
    echo "Installing requirements..."
    uv pip install -r requirements.txt
else
    echo "Operation canceled."
    exit 1
fi

echo "Run 'source .venv/bin/activate' in your shell"
