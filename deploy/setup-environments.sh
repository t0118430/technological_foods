#!/bin/bash
# Quick setup script for dev and prod environments on Pi

set -e

PROJECT_ROOT="/opt/agritech/technological_foods"
PI_IP=$(hostname -I | awk '{print $1}')

echo "=========================================="
echo "🥧 AgriTech Environment Setup"
echo "=========================================="
echo "📍 Pi IP: $PI_IP"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Don't run this as root! Run as ubuntu user."
    exit 1
fi

# Create directory structure
echo "📁 Creating directory structure..."
cd "$PROJECT_ROOT"
mkdir -p envs/dev/data/{influxdb-dev,grafana-dev}
mkdir -p envs/prod/data/{influxdb-prod,grafana-prod}
mkdir -p backups/{dev,prod}
mkdir -p logs/{dev,prod}

# Generate secure passwords
DEV_INFLUX_TOKEN=$(openssl rand -hex 32)
PROD_INFLUX_TOKEN=$(openssl rand -hex 32)
DEV_API_KEY=$(openssl rand -hex 16)
PROD_API_KEY=$(openssl rand -hex 16)

echo "🔐 Generated secure tokens"

# Create dev .env
cat > envs/dev/.env <<EOF
# Development Environment - AgriTech Hydroponics
ENVIRONMENT=development
PI_IP=$PI_IP

# API Configuration
API_PORT=3001
API_KEY=$DEV_API_KEY
LOG_LEVEL=DEBUG

# InfluxDB Configuration
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=$DEV_INFLUX_TOKEN
INFLUXDB_ORG=agritech-dev
INFLUXDB_BUCKET=hydroponics-dev

# Notification Configuration
NTFY_TOPIC=techfoods-dev

# Data Retention (Development - shorter retention)
DATA_RETENTION_DAYS=30

# Feature Flags
ENABLE_DEBUG=true
ENABLE_METRICS=true
EOF

# Create prod .env
cat > envs/prod/.env <<EOF
# Production Environment - AgriTech Hydroponics
ENVIRONMENT=production
PI_IP=$PI_IP

# API Configuration
API_PORT=3002
API_KEY=$PROD_API_KEY
LOG_LEVEL=INFO

# InfluxDB Configuration
INFLUXDB_URL=http://localhost:8087
INFLUXDB_TOKEN=$PROD_INFLUX_TOKEN
INFLUXDB_ORG=agritech-prod
INFLUXDB_BUCKET=hydroponics-prod

# Notification Configuration
NTFY_TOPIC=techfoods

# Data Retention (Production - longer retention)
DATA_RETENTION_DAYS=365

# Feature Flags
ENABLE_DEBUG=false
ENABLE_METRICS=true
EOF

# Secure the files
chmod 600 envs/dev/.env envs/prod/.env
echo "✅ Environment files created"

# Create dev docker-compose
cat > envs/dev/docker-compose.yml <<EOF
version: '3.8'

services:
  influxdb-dev:
    image: influxdb:2.7
    container_name: agritech-influxdb-dev
    ports:
      - "8086:8086"
    volumes:
      - ./data/influxdb-dev:/var/lib/influxdb2
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: admin
      DOCKER_INFLUXDB_INIT_PASSWORD: devadmin123
      DOCKER_INFLUXDB_INIT_ORG: agritech-dev
      DOCKER_INFLUXDB_INIT_BUCKET: hydroponics-dev
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: $DEV_INFLUX_TOKEN
    restart: unless-stopped
    networks:
      - agritech-dev

  grafana-dev:
    image: grafana/grafana:latest
    container_name: agritech-grafana-dev
    ports:
      - "3000:3000"
    volumes:
      - ./data/grafana-dev:/var/lib/grafana
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: devadmin123
      GF_INSTALL_PLUGINS: grafana-clock-panel
      GF_SERVER_ROOT_URL: http://$PI_IP:3000
    restart: unless-stopped
    networks:
      - agritech-dev

networks:
  agritech-dev:
    driver: bridge
EOF

# Create prod docker-compose
cat > envs/prod/docker-compose.yml <<EOF
version: '3.8'

services:
  influxdb-prod:
    image: influxdb:2.7
    container_name: agritech-influxdb-prod
    ports:
      - "8087:8086"
    volumes:
      - ./data/influxdb-prod:/var/lib/influxdb2
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: admin
      DOCKER_INFLUXDB_INIT_PASSWORD: $(openssl rand -base64 16)
      DOCKER_INFLUXDB_INIT_ORG: agritech-prod
      DOCKER_INFLUXDB_INIT_BUCKET: hydroponics-prod
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: $PROD_INFLUX_TOKEN
    restart: unless-stopped
    networks:
      - agritech-prod

  grafana-prod:
    image: grafana/grafana:latest
    container_name: agritech-grafana-prod
    ports:
      - "3001:3000"
    volumes:
      - ./data/grafana-prod:/var/lib/grafana
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: $(openssl rand -base64 16)
      GF_INSTALL_PLUGINS: grafana-clock-panel
      GF_SERVER_ROOT_URL: http://$PI_IP:3001
    restart: unless-stopped
    networks:
      - agritech-prod

networks:
  agritech-prod:
    driver: bridge
EOF

echo "✅ Docker Compose files created"

# Create environment info file
cat > envs/ENVIRONMENT_INFO.md <<EOF
# 🌍 Environment Configuration

Generated on: $(date)
Pi IP Address: $PI_IP

## 🧪 Development Environment

**Ports:**
- API: 3001
- InfluxDB: 8086
- Grafana: 3000

**Access URLs:**
- API: http://$PI_IP:3001
- InfluxDB: http://$PI_IP:8086
- Grafana: http://$PI_IP:3000

**Credentials:**
- Grafana: admin / devadmin123
- InfluxDB: admin / devadmin123

**API Key:** $DEV_API_KEY

**Purpose:** Testing, development, experimentation

---

## 🚀 Production Environment

**Ports:**
- API: 3002
- InfluxDB: 8087
- Grafana: 3001

**Access URLs:**
- API: http://$PI_IP:3002
- InfluxDB: http://$PI_IP:8087
- Grafana: http://$PI_IP:3001

**Credentials:** (Check docker-compose.yml - auto-generated secure passwords)

**API Key:** $PROD_API_KEY

**Purpose:** Live production data

---

## 🔧 Management Commands

### Start Environment
\`\`\`bash
cd $PROJECT_ROOT/envs/dev
docker-compose up -d

cd $PROJECT_ROOT/envs/prod
docker-compose up -d
\`\`\`

### Stop Environment
\`\`\`bash
cd $PROJECT_ROOT/envs/dev
docker-compose down

cd $PROJECT_ROOT/envs/prod
docker-compose down
\`\`\`

### View Logs
\`\`\`bash
cd $PROJECT_ROOT/envs/dev
docker-compose logs -f

cd $PROJECT_ROOT/envs/prod
docker-compose logs -f
\`\`\`

### Deploy Latest Code
\`\`\`bash
$PROJECT_ROOT/deploy/deploy-env.sh dev
$PROJECT_ROOT/deploy/deploy-env.sh prod
\`\`\`
EOF

echo "✅ Documentation created: envs/ENVIRONMENT_INFO.md"

# Make deploy script executable
chmod +x "$PROJECT_ROOT/deploy/deploy-env.sh"

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Start development environment:"
echo "   cd $PROJECT_ROOT/envs/dev"
echo "   docker-compose up -d"
echo ""
echo "2. Start production environment:"
echo "   cd $PROJECT_ROOT/envs/prod"
echo "   docker-compose up -d"
echo ""
echo "3. Check status:"
echo "   docker ps"
echo ""
echo "4. View environment info:"
echo "   cat $PROJECT_ROOT/envs/ENVIRONMENT_INFO.md"
echo ""
echo "🌐 Access your services:"
echo ""
echo "   Development:"
echo "   - Grafana:  http://$PI_IP:3000 (admin/devadmin123)"
echo "   - InfluxDB: http://$PI_IP:8086"
echo "   - API:      http://$PI_IP:3001"
echo ""
echo "   Production:"
echo "   - Grafana:  http://$PI_IP:3001 (check docker-compose.yml for password)"
echo "   - InfluxDB: http://$PI_IP:8087"
echo "   - API:      http://$PI_IP:3002"
echo ""
echo "🔐 IMPORTANT: Save these API keys securely!"
echo "   Dev API Key:  $DEV_API_KEY"
echo "   Prod API Key: $PROD_API_KEY"
echo ""
