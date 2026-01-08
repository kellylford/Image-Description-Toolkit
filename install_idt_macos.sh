#!/bin/bash
# Install IDT command-line tool to system PATH (macOS)

set -e

echo "========================================"
echo "Installing Image Description Toolkit"
echo "========================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
IDT_EXECUTABLE="$SCRIPT_DIR/idt/dist/idt"

# Check if idt executable exists
if [ ! -f "$IDT_EXECUTABLE" ]; then
    echo "ERROR: idt executable not found at: $IDT_EXECUTABLE"
    echo "Please build idt first by running:"
    echo "  cd idt && ./build_idt.sh"
    exit 1
fi

echo "Found IDT executable at: $IDT_EXECUTABLE"
echo ""

# Choose installation method
echo "Choose installation method:"
echo "  1) Create symlink in /usr/local/bin (requires sudo, system-wide)"
echo "  2) Create symlink in ~/bin (user-only, no sudo required)"
echo "  3) Add to PATH in ~/.zshrc (recommended, no sudo required)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "Installing to /usr/local/bin (requires sudo)..."
        sudo ln -sf "$IDT_EXECUTABLE" /usr/local/bin/idt
        echo "✅ Installed! You can now run 'idt' from anywhere."
        ;;
    2)
        echo ""
        echo "Installing to ~/bin..."
        mkdir -p ~/bin
        ln -sf "$IDT_EXECUTABLE" ~/bin/idt
        
        # Check if ~/bin is in PATH
        if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
            echo ""
            echo "⚠️  ~/bin is not in your PATH."
            echo "Add this line to your ~/.zshrc:"
            echo '    export PATH="$HOME/bin:$PATH"'
            echo ""
            echo "Then run: source ~/.zshrc"
        else
            echo "✅ Installed! You can now run 'idt' from anywhere."
        fi
        ;;
    3)
        echo ""
        echo "Adding to PATH in ~/.zshrc..."
        
        # Check if already in zshrc
        if grep -q "Image Description Toolkit" ~/.zshrc 2>/dev/null; then
            echo "⚠️  IDT PATH entry already exists in ~/.zshrc"
            echo "Updating it..."
            # Remove old entry
            sed -i.bak '/# Image Description Toolkit/d' ~/.zshrc
            sed -i.bak '/export PATH.*idt\/dist/d' ~/.zshrc
        fi
        
        # Add new entry
        echo "" >> ~/.zshrc
        echo "# Image Description Toolkit" >> ~/.zshrc
        echo "export PATH=\"$SCRIPT_DIR/idt/dist:\$PATH\"" >> ~/.zshrc
        
        echo "✅ Added to ~/.zshrc"
        echo ""
        echo "To use immediately, run:"
        echo "  source ~/.zshrc"
        echo ""
        echo "Then you can run 'idt' from anywhere."
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "Installation complete!"
echo "========================================"
echo ""
echo "Test with: idt version"
echo ""
