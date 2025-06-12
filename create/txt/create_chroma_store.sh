#!/bin/bash
# Script to create a distributable Chroma vector store
# This allows sharing the vector store with other developers

set -e  # Exit on error

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_DIR="$SCRIPT_DIR/output/chroma_db"
TARGET_DIR="$PROJECT_ROOT/backend/targets/chroma_db"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${YELLOW}Error: Source Chroma database not found at $SOURCE_DIR${NC}"
    echo -e "Please run 'make store' first to create the Chroma database."
    exit 1
fi

# Prepare target directory
echo -e "${GREEN}Creating distributable Chroma database...${NC}"
if [ -d "$TARGET_DIR" ]; then
    echo -e "${YELLOW}Removing existing reference database...${NC}"
    rm -rf "$TARGET_DIR"
fi

# Create parent directory if it doesn't exist
mkdir -p "$(dirname "$TARGET_DIR")"

# Copy the database
echo -e "${GREEN}Copying Chroma database to $TARGET_DIR...${NC}"
cp -r "$SOURCE_DIR" "$TARGET_DIR"

# Create a README file
cat > "$TARGET_DIR/README.md" << EOF
# Reference Chroma Vector Database

This is a reference Chroma vector database for distribution purposes.
It was created on $(date) and is tracked with Git LFS.

## Usage

To use this database:

1. Make sure you have Git LFS installed and initialized
2. Pull this directory with Git LFS
3. Copy it to the correct location:

```bash
# The target directory is determined by the CHROMA_PERSIST_DIRECTORY environment variable in config/.env
```

Or use the provided script:

```bash
./create/use_chroma_store.sh
```
EOF

echo -e "${GREEN}Creating usage script...${NC}"
cat > "$SCRIPT_DIR/use_chroma_store.sh" << EOF
#!/bin/bash
# Script to use the Chroma vector store

set -e  # Exit on error

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="\$(cd "\$SCRIPT_DIR/.." && pwd)"
# Source directory is always in backend/targets
SOURCE_DIR="\$PROJECT_ROOT/backend/targets/chroma_db"

# Target directory from environment variable
if [ -f "\$PROJECT_ROOT/config/.env" ]; then
    source "\$PROJECT_ROOT/config/.env"
fi

# Use environment variable or default to the location in .env
TARGET_DIR="\$PROJECT_ROOT/\${CHROMA_PERSIST_DIRECTORY:-backend/targets/chroma_db}"

# Check if source directory exists
if [ ! -d "\$SOURCE_DIR" ]; then
    echo "Error: Reference Chroma database not found at \$SOURCE_DIR"
    echo "Please make sure you have pulled it with Git LFS."
    exit 1
fi

# Prepare target directory
echo "Setting up Chroma database..."
if [ -d "\$TARGET_DIR" ]; then
    echo "Removing existing database..."
    rm -rf "\$TARGET_DIR"
fi

# Create parent directory if it doesn't exist
mkdir -p "\$(dirname "\$TARGET_DIR")"

# Copy the database
echo "Copying reference Chroma database to \$TARGET_DIR..."
cp -r "\$SOURCE_DIR" "\$TARGET_DIR"

echo "Done! The reference Chroma database is now ready to use."
EOF

chmod +x "$SCRIPT_DIR/use_chroma_store.sh"

echo -e "${GREEN}Chroma vector store created successfully!${NC}"
echo -e "Location: ${YELLOW}$TARGET_DIR${NC}"
echo -e "\nTo distribute this database:"
echo -e "1. Commit it to Git (it will be tracked by Git LFS)"
echo -e "2. Push to your repository"
echo -e "\nOther developers can use it with:"
echo -e "${YELLOW}./create/use_chroma_store.sh${NC}"
