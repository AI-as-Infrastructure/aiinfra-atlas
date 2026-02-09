#!/bin/bash

# Complete development environment reset script
# WARNING: This removes ALL data including corpus, configurations, and retrievers
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  COMPLETE RESET WARNING"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "This will DESTROY:"
echo "  • All virtual environments"
echo "  • All node_modules"
echo "  • Built corpus data"
echo "  • Configuration files"
echo "  • Custom retrievers"
echo "  • Test targets"
echo "  • System settings"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 TIP: Use 'make d' instead if you only want to clean the"
echo "        development environment but keep your corpus/configs"
echo ""
read -p "Are you SURE you want to continue? Type 'yes' to confirm: " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Reset cancelled."
    exit 0
fi

echo ""
echo "Starting complete reset..."

# First run the standard clean (handles processes, venv, node_modules)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Running standard development cleanup..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash "$(dirname "$0")/clean_dev.sh" --force

# Remove corpus data
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Removing corpus data..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "backend/corpus" ]; then
    echo "  Removing backend/corpus/"
    rm -rf backend/corpus
    echo "  ✅ Corpus data removed"
else
    echo "  ℹ️  No corpus data found"
fi

# Remove corpus build artifacts
if [ -d "backend/corpus_build" ]; then
    echo "  Removing backend/corpus_build/"
    rm -rf backend/corpus_build
    echo "  ✅ Corpus build directory removed"
fi

# Remove configuration files
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Removing configuration files..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Remove corpus configuration from old location
if [ -f "backend/config/corpus_active.json" ]; then
    echo "  Removing backend/config/corpus_active.json"
    rm -f backend/config/corpus_active.json
    echo "  ✅ Active corpus configuration removed (old location)"
fi

# Note: corpus_active.json in backend/corpus/ will be removed with the entire corpus directory in step 2

# Remove atlas configuration
if [ -f "backend/config/atlas_config.json" ]; then
    echo "  Removing backend/config/atlas_config.json"
    rm -f backend/config/atlas_config.json
    echo "  ✅ Atlas configuration removed"
fi

# Remove system settings (but not the template)
if [ -f "config/system_settings.json" ]; then
    echo "  Removing config/system_settings.json"
    rm -f config/system_settings.json
    echo "  ✅ System settings removed"
else
    echo "  ℹ️  No system settings found"
fi

# Remove custom retrievers and adapters (keep only base_retriever.py and utils)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4: Removing custom retrievers..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "backend/retrievers" ]; then
    # List files that will be removed
    removed_count=0
    for file in backend/retrievers/*_retriever.py backend/retrievers/*_adapter.py; do
        # Skip base_retriever.py and other utility files
        basename=$(basename "$file")
        if [[ "$basename" != "base_retriever.py" &&
              "$basename" != "retriever_config_utils.py" &&
              "$basename" != "retriever_call_model.py" &&
              "$basename" != "__init__.py" ]]; then
            if [ -f "$file" ]; then
                echo "  Removing $basename"
                rm -f "$file"
                ((removed_count++))
            fi
        fi
    done

    if [ $removed_count -gt 0 ]; then
        echo "  ✅ Removed $removed_count custom retriever(s)/adapter(s)"
    else
        echo "  ℹ️  No custom retrievers/adapters found"
    fi
else
    echo "  ℹ️  Retrievers directory not found"
fi

# Remove test targets (except templates)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5: Removing test target configurations..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "backend/targets" ]; then
    # Remove all .txt files except template files
    removed_count=0
    for file in backend/targets/*.txt; do
        basename=$(basename "$file")
        # Skip template files
        if [[ "$basename" != *"template"* && -f "$file" ]]; then
            echo "  Removing $basename"
            rm -f "$file"
            ((removed_count++))
        fi
    done

    if [ $removed_count -gt 0 ]; then
        echo "  ✅ Removed $removed_count test target(s)"
    else
        echo "  ℹ️  No custom test targets found"
    fi
else
    echo "  ℹ️  Targets directory not found"
fi

# Remove any wizard temporary files
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 6: Removing wizard temporary files..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Remove wizard build state
if [ -f "backend/.wizard_build_state.json" ]; then
    echo "  Removing wizard build state"
    rm -f backend/.wizard_build_state.json
    echo "  ✅ Wizard build state removed"
fi

# Remove any temporary corpus directories
for dir in backend/corpus_*_tmp backend/corpus_backup_*; do
    if [ -d "$dir" ]; then
        echo "  Removing $(basename "$dir")"
        rm -rf "$dir"
    fi
done

# Remove mode state file if it exists
if [ -f "backend/.system_mode" ]; then
    echo "  Removing system mode state"
    rm -f backend/.system_mode
    echo "  ✅ System mode state removed"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ COMPLETE RESET FINISHED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "The system is now in a clean state."
echo "Next steps:"
echo "  1. Run 'make b' to start the backend"
echo "  2. Run 'make f' to start the frontend"
echo "  3. Navigate to http://localhost:5173"
echo "  4. Use the wizard to configure your corpus"
echo ""
echo "This is equivalent to a first-time installation."