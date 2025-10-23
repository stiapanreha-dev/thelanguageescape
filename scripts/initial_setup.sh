#!/bin/bash
# Initial setup script for VPS
# Run once: bash scripts/initial_setup.sh

set -e

echo "========================================"
echo "Initial Setup: The Language Escape Bot"
echo "========================================"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_DIR="/root/language_escape_bot"
REPO_URL="git@github.com:stiapanreha-dev/thelanguageescape.git"

echo ""
echo "📋 Configuration:"
echo "   Project Dir: $PROJECT_DIR"
echo "   Repository: $REPO_URL"

echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Update system
echo ""
echo "🔄 Updating system packages..."
apt-get update
apt-get upgrade -y

# Install required packages
echo ""
echo "📦 Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    postgresql \
    postgresql-contrib \
    nginx \
    ffmpeg \
    sshpass

echo -e "${GREEN}✅ System packages installed${NC}"

# Setup PostgreSQL
echo ""
echo "🗄️  Setting up PostgreSQL..."
if [ -f "scripts/setup_postgres.sh" ]; then
    bash scripts/setup_postgres.sh
else
    echo -e "${YELLOW}⚠️  PostgreSQL setup script not found. Run manually later.${NC}"
fi

# Create project directory
echo ""
echo "📁 Creating project directory..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Clone repository (if not exists)
if [ ! -d ".git" ]; then
    echo ""
    echo "📥 Cloning repository..."

    # Setup SSH key for GitHub (if needed)
    if [ ! -f ~/.ssh/id_rsa ]; then
        echo ""
        echo "🔑 Generating SSH key for GitHub..."
        ssh-keygen -t rsa -b 4096 -C "bot@the-language-escape.ru" -f ~/.ssh/id_rsa -N ""

        echo ""
        echo -e "${YELLOW}⚠️  ADD THIS PUBLIC KEY TO GITHUB:${NC}"
        echo "   https://github.com/settings/keys"
        echo ""
        cat ~/.ssh/id_rsa.pub
        echo ""
        read -p "Press Enter after adding the key to GitHub..."
    fi

    git clone "$REPO_URL" .
else
    echo -e "${YELLOW}⚠️  Repository already exists. Pulling latest...${NC}"
    git pull origin main
fi

echo -e "${GREEN}✅ Repository ready${NC}"

# Create virtual environment
echo ""
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✅ Python dependencies installed${NC}"

# Setup .env file
echo ""
echo "⚙️  Setting up .env file..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env file with your credentials:${NC}"
    echo "   nano .env"
    echo ""
    echo "   Required:"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - ADMIN_TELEGRAM_ID"
    echo "   - YOOKASSA_PROVIDER_TOKEN"
fi

# Copy materials
echo ""
echo "📚 Setting up materials directory..."
if [ -d "docs/Материалы" ]; then
    echo "Materials found in docs/Материалы"
    echo "Running materials parser..."
    python3 scripts/parse_materials.py
    echo -e "${GREEN}✅ Materials parsed${NC}"
else
    echo -e "${YELLOW}⚠️  Materials not found. Upload to docs/Материалы${NC}"
fi

# Initialize database
echo ""
echo "🗄️  Initializing database..."
python3 -c "
import asyncio
import sys
sys.path.append('.')
from bot.database.database import init_db
asyncio.run(init_db())
" || echo -e "${RED}❌ Database initialization failed${NC}"

# Create systemd service
echo ""
echo "🔧 Creating systemd service..."
cat > /etc/systemd/system/language-escape-bot.service <<EOF
[Unit]
Description=The Language Escape Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/bot/main.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=language-escape-bot

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload
systemctl enable language-escape-bot

echo -e "${GREEN}✅ Systemd service created${NC}"

# Summary
echo ""
echo "========================================"
echo "Initial Setup Complete!"
echo "========================================"
echo ""
echo -e "${GREEN}✅ What's done:${NC}"
echo "   • System packages installed"
echo "   • PostgreSQL configured"
echo "   • Repository cloned"
echo "   • Python environment ready"
echo "   • Database initialized"
echo "   • Systemd service created"
echo ""
echo -e "${YELLOW}⚠️  Next steps:${NC}"
echo "   1. Edit .env file:"
echo "      cd $PROJECT_DIR"
echo "      nano .env"
echo ""
echo "   2. Add your credentials:"
echo "      - TELEGRAM_BOT_TOKEN (from @BotFather)"
echo "      - ADMIN_TELEGRAM_ID (from @userinfobot)"
echo "      - YOOKASSA_PROVIDER_TOKEN (from YooKassa)"
echo ""
echo "   3. Upload materials to docs/Материалы/ (if needed)"
echo ""
echo "   4. Start the bot:"
echo "      systemctl start language-escape-bot"
echo "      systemctl status language-escape-bot"
echo ""
echo "   5. View logs:"
echo "      journalctl -u language-escape-bot -f"
echo ""
echo "========================================"
