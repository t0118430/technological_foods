#!/bin/bash
# Deploy to specific environment (dev or prod)

set -e

ENV="${1:-dev}"  # Default to dev if not specified
PROJECT_ROOT="/opt/agritech/technological_foods"

echo "=========================================="
echo "🚀 Deploying to $ENV environment"
echo "=========================================="

if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
    echo "❌ Invalid environment: $ENV"
    echo "Usage: ./deploy-env.sh [dev|prod]"
    exit 1
fi

# Navigate to project
cd "$PROJECT_ROOT"

# Pull latest code
echo "📥 Pulling latest code..."
git fetch origin
git checkout master
git pull origin master

# Load environment variables
echo "🔧 Loading $ENV environment..."
export $(cat "envs/$ENV/.env" | grep -v '^#' | xargs)

# Stop services
echo "⏹️  Stopping $ENV services..."
cd "envs/$ENV"
docker-compose down

# Backup database
echo "💾 Creating backup..."
BACKUP_DIR="$PROJECT_ROOT/backups/$ENV"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="${ENV}_backup_${TIMESTAMP}"

if [ -d "data/influxdb-${ENV}" ]; then
    tar -czf "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" "data/influxdb-${ENV}"
    echo "✅ Backup created: $BACKUP_NAME.tar.gz"
fi

# Pull latest Docker images
echo "🐋 Pulling Docker images..."
docker-compose pull

# Start services
echo "🚀 Starting $ENV services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Health check
echo "🏥 Running health check..."
if curl -s "http://localhost:${API_PORT}/health" > /dev/null 2>&1; then
    echo "✅ $ENV API is healthy"
else
    echo "⚠️  $ENV API health check failed (may still be starting)"
fi

# Check Docker containers
echo ""
echo "📊 Container status:"
docker ps | grep "agritech.*${ENV}"

echo ""
echo "=========================================="
echo "✅ Deployment to $ENV complete!"
echo "=========================================="
echo ""
echo "🌐 Environment URLs:"
if [ "$ENV" = "dev" ]; then
    echo "   API:      http://localhost:3001"
    echo "   InfluxDB: http://localhost:8086"
    echo "   Grafana:  http://localhost:3000"
else
    echo "   API:      http://localhost:3002"
    echo "   InfluxDB: http://localhost:8087"
    echo "   Grafana:  http://localhost:3001"
fi
echo ""
echo "📝 View logs:"
echo "   cd $PROJECT_ROOT/envs/$ENV"
echo "   docker-compose logs -f"
