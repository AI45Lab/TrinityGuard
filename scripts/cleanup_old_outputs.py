"""清理旧的输出文件脚本。

将散落在项目目录中的旧输出文件移动到归档目录。
"""

import sys
from pathlib import Path
import shutil
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def cleanup_old_outputs(dry_run=True):
    """清理旧的输出文件。

    Args:
        dry_run: 如果为 True，只显示将要移动的文件，不实际移动
    """
    # 定义要搜索的目录
    search_dirs = [
        project_root,  # 项目根目录
        project_root / "examples" / "full_demo",  # examples/full_demo
    ]

    # 定义要查找的文件模式
    patterns = [
        "*.txt",
        "*.md",
    ]

    # 排除的文件（不应该被移动）
    exclude_patterns = [
        "README.md",
        "requirements.txt",
        "next_step.md",
        "analysis.md",
        "full_demo_test.md",
        "MAS风险层级说明.md",
    ]

    # 排除的文件名前缀
    exclude_prefixes = [
        ".",  # 隐藏文件
    ]

    # 创建归档目录
    archive_dir = project_root / "logs" / "archive" / datetime.now().strftime("%Y%m%d_%H%M%S")

    found_files = []

    # 搜索文件
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        for pattern in patterns:
            for file_path in search_dir.glob(pattern):
                # 跳过目录
                if file_path.is_dir():
                    continue

                # 跳过排除的文件
                if file_path.name in exclude_patterns:
                    continue

                # 跳过以特定前缀开头的文件
                if any(file_path.name.startswith(prefix) for prefix in exclude_prefixes):
                    continue

                # 跳过 logs 目录下的文件
                if "logs" in file_path.parts:
                    continue

                # 跳过 docs 目录下的文件
                if "docs" in file_path.parts:
                    continue

                # 跳过 src 目录下的文件
                if "src" in file_path.parts:
                    continue

                # 跳过 tests 目录下的文件
                if "tests" in file_path.parts:
                    continue

                # 检查文件是否看起来像是输出文件
                # 通常包含 summary, research, output, result 等关键词
                keywords = ["summary", "research", "output", "result", "work", "report"]
                if any(keyword in file_path.name.lower() for keyword in keywords):
                    found_files.append(file_path)

    if not found_files:
        print("✓ 没有找到需要清理的旧输出文件")
        return

    print(f"找到 {len(found_files)} 个旧输出文件:")
    print()

    for file_path in found_files:
        rel_path = file_path.relative_to(project_root)
        size = file_path.stat().st_size
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        print(f"  - {rel_path}")
        print(f"    大小: {size} bytes | 修改时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

    print()

    if dry_run:
        print("🔍 这是预览模式（dry run）")
        print(f"   如果执行，这些文件将被移动到: {archive_dir.relative_to(project_root)}")
        print()
        print("要实际执行清理，请运行:")
        print("  python scripts/cleanup_old_outputs.py --execute")
        return

    # 创建归档目录
    archive_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 创建归档目录: {archive_dir.relative_to(project_root)}")
    print()

    # 移动文件
    moved_count = 0
    for file_path in found_files:
        try:
            # 保持相对路径结构
            rel_path = file_path.relative_to(project_root)
            dest_path = archive_dir / rel_path

            # 创建目标目录
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # 移动文件
            shutil.move(str(file_path), str(dest_path))
            print(f"✓ 移动: {rel_path} -> {dest_path.relative_to(project_root)}")
            moved_count += 1
        except Exception as e:
            print(f"✗ 移动失败: {file_path.name} - {e}")

    print()
    print(f"✅ 完成！移动了 {moved_count}/{len(found_files)} 个文件")
    print(f"   归档位置: {archive_dir.relative_to(project_root)}")


def main():
    """主函数。"""
    import argparse

    parser = argparse.ArgumentParser(
        description="清理旧的输出文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 预览将要移动的文件（不实际移动）
  python scripts/cleanup_old_outputs.py

  # 实际执行清理
  python scripts/cleanup_old_outputs.py --execute
        """
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="实际执行清理（默认为预览模式）"
    )

    args = parser.parse_args()

    print()
    print("=" * 60)
    print("清理旧输出文件")
    print("=" * 60)
    print()

    cleanup_old_outputs(dry_run=not args.execute)

    print()


if __name__ == "__main__":
    main()