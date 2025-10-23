#!/bin/bash
# Setup PostgreSQL for The Language Escape Bot
# Run on VPS: sudo bash scripts/setup_postgres.sh

set -e

echo "========================================"
echo "PostgreSQL Setup for Language Escape Bot"
echo "========================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Database configuration
DB_NAME="language_escape"
DB_USER="bot_user"
DB_PASSWORD="bot_password_secure_2024"

echo ""
echo "📦 Installing PostgreSQL..."

# Install PostgreSQL
apt-get update
apt-get install -y postgresql postgresql-contrib

# Start PostgreSQL service
systemctl start postgresql
systemctl enable postgresql

echo -e "${GREEN}✅ PostgreSQL installed${NC}"

echo ""
echo "👤 Creating database and user..."

# Create database and user
sudo -u postgres psql <<EOF
-- Create user if not exists
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$DB_USER') THEN
      CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
   END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Connect to database and grant schema privileges
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
EOF

echo -e "${GREEN}✅ Database and user created${NC}"

echo ""
echo "🔐 Configuring PostgreSQL..."

# Allow local connections
PG_HBA_CONF="/etc/postgresql/$(ls /etc/postgresql)/main/pg_hba.conf"

# Backup original config
cp "$PG_HBA_CONF" "$PG_HBA_CONF.backup"

# Add local connection rule if not exists
if ! grep -q "host.*$DB_NAME.*$DB_USER" "$PG_HBA_CONF"; then
    echo "host    $DB_NAME    $DB_USER    127.0.0.1/32    md5" >> "$PG_HBA_CONF"
fi

# Reload PostgreSQL
systemctl reload postgresql

echo -e "${GREEN}✅ PostgreSQL configured${NC}"

echo ""
echo "✨ Testing connection..."

# Test connection
if sudo -u postgres psql -U $DB_USER -d $DB_NAME -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Connection test successful${NC}"
else
    echo -e "${RED}❌ Connection test failed${NC}"
    echo "You may need to configure authentication manually"
fi

echo ""
echo "========================================"
echo "PostgreSQL Setup Complete!"
echo "========================================"
echo ""
echo "📝 Database Credentials:"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"
echo "   Password: $DB_PASSWORD"
echo "   Host: localhost"
echo "   Port: 5432"
echo ""
echo "🔗 Connection String:"
echo "   postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
echo ""
echo "⚠️  Don't forget to add this to your .env file!"
echo "========================================"
