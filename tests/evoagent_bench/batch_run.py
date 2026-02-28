import argparse
import datetime
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    from .run_workflow import run_evoagent_workflow
except Exception:
    from tests.evoagent_bench.run_workflow import run_evoagent_workflow


def _process_file(file_path: Path, tests: Optional[List[str]], logs_dir: Path) -> Dict[str, Any]:
    result = run_evoagent_workflow(str(file_path), tests_to_run=tests)
    out_path = logs_dir / f"{file_path.stem}_results.json"
    if result is not None:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    return {
        "file": str(file_path),
        "ok": result is not None,
        "output": str(out_path) if result is not None else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="./workflow")
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    parser.add_argument("--tests", type=str, default="")
    parser.add_argument("--logs-dir", type=str, default="./logs")
    args = parser.parse_args()

    base_dir = Path(args.dir).resolve()
    logs_dir = Path(args.logs_dir).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    tests = None
    if args.tests:
        tests = [t.strip() for t in args.tests.split(",") if t.strip()]

    files = sorted([p for p in base_dir.glob("*.json") if p.is_file()])
    results = []

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        fut_map = {ex.submit(_process_file, fp, tests, logs_dir): fp for fp in files}
        for fut in as_completed(fut_map):
            try:
                results.append(fut.result())
            except Exception as e:
                results.append({"file": str(fut_map[fut]), "ok": False, "error": str(e)})

    summary = {
        "timestamp": datetime.datetime.now().isoformat(),
        "input_dir": str(base_dir),
        "total": len(files),
        "succeeded": sum(1 for r in results if r.get("ok")),
        "failed": sum(1 for r in results if not r.get("ok")),
        "details": results,
    }
    summary_path = logs_dir / f"batch_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
