#!/bin/bash
# Agent Memory DMG Packager for macOS
# Creates a distributable DMG installer

set -e

APP_NAME="Agent Memory"
APP_DIR="${APP_NAME}.app"
DMG_NAME="${APP_NAME}.dmg"
VERSION="0.1.0"
VOL_NAME="${APP_NAME} ${VERSION}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Agent Memory DMG Packager ===${NC}"

# Check for required tools
check_tool() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}Error: $1 is required but not installed.${NC}"
        exit 1
    fi
}

echo -e "${YELLOW}Checking dependencies...${NC}"
check_tool "python3"
check_tool "uv"
check_tool "hdiutil"

# Create temp directory
WORK_DIR=$(mktemp -d)
echo "Working in: $WORK_DIR"
cd "$WORK_DIR"

# Create app structure
echo -e "${YELLOW}Creating app structure...${NC}"
mkdir -p "${APP_DIR}/Contents/MacOS"
mkdir -p "${APP_DIR}/Contents/Resources"

# Create launcher script
cat > "${APP_DIR}/Contents/MacOS/agent-memory" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../Resources"

# Check for Python
if ! command -v python3 &> /dev/null; then
    osascript -e 'display dialog "Python 3 is required but not found." buttons "OK" with icon stop'
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    uv sync
fi

# Start SurrealDB (file-backed with RocksDB)
echo "Starting SurrealDB..."
surreal start --user root --pass root --allow-funcs --allow-net --allow-experimental rocksdb://./memory.db &
SURREAL_PID=$!

# Wait for SurrealDB
sleep 3

# Load schema
echo "Loading schema..."
source venv/bin/activate
uv run load.py

# Open Surrealist
open http://localhost:3000

# Run agent
echo "Starting agent..."
uv run agent.py

# Cleanup on exit
trap "kill $SURREAL_PID 2>/dev/null" EXIT
EOF

chmod +x "${APP_DIR}/Contents/MacOS/agent-memory"

# Copy resources (exclude git, dist, etc)
echo -e "${YELLOW}Copying resources...${NC}"
rsync -av --exclude='.git' --exclude='dist' --exclude='*.egg-info' /workspace/Agent-Memory/ "${APP_DIR}/Contents/Resources/"

# Create Info.plist
cat > "${APP_DIR}/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>agent-memory</string>
    <key>CFBundleIconFile</key>
    <string>app.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.agentmemory.app</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2026. All rights reserved.</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.developer-tools</string>
</dict>
</plist>
EOF

# Create entitlements
cat > "${APP_DIR}/Contents/Resources/agent-memory.entitlements" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.app-sandbox</key>
    <false/>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
</dict>
</plist>
EOF

# Create DMG
echo -e "${YELLOW}Creating DMG...${NC}"
hdiutil create -volname "$VOL_NAME" -srcfolder "$APP_DIR" -ov -format UDZO "$DMG_NAME"

# Copy to output
OUTPUT_DIR="/workspace/Agent-Memory/dist"
mkdir -p "$OUTPUT_DIR"
cp "$DMG_NAME" "$OUTPUT_DIR/"

echo -e "${GREEN}DMG created: $OUTPUT_DIR/$DMG_NAME${NC}"

# Cleanup
rm -rf "$WORK_DIR"

echo -e "${GREEN}Done!${NC}"