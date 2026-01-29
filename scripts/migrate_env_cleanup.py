#!/usr/bin/env python3
"""
Environment Migration Script - Clean up obsolete environment variables

This script removes deprecated environment variables that are no longer needed
after the corpus wizard integration. It creates timestamped backups before
making any changes.

Usage:
    python scripts/migrate_env_cleanup.py [--dry-run]
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import shutil

def backup_env_file(env_path: Path) -> Path:
    """Create a timestamped backup of the environment file."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = Path('config/backups')
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_path = backup_dir / f"{env_path.stem}_{timestamp}{env_path.suffix}"
    shutil.copy(env_path, backup_path)
    return backup_path

def get_obsolete_variables():
    """Get list of environment variables that should be removed."""
    return [
        # Hansard-specific variables (removed in previous refactor)
        'HANSARD_SOURCES_ROOT',
        'HANSARD_CORPUS_ROOT',
        'HANSARD_DATA_DIR',

        # Multi-corpus variables (no longer used)
        'MULTI_CORPUS_ENABLED',
        'MULTI_CORPUS_SOURCES',
        'MULTI_CORPUS_NAMES',

        # ChromaDB variables (now in corpus config)
        'CHROMA_HOST',
        'CHROMA_PORT',
        'CHROMA_PERSIST_DIRECTORY',
        'CHROMA_COLLECTION_NAME',

        # BM25 variable (now in corpus config)
        'BM25_CORPUS',

        # Retriever module (now auto-detected)
        'RETRIEVER_MODULE',

        # Old vector store variables
        'VECTOR_STORE_PATH',
        'EMBEDDINGS_PATH',

        # Old corpus-specific variables
        'CORPUS_PATH',
        'CORPUS_TYPE',
        'CORPUS_VERSION'
    ]

def clean_env_file(env_path: Path, dry_run: bool = False) -> tuple[int, list]:
    """
    Clean obsolete variables from an environment file.

    Returns:
        Tuple of (lines_removed, removed_variables)
    """
    if not env_path.exists():
        print(f"  ⚠️  File not found: {env_path}")
        return 0, []

    obsolete = get_obsolete_variables()

    with open(env_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    removed_count = 0
    removed_vars = []

    for line in lines:
        # Check if line contains an obsolete variable
        should_remove = False
        stripped = line.strip()

        for var in obsolete:
            # Check for active or commented versions
            if stripped.startswith(f'{var}=') or stripped.startswith(f'# {var}='):
                should_remove = True
                removed_vars.append(var)
                removed_count += 1
                if not dry_run:
                    print(f"    - Removing: {var}")
                else:
                    print(f"    - Would remove: {var}")
                break

        if not should_remove:
            new_lines.append(line)

    if not dry_run and removed_count > 0:
        # Create backup before writing
        backup_path = backup_env_file(env_path)
        print(f"    ✓ Backup created: {backup_path}")

        # Write cleaned file
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
        print(f"    ✓ File updated: {removed_count} lines removed")

    return removed_count, removed_vars

def main():
    """Main migration script."""
    parser = argparse.ArgumentParser(description='Clean obsolete environment variables')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be removed without making changes')
    args = parser.parse_args()

    print("=" * 60)
    print("Environment Migration - Cleanup Obsolete Variables")
    print("=" * 60)

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")
    else:
        print("\n⚠️  This will modify your environment files!")
        print("   Backups will be created in config/backups/\n")

        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            print("\nMigration cancelled.")
            return 1

    env_files = [
        Path('config/.env.development'),
        Path('config/.env.staging'),
        Path('config/.env.production')
    ]

    total_removed = 0
    all_removed_vars = set()

    for env_file in env_files:
        print(f"\n📄 Processing: {env_file}")
        count, vars_removed = clean_env_file(env_file, dry_run=args.dry_run)
        total_removed += count
        all_removed_vars.update(vars_removed)

    # Summary
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)

    if args.dry_run:
        print(f"\n🔍 DRY RUN COMPLETE")
        print(f"   Would remove {total_removed} lines across {len(env_files)} files")
    else:
        print(f"\n✅ MIGRATION COMPLETE")
        print(f"   Removed {total_removed} obsolete variables")
        print(f"   Processed {len(env_files)} files")

    if all_removed_vars:
        print(f"\nRemoved variables:")
        for var in sorted(all_removed_vars):
            print(f"  - {var}")

    print("\n" + "=" * 60)

    # Additional recommendations
    if not args.dry_run:
        print("\n📋 Next Steps:")
        print("1. Restart your application to use the cleaned configuration")
        print("2. Test that all functionality still works")
        print("3. If issues occur, restore from backups in config/backups/")
        print("4. Remove backup files once confirmed working")

    return 0

if __name__ == "__main__":
    sys.exit(main())