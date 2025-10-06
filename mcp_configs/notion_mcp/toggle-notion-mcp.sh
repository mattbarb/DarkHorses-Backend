#!/bin/bash

# Toggle Notion MCP On/Off
# This script enables or disables Notion MCP in Claude Desktop config

set -e

CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ ! -f "$CLAUDE_CONFIG" ]; then
    echo -e "${RED}Error: Claude Desktop config not found${NC}"
    exit 1
fi

# Backup config
cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"

# Check current status and toggle
python3 << 'EOF'
import json
import sys

config_path = r"$CLAUDE_CONFIG"

with open(config_path, 'r') as f:
    config = json.load(f)

if 'mcpServers' not in config:
    config['mcpServers'] = {}

# Check if notion exists and is enabled
if 'notion' in config['mcpServers']:
    # Check if it's disabled (moved to _disabled_notion)
    if '_disabled_notion' in config['mcpServers']:
        # Already disabled, re-enable it
        config['mcpServers']['notion'] = config['mcpServers']['_disabled_notion']
        del config['mcpServers']['_disabled_notion']
        print("${GREEN}✓ Notion MCP enabled${NC}")
    else:
        # Disable it
        config['mcpServers']['_disabled_notion'] = config['mcpServers']['notion']
        del config['mcpServers']['notion']
        print("${YELLOW}✓ Notion MCP disabled${NC}")
elif '_disabled_notion' in config['mcpServers']:
    # Re-enable
    config['mcpServers']['notion'] = config['mcpServers']['_disabled_notion']
    del config['mcpServers']['_disabled_notion']
    print("${GREEN}✓ Notion MCP enabled${NC}")
else:
    print("${RED}Error: Notion MCP not found in config. Run setup-notion-mcp.sh first.${NC}")
    sys.exit(1)

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("${YELLOW}Please restart Claude Desktop for changes to take effect.${NC}")
EOF
