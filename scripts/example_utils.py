from pathlib import Path
from typing import Tuple
import difflib

def compare_text_files(a: Path, b: Path) -> Tuple[bool, str]:
    """
    Compare two text files after normalizing line endings to Unix style.
    
    :param a: Path to the file containing the actual output.
    :type a: Path
    :param b: Path to the file containing the expected output.
    :type b: Path
    :return: Tuple where the first element is True when files match, otherwise False with a unified diff as the second element.
    :rtype: Tuple[bool, str]
    """
    a_text = a.read_text(encoding="utf-8").replace("\r\n", "\n")
    b_text = b.read_text(encoding="utf-8").replace("\r\n", "\n")
    if a_text != b_text:
        diff = "\n".join(difflib.unified_diff(
            b_text.splitlines(), a_text.splitlines(),
            fromfile=str(b), tofile=str(a), lineterm=""
        ))
        return False, diff
    return True, ""

def assert_dirs_equal(got_dir: Path, expected_dir: Path) -> Tuple[bool, str]:
    """
    Compare files under an expected directory against a directory of actual results.

    :param got_dir: Directory containing the produced files.
    :type got_dir: Path
    :param expected_dir: Directory containing the baseline files to compare against.
    :type expected_dir: Path
    :return: Tuple where the first element is True when all expected files match, otherwise False with a descriptive message.
    :rtype: Tuple[bool, str]
    """
    messages = []
    if not expected_dir.exists():
        return False, f"Expected directory not found: {expected_dir}"
    for expected in expected_dir.rglob("*"):
        rel = expected.relative_to(expected_dir)
        got = got_dir / rel
        if not got.exists():
            messages.append(f"Missing output file: {got}")
            continue
        if expected.is_file():
            # treat common text extensions as text
            if expected.suffix.lower() in {".json", ".txt", ".xml", ".html", ".js", ".py", ".css", ".ams", ".aimms"}:
                ok, diff = compare_text_files(got, expected)
                if not ok:
                    messages.append(diff)
            else:
                if got.read_bytes() != expected.read_bytes():
                    messages.append(f"Binary file differs: {got}")
    if messages:
        return False, "\n\n".join(messages)
    return True, ""
