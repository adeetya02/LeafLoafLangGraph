#!/bin/bash
# Fix SSL certificate issues on macOS for Python

echo "Fixing SSL certificates for Python on macOS..."

# Install/update certificates
pip install --upgrade certifi

# Get Python base path
PYTHON_PATH=$(python3 -c "import sys; print(sys.base_prefix)")
echo "Python path: $PYTHON_PATH"

# Link certificates
cd "$PYTHON_PATH" || exit
./Install\ Certificates.command 2>/dev/null || echo "Certificates command not found, trying alternative..."

# Alternative: Set environment variable
export SSL_CERT_FILE=$(python3 -m certifi)
export REQUESTS_CA_BUNDLE=$(python3 -m certifi)

echo "SSL certificates fixed. You may need to restart your terminal."
echo ""
echo "Add these to your shell profile (~/.bashrc or ~/.zshrc):"
echo "export SSL_CERT_FILE=\$(python3 -m certifi)"
echo "export REQUESTS_CA_BUNDLE=\$(python3 -m certifi)"