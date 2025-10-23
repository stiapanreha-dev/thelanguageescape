#!/bin/bash
# Deploy The Language Escape Bot to VPS
# Run: bash scripts/deploy.sh

set -e

echo "========================================"
echo "Deploying The Language Escape Bot"
echo "========================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
PROJECT_DIR="/root/language_escape_bot"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="language-escape-bot"

echo ""
echo "📁 Setting up project directory..."

# Create project directory if doesn't exist
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo -e "${GREEN}✅ Project directory ready${NC}"

echo ""
echo "🐍 Setting up Python virtual environment..."

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠️  Virtual environment already exists${NC}"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

echo ""
echo "📦 Installing Python dependencies..."

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✅ Dependencies installed${NC}"

echo ""
echo "🗄️  Initializing database..."

# Initialize database tables
python3 bot/main.py --init-db || python3 -c "
import asyncio
import sys
sys.path.append('.')
from bot.database.database import init_db
asyncio.run(init_db())
"

echo -e "${GREEN}✅ Database initialized${NC}"

echo ""
echo "🔧 Creating systemd service..."

# Create systemd service file
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=The Language Escape Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/bot/main.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Systemd service created${NC}"

echo ""
echo "🚀 Starting bot service..."

# Reload systemd, enable and start service
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo -e "${GREEN}✅ Bot service started${NC}"

echo ""
echo "📊 Checking service status..."

# Show service status
systemctl status "$SERVICE_NAME" --no-pager || true

echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo ""
echo "📝 Useful commands:"
echo "   Status:  systemctl status $SERVICE_NAME"
echo "   Stop:    systemctl stop $SERVICE_NAME"
echo "   Start:   systemctl start $SERVICE_NAME"
echo "   Restart: systemctl restart $SERVICE_NAME"
echo "   Logs:    journalctl -u $SERVICE_NAME -f"
echo ""
echo "🔗 Bot is now running in background!"
echo "========================================"
