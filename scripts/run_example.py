#!/usr/bin/env python3
"""
Run a single example conversion in a fresh Python process.

Usage: python scripts/run_example.py <example_name>

This script copies `examples/<example_name>/input` -> `examples/<example_name>/work`,
then calls `winui_to_webui.process_aimms_app(work_path, example_name)`.

If the example has a `pagemarkers.txt` file (one WinUI page Name per line, blank
lines and lines starting with '#' ignored), that full conversion is skipped in favor
of calling `process_aimms_app(work_path, example_name, page_name=<line>)` once per
line, in order - simulating a sequence of separate `w2w --page <name>` invocations
against the same project, to exercise single-page mode.

Exit code 0 indicates success.
"""
import sys
import shutil
from pathlib import Path
import os

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
REPO_ROOT = Path(__file__).resolve().parents[1]

# Ensure the repository root is on sys.path so local imports work when this
# script is executed from a subprocess whose CWD may differ.
sys.path.insert(0, str(REPO_ROOT))
# Also set CWD to repo root to make relative file operations predictable.
os.chdir(str(REPO_ROOT))

def safe_rmtree(path: Path, examples_base: Path) -> None:
    """
    Remove a directory only when it resides within the examples directory hierarchy.
    
    :param path: Directory path to remove.
    :type path: Path
    :param examples_base: Base directory under which deletions are allowed.
    :type examples_base: Path
    :return: None. Deletes the directory if it is inside the allowed base path.
    :rtype: None
    """
    path_res = path.resolve()
    base_res = examples_base.resolve()
    if base_res not in path_res.parents and path_res != base_res:
        raise RuntimeError(f"Refusing to remove directory outside examples: {path}")
    shutil.rmtree(path)

def read_page_markers(example_dir: Path) -> list[str]:
    """
    Read `pagemarkers.txt` from an example directory, if present.

    :param example_dir: Root directory of the example (containing input/, expected/, etc.).
    :type example_dir: Path
    :return: List of page names (one per non-blank, non-comment line), in file order.
        Empty list when no marker file exists, meaning "run a normal full conversion".
    :rtype: list[str]
    """
    markers_file = example_dir / "pagemarkers.txt"
    if not markers_file.exists():
        return []
    page_names = []
    for line in markers_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            page_names.append(line)
    return page_names

def main(argv):
    """
    Run a single example conversion, optionally comparing the output with expected results.
    
    :param argv: Command-line arguments passed to the script.
    :type argv: list
    :return: Exit code indicating success (0), usage issues (2), or comparison failure (3).
    :rtype: int
    """
    # Usage: run_example.py [--compare] [--compare-only] <example_name>
    compare = False
    compare_only = False
    args = [a for a in argv[1:] if a != '']
    if not args:
        print("Usage: run_example.py [--compare] [--compare-only] <example_name>", file=sys.stderr)
        return 2
    if '--compare' in args:
        compare = True
        args.remove('--compare')
    if '--compare-only' in args:
        compare = True
        compare_only = True
        args.remove('--compare-only')
    if not args:
        print("Usage: run_example.py [--compare] [--compare-only] <example_name>", file=sys.stderr)
        return 2
    example_name = args[0]
    src = EXAMPLES_DIR / example_name
    if not src.exists():
        print(f"Example not found: {src}", file=sys.stderr)
        return 2

    if not compare_only:
        input_dir = src / "input"
        if not input_dir.exists():
            print(f"Input directory not found: {input_dir}", file=sys.stderr)
            return 2

        # Work directory under example
        work_dir = src / "work"
        if work_dir.exists():
            safe_rmtree(work_dir, EXAMPLES_DIR)
        shutil.copytree(input_dir, work_dir)

        page_names = read_page_markers(src)

        # Run the conversion in this process
        try:
            # import locally to keep top-level light for pytest discovery
            import winui_to_webui
            if page_names:
                for page_name in page_names:
                    winui_to_webui.process_aimms_app(str(work_dir), example_name, page_name=page_name)
            else:
                winui_to_webui.process_aimms_app(str(work_dir), example_name)
        except Exception as e:
            print(f"Error running conversion for example {example_name}: {e}", file=sys.stderr)
            raise

    work_dir = src / "work"

    # Optionally compare work against expected and return non-zero on mismatch
    if compare:
        try:
            from scripts import example_utils
        except Exception:
            # fallback import if executed differently
            import example_utils
        expected_dir = EXAMPLES_DIR / example_name / 'expected'
        ok, msg = example_utils.assert_dirs_equal(work_dir, expected_dir)
        if not ok:
            print(f"Comparison failed for {example_name}:\n{msg}", file=sys.stderr)
            return 3
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
