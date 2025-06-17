#!/bin/bash

# Automated Kali Assistant Setup Script
echo "=== Kali Assistant Setup ==="

# 1. Install/Update Ollama
echo "[1/5] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# 2. Configure Ollama Service
echo "[2/5] Configuring Ollama service..."
sudo tee /etc/systemd/system/ollama.service > /dev/null <<EOF
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=$USER
Group=$USER
Restart=always
RestartSec=3
Environment="PATH=/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=default.target
EOF

# 3. Start Ollama
echo "[3/5] Starting Ollama..."
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl restart ollama

# 4. Pull DeepSeek Model
echo "[4/5] Downloading AI model (this may take a while)..."
ollama pull deepseek-coder

# 5. Install Assistant
echo "[5/5] Setting up Kali Assistant..."
cat > kali_assistant.py <<'EOL'
"""
Kali Linux Conversational Assistant
Automated Setup Version
"""
# [Previous full python code would go here]
EOL

# Install dependencies
pip install requests

echo "=== Setup Complete ==="
echo "To start the assistant: python3 kali_assistant.py"
echo "If you get API errors, wait 30 seconds for Ollama to fully start"
