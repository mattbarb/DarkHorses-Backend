#!/bin/bash

# Notion MCP Setup Script
# This script sets up Notion MCP integration with Claude Desktop

set -e

echo "🔧 Setting up Notion MCP..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Claude Desktop config path
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# Check if Claude Desktop config exists
if [ ! -f "$CLAUDE_CONFIG" ]; then
    echo -e "${RED}Error: Claude Desktop config not found at $CLAUDE_CONFIG${NC}"
    exit 1
fi

# Check if notion-mcp-server is installed globally
if ! npm list -g notion-mcp-server &> /dev/null; then
    echo -e "${YELLOW}Installing Notion MCP server...${NC}"
    npm install -g notion-mcp-server --force
else
    echo -e "${GREEN}✓ Notion MCP packages already installed${NC}"
fi

# Prompt for Notion API token if not provided
if [ -z "$NOTION_API_TOKEN" ]; then
    echo -e "${YELLOW}Please enter your Notion API token:${NC}"
    echo "(Get it from: https://www.notion.so/my-integrations)"
    read -s NOTION_API_TOKEN
    echo
fi

if [ -z "$NOTION_API_TOKEN" ]; then
    echo -e "${RED}Error: Notion API token is required${NC}"
    exit 1
fi

# Get the path to the MCP server
MCP_SERVER_PATH=$(npm root -g)/notion-mcp-server/build/index.js

if [ ! -f "$MCP_SERVER_PATH" ]; then
    echo -e "${RED}Error: Notion MCP server not found at $MCP_SERVER_PATH${NC}"
    exit 1
fi

# Backup existing config
cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
echo -e "${GREEN}✓ Backed up existing config${NC}"

# Update config using Python to properly handle JSON
python3 << EOF
import json
import sys

config_path = "$CLAUDE_CONFIG"
token = "$NOTION_API_TOKEN"
server_path = "$MCP_SERVER_PATH"

try:
    with open(config_path, 'r') as f:
        config = json.load(f)

    if 'mcpServers' not in config:
        config['mcpServers'] = {}

    config['mcpServers']['notion'] = {
        "command": "node",
        "args": [server_path],
        "env": {
            "NOTION_API_TOKEN": token
        }
    }

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print("${GREEN}✓ Successfully added Notion MCP to Claude Desktop config${NC}")
    sys.exit(0)
except Exception as e:
    print(f"${RED}Error updating config: {e}${NC}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Notion MCP setup complete!${NC}"
    echo -e "${YELLOW}Please restart Claude Desktop to activate the integration.${NC}"
else
    echo -e "${RED}Setup failed. Restoring backup...${NC}"
    cp "$CLAUDE_CONFIG.backup."* "$CLAUDE_CONFIG"
    exit 1
fi
