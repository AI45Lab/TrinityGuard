"""Script to fix existing log files by resolving chat_manager recipients.

This script processes existing comprehensive_report JSON files and resolves
all 'chat_manager' recipients to actual target agents.

Usage:
    python scripts/fix_existing_logs.py
    python scripts/fix_existing_logs.py --input logs/level3/comprehensive_report_1769684853.json
    python scripts/fix_existing_logs.py --all  # Process all comprehensive_report files
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.message_utils import resolve_nested_messages, get_resolution_stats


def process_file(input_path: Path, output_path: Path = None, in_place: bool = False):
    """Process a single JSON file to resolve chat_manager recipients.

    Args:
        input_path: Path to input JSON file
        output_path: Path to output JSON file (if not in_place)
        in_place: If True, overwrite the input file
    """
    print(f"Processing: {input_path}")

    # Read input file
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Count chat_manager occurrences before resolution
    chat_manager_count_before = count_chat_managers(data)
    print(f"  Found {chat_manager_count_before} 'chat_manager' recipients")

    # Resolve chat_manager recipients
    resolved_data = resolve_nested_messages(data)

    # Count chat_manager occurrences after resolution
    chat_manager_count_after = count_chat_managers(resolved_data)
    resolved_count = chat_manager_count_before - chat_manager_count_after

    print(f"  Resolved {resolved_count} recipients")
    print(f"  Remaining 'chat_manager': {chat_manager_count_after} (last messages in sequences)")

    # Determine output path
    if in_place:
        output_path = input_path
    elif output_path is None:
        # Create backup and use original name
        backup_path = input_path.with_suffix('.json.backup')
        input_path.rename(backup_path)
        output_path = input_path
        print(f"  Backup created: {backup_path}")

    # Write output file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resolved_data, f, ensure_ascii=False, indent=2)

    print(f"  Output saved: {output_path}")
    print()

    return resolved_count


def count_chat_managers(data, count=0):
    """Recursively count 'chat_manager' occurrences in nested structures."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key in ('to_agent', 'to') and value == 'chat_manager':
                count += 1
            count = count_chat_managers(value, count)
    elif isinstance(data, list):
        for item in data:
            count = count_chat_managers(item, count)
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Fix existing log files by resolving chat_manager recipients",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a specific file (creates backup)
  python scripts/fix_existing_logs.py --input logs/level3/comprehensive_report_1769684853.json

  # Process in-place (no backup)
  python scripts/fix_existing_logs.py --input logs/level3/comprehensive_report_1769684853.json --in-place

  # Process all comprehensive_report files in logs/level3/
  python scripts/fix_existing_logs.py --all

  # Process all files in a specific directory
  python scripts/fix_existing_logs.py --dir logs/level3/
        """
    )

    parser.add_argument(
        '--input',
        type=str,
        help='Path to input JSON file'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Path to output JSON file (default: overwrites input with backup)'
    )
    parser.add_argument(
        '--in-place',
        action='store_true',
        help='Overwrite input file without creating backup'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all comprehensive_report_*.json files in logs/level3/'
    )
    parser.add_argument(
        '--dir',
        type=str,
        help='Process all comprehensive_report_*.json files in specified directory'
    )

    args = parser.parse_args()

    # Determine which files to process
    files_to_process = []

    if args.input:
        # Single file
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: File not found: {input_path}")
            return 1
        files_to_process.append(input_path)

    elif args.all:
        # All files in default logs/level3/
        logs_dir = project_root / "logs" / "level3"
        files_to_process = list(logs_dir.glob("comprehensive_report_*.json"))

    elif args.dir:
        # All files in specified directory
        dir_path = Path(args.dir)
        if not dir_path.exists():
            print(f"Error: Directory not found: {dir_path}")
            return 1
        files_to_process = list(dir_path.glob("comprehensive_report_*.json"))

    else:
        # Default: process most recent file in logs/level3/
        logs_dir = project_root / "logs" / "level3"
        if logs_dir.exists():
            files = list(logs_dir.glob("comprehensive_report_*.json"))
            if files:
                # Sort by modification time, get most recent
                files_to_process = [max(files, key=lambda p: p.stat().st_mtime)]
            else:
                print(f"No comprehensive_report files found in {logs_dir}")
                return 1
        else:
            print(f"Error: Directory not found: {logs_dir}")
            return 1

    # Process files
    if not files_to_process:
        print("No files to process")
        return 0

    print(f"Found {len(files_to_process)} file(s) to process\n")

    total_resolved = 0
    for input_path in files_to_process:
        output_path = Path(args.output) if args.output else None
        resolved_count = process_file(input_path, output_path, args.in_place)
        total_resolved += resolved_count

    print("=" * 60)
    print(f"Total files processed: {len(files_to_process)}")
    print(f"Total recipients resolved: {total_resolved}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())