import difflib
import os
import re
import sys
import time
from pathlib import Path

def _get_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    p = Path(__file__).resolve().parent
    if p.name == "actions":
        return p.parent
    return p

ROOT_DIR = _get_project_root()
TARGET_DIRS = ["actions", "core", "memory", "config", "dashboard", "plugins"]
EXCLUDE_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "env", "Lib", "lib", "Scripts", "site-packages",
    "model", "models", "alarm", "sounds", "node_modules", ".jarvis", ".nexus_backups", "build", "dist"
}

_RECENT_CHANGES: list[dict] = []
_FILE_SNAPSHOTS: dict[str, str] = {}

def record_change(file_path: Path, new_content: str) -> str:
    """Computes a live diff between previous and newly saved code."""
    rel_name = file_path.name
    old_content = _FILE_SNAPSHOTS.get(rel_name, "")
    _FILE_SNAPSHOTS[rel_name] = new_content

    if not old_content:
        return f"Baseline loaded for '{rel_name}'."

    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))

    added = [l[1:].strip() for l in diff if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:].strip() for l in diff if l.startswith("-") and not l.startswith("---")]

    highlights = []
    for l in added:
        if l.startswith("def ") or l.startswith("class ") or "return " in l:
            highlights.append(f"Added: {l}")
    for l in removed:
        if l.startswith("def ") or l.startswith("class "):
            highlights.append(f"Removed: {l}")

    time_str = time.strftime("%I:%M:%S %p")
    entry = {
        "file": rel_name,
        "time": time_str,
        "added_count": len(added),
        "removed_count": len(removed),
        "highlights": highlights,
        "sample": [l for l in added if l and not l.startswith("#")][:5]
    }
    _RECENT_CHANGES.insert(0, entry)
    if len(_RECENT_CHANGES) > 20:
        _RECENT_CHANGES.pop()

    summary_parts = [f"File: {rel_name} ({time_str})"]
    if highlights:
        summary_parts.extend(f"  • {h}" for h in highlights)
    elif entry["sample"]:
        summary_parts.append("  • Added snippet: " + "; ".join(entry["sample"][:3]))
    return "\n".join(summary_parts)

def get_recent_changes_report() -> str:
    if not _RECENT_CHANGES:
        return "No code changes have been recorded in the actions folder during this session yet."

    lines = ["=== RECENT CODE MODIFICATIONS IN THIS SESSION ==="]
    for idx, ch in enumerate(_RECENT_CHANGES[:5], 1):
        lines.append(f"\n[{idx}] {ch['file']} at {ch['time']}:")
        lines.append(f"    Lines added: {ch['added_count']} | Lines removed: {ch['removed_count']}")
        if ch["highlights"]:
            lines.append("    Key changes:")
            for h in ch["highlights"]:
                lines.append(f"      - {h}")
        elif ch["sample"]:
            lines.append("    Added code snippet:")
            for s in ch["sample"][:3]:
                lines.append(f"      + {s}")
    return "\n".join(lines)

def search_in_codebase(query: str) -> str:
    t0 = time.monotonic()
    query = query.strip()
    if not query:
        return "Search query cannot be empty."

    print(f"\n[CodebaseInspector] 🔍 Searching for '{query}' across project...")
    files = []
    for f in ROOT_DIR.glob("*.py"):
        files.append(f)
    for folder_name in TARGET_DIRS:
        folder = ROOT_DIR / folder_name
        if folder.exists() and folder.is_dir():
            for root, dirs, filenames in os.walk(folder):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for fname in filenames:
                    if fname.endswith((".py", ".json", ".txt")):
                        files.append(Path(root) / fname)

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    results = []
    for fpath in files:
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
            for idx, line in enumerate(content, 1):
                if pattern.search(line):
                    rel = fpath.relative_to(ROOT_DIR)
                    results.append(f"{rel}:{idx} | {line.strip()[:110]}")
                    if len(results) >= 20:
                        break
        except Exception:
            pass
        if len(results) >= 20:
            break

    elapsed = time.monotonic() - t0
    print(f"[CodebaseInspector] ⚡ Completed in {elapsed:.3f}s ({len(results)} matches found)")
    if not results:
        return f"No occurrences of '{query}' found."
    return f"=== Search Results ({len(results)} found in {elapsed:.2f}s) ===\n" + "\n".join(results)

def read_code_file(file_path: str, start_line: int = 1, max_lines: int = 150) -> str:
    target = (ROOT_DIR / file_path).resolve()
    if not target.exists() or not target.is_file():
        target = (ROOT_DIR / "actions" / file_path).resolve()
        if not target.exists() or not target.is_file():
            return f"File '{file_path}' not found."

    raw_lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    total = len(raw_lines)
    start_idx = max(0, start_line - 1)
    end_idx = min(total, start_idx + max_lines)
    numbered = [f"{i + 1:04d} | {raw_lines[i]}" for i in range(start_idx, end_idx)]
    return f"=== {target.relative_to(ROOT_DIR)} (Lines {start_idx + 1}-{end_idx} of {total}) ===\n" + "\n".join(numbered)

def list_project_tree(subfolder: str = "") -> str:
    lines = [f"📁 Project: {ROOT_DIR.name}/"]
    for f in sorted(ROOT_DIR.glob("*.py")):
        lines.append(f"  📄 {f.name}")
    for folder in TARGET_DIRS:
        p = ROOT_DIR / folder
        if p.exists() and p.is_dir():
            lines.append(f"  📂 {folder}/")
            for sub in sorted(p.glob("*.py")):
                lines.append(f"     📄 {sub.name}")
    return "\n".join(lines)

def codebase_inspector(parameters: dict, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "search_code")).strip().lower()
    file_path = str(params.get("file_path", "")).strip()
    query = str(params.get("query", "")).strip()
    start_line = int(params.get("start_line", 1))

    if player:
        player.write_log(f"CODE: 🔍 Codebase inspection ({action})...")

    if action in ("recent_changes", "what_changed", "diff", "changes"):
        return get_recent_changes_report()

    if action in ("search", "search_code", "find"):
        return search_in_codebase(query or file_path)

    if action in ("read", "read_file", "view"):
        return read_code_file(file_path, start_line=start_line)

    if action in ("list_tree", "list_files", "tree"):
        return list_project_tree(file_path)

    return f"Unknown action: {action}"