#!/bin/bash

# Prompt Studio - Update Script
# This script pulls the latest Docker image and restarts the container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

IMAGE="ghcr.io/pilvicontactcenter/prompt-studio:latest"
COMPOSE_FILE="docker-compose.prod.yml"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   🎙️  Prompt Studio - Update Script${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}Error: $COMPOSE_FILE not found!${NC}"
    echo -e "${YELLOW}Make sure you're running this script from the prompt-studio directory.${NC}"
    exit 1
fi

# Step 1: Pull the latest image
echo -e "${YELLOW}📥 Pulling latest image...${NC}"
docker pull $IMAGE
echo -e "${GREEN}✓ Image pulled successfully${NC}"
echo ""

# Step 2: Stop and remove the current container
echo -e "${YELLOW}🔄 Restarting container...${NC}"
docker-compose -f $COMPOSE_FILE down
docker-compose -f $COMPOSE_FILE up -d
echo -e "${GREEN}✓ Container restarted${NC}"
echo ""

# Step 3: Wait for health check
echo -e "${YELLOW}⏳ Waiting for health check (30s)...${NC}"
sleep 5

# Check container status
if docker-compose -f $COMPOSE_FILE ps | grep -q "healthy\|Up"; then
    echo -e "${GREEN}✓ Container is running${NC}"
else
    echo -e "${YELLOW}⚠ Container may still be starting...${NC}"
fi
echo ""

# Step 4: Show container logs (last 10 lines)
echo -e "${BLUE}📋 Recent logs:${NC}"
echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
docker-compose -f $COMPOSE_FILE logs --tail=10
echo -e "${BLUE}────────────────────────────────────────────────────${NC}"
echo ""

# Step 5: Cleanup old images
echo -e "${YELLOW}🧹 Cleaning up old images...${NC}"
docker image prune -f > /dev/null 2>&1
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}   ✅ Update complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "Run ${BLUE}docker-compose -f $COMPOSE_FILE logs -f${NC} to follow logs"
