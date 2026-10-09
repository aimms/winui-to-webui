import shutil
import filecmp
import difflib
from pathlib import Path
import subprocess
import sys
import winui_to_webui    

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

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
    # safety: only allow deletions inside the examples base folder
    path_res = path.resolve()
    base_res = examples_base.resolve()
    if base_res not in path_res.parents and path_res != base_res:
        raise RuntimeError(f"Refusing to remove directory outside examples: {path}")
    shutil.rmtree(path)

def compare_text_files(a: Path, b: Path) -> None:
    """
    Compare two text files after normalizing line endings to Unix style.
    
    :param a: Path to the file containing the actual output.
    :type a: Path
    :param b: Path to the file containing the expected output.
    :type b: Path
    :return: None. Raises AssertionError when the files differ and includes a unified diff.
    :rtype: None
    """
    a_text = a.read_text(encoding="utf-8").replace("\r\n", "\n")
    b_text = b.read_text(encoding="utf-8").replace("\r\n", "\n")
    if a_text != b_text:
        diff = "\n".join(difflib.unified_diff(
            b_text.splitlines(), a_text.splitlines(),
            fromfile=str(b), tofile=str(a), lineterm=""
        ))
        raise AssertionError(f"File mismatch: {a} != {b}\n{diff}")

def assert_dirs_equal(got_dir: Path, expected_dir: Path) -> None:
    """
    Compare files under an expected directory against a directory of actual results.
    
    :param got_dir: Directory containing the produced files.
    :type got_dir: Path
    :param expected_dir: Directory containing the baseline files to compare against.
    :type expected_dir: Path
    :return: None. Raises AssertionError when a missing or differing file is found.
    :rtype: None
    """
    # Walk expected files and ensure they exist and match
    for expected in expected_dir.rglob("*"):
        rel = expected.relative_to(expected_dir)
        got = got_dir / rel
        assert got.exists(), f"Missing output file: {got}"
        if expected.is_file():
            # simple heuristic: treat binary files by size equality
            if expected.suffix.lower() in {".json", ".txt", ".xml", ".html", ".js", ".py", ".css",".aimms", ".ams"}:
                compare_text_files(got, expected)
            else:
                assert got.read_bytes() == expected.read_bytes(), f"Binary file differs: {got}"

def run_example(example_name: str) -> None:
    """
    Execute the conversion for a named example and compare generated output with expected files.
    
    :param example_name: Name of the example directory under `examples`.
    :type example_name: str
    :return: None. Raises AssertionError when execution fails or outputs differ from expectations.
    :rtype: None
    """
    src = EXAMPLES_DIR / example_name
    assert src.exists(), f"Example not found: {str(src.resolve(strict=False))}"
    input_dir = src / "input"
    assert input_dir.exists(), f"Input directory not found: {str(input_dir.resolve(strict=False))}"
    expected_dir = src / "expected"
    assert expected_dir.exists(), f"Expected directory not found: {str(expected_dir.resolve(strict=False))}"
    # Run the conversion in a fresh Python process so AIMMS may be loaded safely.
    runner = Path(__file__).parent / "scripts" / "run_example.py"
    if not runner.exists():
        raise AssertionError(f"Runner script not found: {runner}")

    cmd = [sys.executable, str(runner), example_name]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"Example runner failed for {example_name}\n--- stdout/stderr ---\n{proc.stdout}")

    # Now compare outputs in work against expected
    work_dir = src / "work"
    assert work_dir.exists(), f"Work dir missing after runner: {work_dir}"
    assert_dirs_equal(work_dir, expected_dir)

def test_all_examples():
    """
    Run conversion and comparison for every example that has input and expected directories.
    
    :return: None. Relies on pytest to surface assertion failures.
    :rtype: None
    """
    print(f"Current examples directory: {str(EXAMPLES_DIR.resolve(strict=False))}")
    assert EXAMPLES_DIR.exists(), f"Examples directory does not exist: {EXAMPLES_DIR}"
    for ex in (EXAMPLES_DIR).iterdir():
        if ex.is_dir() and (ex / "input").exists() and (ex / "expected").exists():
            print(f"--- Testing example: {ex.name} ---")
            run_example(ex.name)
