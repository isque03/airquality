#!/usr/bin/env bash
set -euo pipefail

echo "Creating virtual environment..."

python3 -m venv .venv

echo "Activating..."

source .venv/bin/activate

echo "Upgrading pip..."

python -m pip install --upgrade pip setuptools wheel

echo "Installing requirements..."

if [[ -f requirements.txt ]]; then
    pip install -r requirements.txt
else
    cat > requirements.txt <<EOF
httpx
rich
pydantic
python-dotenv
tenacity
EOF

    pip install -r requirements.txt
fi

echo
echo "Done."
echo
echo "Activate with:"
echo "source .venv/bin/activate"