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

if [ -d ./.venv ]; then
    echo "Found .venv/"
else
    echo ".venv/ not found."
    if confirm "Would you like to create it?"; then
        python3 -m venv .venv
    else
        echo "Operation canceled."
        exit 1
    fi
fi

source ./.venv/bin/activate
echo "Virtual environment activated."

if confirm "Install requirements?"; then
    echo "Installing requirements..."
    pip3 install -r requirements.txt
else
    echo "Operation canceled."
    exit 1
fi

echo "Run 'source ./.venv/bin/activate' in your shell"
