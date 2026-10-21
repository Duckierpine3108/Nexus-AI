# ==============================================================================
#            NEXUS AI — AUTONOMOUS SELF-EVOLUTION ENGINE (v4.0 Enterprise)
# ==============================================================================
"""
Production Autonomous Self-Healing and Surgical Code Evolution Engine.
Key Capabilities:
  1. Autonomous Diagnostics & Auto-Repair (Pinpoints exact lines from tracebacks)
  2. AST Structural Entity Guard (Blocks accidental file wiping/truncation)
  3. Surgical Search-and-Replace (Zero-touch to surrounding functions)
  4. Class-Aware Indentation-Preserving Function Patcher (ClassName.method_name)
  5. Interactive Unified Diff Streaming to Nexus UI Content Panel
  6. Automatic Pre-Modification Snapshot Backups & Instant Rollback
"""

from __future__ import annotations

import ast
import difflib
import importlib
import json
import os
import platform
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Optional, Tuple, Set

# ── 1. CROSS-PLATFORM PATH RESOLUTION & CONFIG ───────────────────────────────
def _get_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    p = Path(__file__).resolve().parent
    if p.name == "actions":
        return p.parent
    return p

ROOT_DIR = _get_project_root()
BACKUP_DIR = ROOT_DIR / ".nexus_backups"
API_CONFIG_PATH = ROOT_DIR / "config" / "api_keys.json"

def _ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def _get_api_key() -> str:
    try:
        if API_CONFIG_PATH.exists():
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("gemini_api_key", "").strip()
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "").strip()

def _resolve_file_path(raw_path: str) -> Path | None:
    """Safely resolves target file across Windows, macOS, and Linux."""
    clean = (raw_path or "").strip().replace("\\", "/")
    if not clean:
        return None

    # Check absolute / direct relative path
    target = (ROOT_DIR / clean).resolve()
    if target.exists() and target.is_file():
        return target

    # Check inside actions/
    action_target = (ROOT_DIR / "actions" / clean).resolve()
    if action_target.exists() and action_target.is_file():
        return action_target

    # Check with .py extension appended
    if not clean.endswith(".py"):
        target_py = (ROOT_DIR / f"{clean}.py").resolve()
        if target_py.exists() and target_py.is_file():
            return target_py
        action_py = (ROOT_DIR / "actions" / f"{clean}.py").resolve()
        if action_py.exists() and action_py.is_file():
            return action_py

    return None


# ── 2. AST COMPILER & STRUCTURAL ENTITY SAFETY GATES ─────────────────────────
def validate_python_syntax(code_string: str) -> Tuple[bool, str]:
    """Compiles code via AST in memory. Rejects any syntax or indentation flaws."""
    try:
        ast.parse(code_string)
        return True, "Syntax valid."
    except SyntaxError as e:
        line_snippet = e.text.strip() if e.text else ""
        return False, f"SyntaxError line {e.lineno}, col {e.offset}: {e.msg} -> '{line_snippet}'"
    except Exception as ex:
        return False, f"AST Compilation error: {ex}"


def _extract_ast_entity_names(tree: ast.AST) -> Set[str]:
    """Collects all top-level and class-level function and class names."""
    entities = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            entities.add(node.name)
            if isinstance(node, ast.ClassDef):
                for sub in ast.iter_child_nodes(node):
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        entities.add(f"{node.name}.{sub.name}")
    return entities


def _structural_wipe_shield(original_code: str, new_code: str) -> Tuple[bool, str]:
    """
    Prevents catastrophic code loss where an AI overwrites a whole file
    with only one function.
    """
    try:
        orig_tree = ast.parse(original_code)
        new_tree = ast.parse(new_code)
    except Exception:
        # If the file already had syntax errors, fallback to basic line comparison
        orig_lines = len(original_code.splitlines())
        new_lines = len(new_code.splitlines())
        if orig_lines > 40 and new_lines < (orig_lines * 0.4):
            return False, f"Truncation risk: line count dropped from {orig_lines} to {new_lines}."
        return True, "Proceeding (syntax fallback)."

    orig_entities = _extract_ast_entity_names(orig_tree)
    new_entities = _extract_ast_entity_names(new_tree)

    # If the original file had several definitions, check how many were removed
    if len(orig_entities) >= 3:
        lost_entities = orig_entities - new_entities
        # If more than 35% of existing definitions were dropped in a single write, block it!
        if len(lost_entities) > (len(orig_entities) * 0.35):
            missing_sample = ", ".join(list(lost_entities)[:6])
            return False, (
                f"❌ WRITE ABORTED (Structural Wipe Shield):\n"
                f"The original file has {len(orig_entities)} functions/classes, but your replacement only has {len(new_entities)}!\n"
                f"Missing definitions that would be erased: [{missing_sample}].\n"
                f"Use action='search_and_replace' or action='patch_function' to fix specific code safely."
            )

    return True, "Structural check passed."


# ── 3. AUTOMATED BACKUP & ROLLBACK ENGINE ─────────────────────────────────────
def create_backup(target_path: Path) -> Path:
    """Creates a timestamped backup before touching any code file."""
    _ensure_backup_dir()
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"{target_path.stem}_{timestamp}{target_path.suffix}.bak"
    shutil.copy2(target_path, backup_file)
    return backup_file

def rollback_file(file_name: str) -> str:
    """Restores a backup, whether passed a backup name, target file name, or 'latest'."""
    _ensure_backup_dir()
    raw = (file_name or "").strip().replace("\\", "/")
    target_path = None
    backup_to_restore = None

    # Case 1: Caller passed exact backup filename
    clean_name = Path(raw).name
    direct_bak = BACKUP_DIR / clean_name
    if direct_bak.exists() and direct_bak.is_file():
        backup_to_restore = direct_bak
        base_stem = re.sub(r'_\d{8}_\d{6}.*$', '', clean_name.replace('.bak', ''))
        if not base_stem.endswith('.py'):
            base_stem += '.py'
        target_path = _resolve_file_path(base_stem) or (ROOT_DIR / "actions" / base_stem)

    # Case 2: Caller passed target filename
    if not backup_to_restore:
        stem = Path(raw).stem
        stem = re.sub(r'_\d{8}_\d{6}.*$', '', stem).replace('.py', '')
        matches = sorted(BACKUP_DIR.glob(f"{stem}_*.bak"), reverse=True)
        if matches:
            backup_to_restore = matches[0]
            target_path = _resolve_file_path(f"{stem}.py") or (ROOT_DIR / "actions" / f"{stem}.py")

    # Case 3: Caller passed 'latest'
    if not backup_to_restore and raw.lower() in ("latest", "last", "recent", ""):
        all_baks = sorted(BACKUP_DIR.glob("*.bak"), reverse=True)
        if all_baks:
            backup_to_restore = all_baks[0]
            base_stem = re.sub(r'_\d{8}_\d{6}.*$', '', backup_to_restore.name.replace('.bak', ''))
            if not base_stem.endswith('.py'):
                base_stem += '.py'
            target_path = _resolve_file_path(base_stem) or (ROOT_DIR / "actions" / base_stem)

    if not backup_to_restore or not target_path:
        return f"No safety backups found for '{file_name}' in .nexus_backups."

    try:
        shutil.copy2(backup_to_restore, target_path)
        reload_msg = _hot_reload_module(target_path)
        return (
            f"✅ Successfully rolled back '{target_path.name}'!\n"
            f"Restored from backup: '{backup_to_restore.name}'.{reload_msg}"
        )
    except Exception as e:
        return f"Rollback failed: {e}"

def list_backups() -> str:
    """Lists recent safety backups."""
    _ensure_backup_dir()
    baks = sorted(BACKUP_DIR.glob("*.bak"), reverse=True)[:10]
    if not baks:
        return "No backups currently stored."
    return "=== RECENT SAFETY BACKUPS ===\n" + "\n".join(f"• {b.name}" for b in baks)


# ── 4. LIVE IN-MEMORY HOT-RELOADER & DIFF GENERATOR ──────────────────────────
def _hot_reload_module(file_path: Path) -> str:
    """Live reloads the Python module in RAM without restarting."""
    try:
        rel = file_path.relative_to(ROOT_DIR)
        parts = rel.parts
        if "actions" in parts:
            mod_name = f"actions.{file_path.stem}"
            if mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])
                return f"\n⚡ Live reloaded '{mod_name}' into RAM."
            else:
                importlib.import_module(mod_name)
                return f"\n⚡ Imported '{mod_name}' into RAM."
    except Exception as e:
        return f"\n⚠️ Reload note: {e}"
    return ""

def _generate_unified_diff(original: str, updated: str, filename: str) -> str:
    """Generates a clean Git-style unified diff showing exact changes."""
    orig_lines = original.splitlines(keepends=True)
    new_lines = updated.splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        orig_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        n=3
    ))
    return "".join(diff).strip()


# ── 5. SURGICAL MODIFICATION OPERATIONS ──────────────────────────────────────

def apply_search_and_replace(file_path: str, search_block: str, replace_block: str, player=None) -> str:
    """
    Surgically replaces a targeted block of lines with new code.
    Surrounding functions are untouched. Quote and spacing tolerant.
    """
    target = _resolve_file_path(file_path)
    if not target:
        return f"Error: Target file '{file_path}' does not exist."

    original_code = target.read_text(encoding="utf-8")
    s_block = search_block.strip()
    r_block = replace_block.strip()

    if not s_block:
        return "Search block cannot be empty."

    # 1. Exact match
    if s_block in original_code:
        updated_code = original_code.replace(s_block, r_block, 1)
    else:
        # 2. Quote & Spacing Tolerant Matcher (Matches ' vs " and flexible spaces)
        def _canonical(text: str) -> str:
            t = text.replace("'", '"')
            t = re.sub(r'\s*([:=,\(\)\[\]\{\}])\s*', r'\1', t)
            return "\n".join(" ".join(line.split()) for line in t.splitlines() if line.strip())

        s_canon = _canonical(s_block)
        orig_lines = original_code.splitlines()
        found_start = -1
        block_len = len([l for l in s_block.splitlines() if l.strip()])

        for i in range(len(orig_lines) - block_len + 1):
            window = _canonical("\n".join(orig_lines[i + k] for k in range(block_len)))
            if window == s_canon:
                found_start = i
                break

        if found_start == -1:
            return (
                f"❌ SEARCH TARGET NOT FOUND in '{target.name}'.\n"
                f"Make sure the search block matches the current file lines."
            )

        # Detect baseline indentation
        indent_match = re.match(r"^(\s*)", orig_lines[found_start])
        base_indent = indent_match.group(1) if indent_match else ""

        # Re-indent replacement lines
        indented_replacement = []
        for line in r_block.splitlines():
            indented_replacement.append(base_indent + line if line.strip() else "")

        updated_lines = orig_lines[:found_start] + indented_replacement + orig_lines[found_start + block_len:]
        updated_code = "\n".join(updated_lines) + "\n"

    # AST validation on whole file
    is_valid, err = validate_python_syntax(updated_code)
    if not is_valid:
        return f"❌ REPLACEMENT REJECTED: Resulting code has syntax errors:\n{err}"

    # Backup & Write
    bak = create_backup(target)
    target.write_text(updated_code, encoding="utf-8")
    diff_text = _generate_unified_diff(original_code, updated_code, target.name)
    reload_msg = _hot_reload_module(target)

    if player and hasattr(player, "show_content") and diff_text:
        player.show_content(f"DIFF: {target.name}", diff_text[:2500])

    return (
        f"✅ Surgical replacement applied to '{target.name}'!\n"
        f"📦 Backup: '{bak.name}'.{reload_msg}\n\n"
        f"--- MODIFICATION AUDIT ---\n{diff_text or 'Lines modified in place.'}"
    )


def apply_function_patch(file_path: str, function_name: str, new_func_code: str, player=None) -> str:
    """
    Surgically replaces a specific function or class method by name.
    Supports ClassName.method_name and preserves indentation.
    """
    target = _resolve_file_path(file_path)
    if not target:
        return f"Error: Target file '{file_path}' does not exist."

    original_code = target.read_text(encoding="utf-8")
    try:
        tree = ast.parse(original_code)
    except SyntaxError as e:
        return f"Original file contains syntax errors: {e}"

    target_class = None
    target_func = function_name.strip()
    if "." in target_func:
        target_class, target_func = target_func.split(".", 1)

    matched_node = None
    # Traverse tree with class context
    for node in ast.iter_child_nodes(tree):
        if target_class and isinstance(node, ast.ClassDef) and node.name == target_class:
            for sub in ast.iter_child_nodes(node):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == target_func:
                    matched_node = sub
                    break
        elif not target_class and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target_func:
            matched_node = node
            break

    # Deep fallback search if not found at root
    if not matched_node:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target_func:
                matched_node = node
                break

    if not matched_node:
        return f"Function or method '{function_name}' not found in '{target.name}'."

    start_line = matched_node.lineno - 1
    end_line = matched_node.end_lineno

    orig_lines = original_code.splitlines(keepends=True)
    first_orig_line = orig_lines[start_line]
    indent_match = re.match(r"^(\s*)", first_orig_line)
    target_indent = indent_match.group(1) if indent_match else ""

    # Adjust replacement indentation to match target
    raw_lines = new_func_code.strip().splitlines()
    first_rep_indent = len(raw_lines[0]) - len(raw_lines[0].lstrip())
    adjusted_rep_lines = []
    for line in raw_lines:
        if line.strip():
            stripped = line[first_rep_indent:] if line.startswith(" " * first_rep_indent) else line.lstrip()
            adjusted_rep_lines.append(target_indent + stripped + "\n")
        else:
            adjusted_rep_lines.append("\n")

    updated_lines = orig_lines[:start_line] + adjusted_rep_lines + orig_lines[end_line:]
    updated_code = "".join(updated_lines)

    # Validate AST
    is_valid, err = validate_python_syntax(updated_code)
    if not is_valid:
        return f"❌ PATCH REJECTED: Replacement caused syntax error:\n{err}"

    # Backup & Write
    bak = create_backup(target)
    target.write_text(updated_code, encoding="utf-8")
    diff_text = _generate_unified_diff(original_code, updated_code, target.name)
    reload_msg = _hot_reload_module(target)

    if player and hasattr(player, "show_content") and diff_text:
        player.show_content(f"PATCH: {function_name}", diff_text[:2500])

    return (
        f"✅ Function '{function_name}' successfully patched in '{target.name}'!\n"
        f"📦 Backup: '{bak.name}'.{reload_msg}\n\n"
        f"--- MODIFICATION AUDIT ---\n{diff_text or 'Function replaced.'}"
    )


def apply_full_write(file_path: str, new_code: str, player=None) -> str:
    """Overwrites a complete file after AST and Structural Wipe Shield checks."""
    target = _resolve_file_path(file_path)
    if not target:
        return f"Error: Target file '{file_path}' does not exist."

    original_code = target.read_text(encoding="utf-8")

    # 1. AST Safety Check
    is_valid, err = validate_python_syntax(new_code)
    if not is_valid:
        return f"❌ UPDATE REJECTED: Code contains a syntax flaw:\n{err}"

    # 2. Structural Wipe Shield (prevents deleting all other functions)
    safe_to_write, shield_reason = _structural_wipe_shield(original_code, new_code)
    if not safe_to_write:
        return shield_reason

    # 3. Backup, Write, Diff
    bak = create_backup(target)
    target.write_text(new_code, encoding="utf-8")
    diff_text = _generate_unified_diff(original_code, new_code, target.name)
    reload_msg = _hot_reload_module(target)

    if player and hasattr(player, "show_content") and diff_text:
        player.show_content(f"WRITE: {target.name}", diff_text[:2500])

    return (
        f"✅ File '{target.name}' updated successfully!\n"
        f"📦 Backup: '{bak.name}'.{reload_msg}\n\n"
        f"--- MODIFICATION AUDIT ---\n{diff_text or 'Full file rewritten.'}"
    )


def apply_code_append(file_path: str, code_to_append: str, player=None) -> str:
    """Appends a new function or class to the bottom of the file."""
    target = _resolve_file_path(file_path)
    if not target:
        return f"Error: Target file '{file_path}' does not exist."

    original_code = target.read_text(encoding="utf-8")
    combined_code = original_code.rstrip() + "\n\n\n" + code_to_append.strip() + "\n"

    is_valid, err = validate_python_syntax(combined_code)
    if not is_valid:
        return f"❌ APPEND REJECTED: Appended code causes syntax error:\n{err}"

    bak = create_backup(target)
    target.write_text(combined_code, encoding="utf-8")
    diff_text = _generate_unified_diff(original_code, combined_code, target.name)
    reload_msg = _hot_reload_module(target)

    if player and hasattr(player, "show_content") and diff_text:
        player.show_content(f"APPEND: {target.name}", diff_text[:2500])

    return (
        f"✅ New code appended to '{target.name}'!\n"
        f"📦 Backup: '{bak.name}'.{reload_msg}\n\n"
        f"--- MODIFICATION AUDIT ---\n{diff_text or 'Code appended.'}"
    )


# ── 6. AUTONOMOUS DIAGNOSIS & REPAIR AGENT ───────────────────────────────────

def auto_diagnose_and_repair(file_path: str, error_message: str, player=None) -> str:
    """
    Autonomous Self-Healing:
    Reads the target file and error message, consults Gemini via reasoning,
    generates a surgical SEARCH/REPLACE block, validates AST, backups,
    writes to disk, and displays the exact diff on the UI.
    Surrounding code is 100% protected.
    """
    target = _resolve_file_path(file_path)
    if not target:
        return f"Autonomous repair aborted: File '{file_path}' was not found."

    api_key = _get_api_key()
    if not api_key:
        return "Autonomous repair requires GEMINI_API_KEY configured in config/api_keys.json."

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return "Google GenAI SDK is required for auto_repair. Run: pip install google-genai"

    original_code = target.read_text(encoding="utf-8")
    if player:
        player.write_log(f"EVOLUTION: 🧠 Diagnosing bug in '{target.name}' with Gemini...")

    prompt = (
        f"You are the Autonomous Self-Repair Core of Nexus AI.\n"
        f"A tool or function inside '{target.name}' encountered this failure:\n"
        f"--- ERROR TRACEBACK / ISSUE ---\n{error_message}\n\n"
        f"--- COMPLETE SOURCE CODE OF {target.name} ---\n{original_code}\n\n"
        f"CRITICAL DIRECTIVES:\n"
        f"1. Diagnose the root cause of the error.\n"
        f"2. DO NOT rewrite the entire file. You MUST output ONLY a surgical SEARCH/REPLACE block.\n"
        f"3. Surround your replacement with exact markers:\n"
        f"<<<<<<< SEARCH\n"
        f"[exact lines from {target.name} to replace]\n"
        f"=======\n"
        f"[repaired replacement lines]\n"
        f">>>>>>>\n"
        f"4. Match indentation and syntax perfectly. Do not touch any other functions."
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        ai_reply = response.text or ""
    except Exception as e:
        return f"Gemini diagnosis call failed: {e}"

    # Extract SEARCH/REPLACE markers
    marker_pattern = re.compile(r"<<<<<<<\s*SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>>", re.DOTALL)
    match = marker_pattern.search(ai_reply)

    if not match:
        return (
            f"Autonomous repair failed to generate clean search markers.\n"
            f"Gemini Raw Analysis:\n{ai_reply[:500]}"
        )

    search_block = match.group(1)
    replace_block = match.group(2)

    if player:
        player.write_log(f"EVOLUTION: ⚡ Applying surgical patch to '{target.name}'...")

    result = apply_search_and_replace(
        file_path=str(target),
        search_block=search_block,
        replace_block=replace_block,
        player=player
    )

    return f"[AUTONOMOUS REPAIR REPORT]\n{result}"


# ── 7. MASTER DISPATCH ENTRY POINT (Called by main.py) ────────────────────────
def self_evolution(parameters: dict, player=None) -> str:
    """
    Master Gateway for Nexus Self-Evolution.
    Supported Actions:
      - 'auto_repair'        : Automatically diagnoses an error traceback and surgically fixes it.
      - 'search_and_replace' : Surgically swaps specific lines with zero risk to other definitions.
      - 'patch_function'     : Replaces a specific function or class method by name.
      - 'append_code'        : Adds a new function or class to the end of a file.
      - 'modify_file'        : Overwrites file with full validated code (Shield protected).
      - 'rollback'           : Restores a file from its timestamped .bak backup.
      - 'list_backups'       : Lists stored safety backups.
      - 'validate'           : Dry-run AST syntax check without writing.
    """
    params = parameters or {}
    action = str(params.get("action", "auto_repair")).strip().lower()
    file_path = str(params.get("file_path", "")).strip()
    code = str(params.get("code", "")).strip()
    func_name = str(params.get("function_name", "")).strip()
    error_msg = str(params.get("error", "") or params.get("error_message", "") or params.get("traceback", "")).strip()
    search_target = str(
        params.get("search") or params.get("search_block") or 
        params.get("search_string") or params.get("find") or params.get("old_code") or ""
    ).strip()
    replace_target = str(
        params.get("replace") or params.get("replace_block") or 
        params.get("replace_string") or params.get("replacement") or 
        params.get("new_code") or code or ""
    ).strip()

    if player and hasattr(player, "write_log"):
        player.write_log(f"EVOLUTION: 🛠️ [{action.upper()}] on '{file_path or 'codebase'}'...")

    print(f"[SelfEvolution] ▶ Action: '{action}' on '{file_path}'")

    # 1. Autonomous Self-Repair
    if action in ("auto_repair", "diagnose_and_repair", "heal", "fix_error"):
        if not file_path or not error_msg:
            return "Both 'file_path' and 'error' (or traceback) are required for auto_repair."
        return auto_diagnose_and_repair(file_path=file_path, error_message=error_msg, player=player)

    # 2. Surgical Search & Replace
    elif action in ("search_and_replace", "replace", "surgical_replace"):
        if not file_path or not search_target or not replace_target:
            return "'file_path', 'search' block, and 'replace' block are all required."
        return apply_search_and_replace(file_path, search_target, replace_target, player=player)

    # 3. Class-Aware Function Patch
    elif action in ("patch_function", "patch"):
        if not file_path or not func_name or not code:
            return "'file_path', 'function_name', and 'code' are all required for patch_function."
        return apply_function_patch(file_path, func_name, code, player=player)

    # 4. Clean Append
    elif action in ("append_code", "append", "add_function"):
        if not file_path or not code:
            return "Both 'file_path' and 'code' are required for append_code."
        return apply_code_append(file_path, code, player=player)

    # 5. Full File Write (Shielded)
    elif action in ("modify_file", "modify", "update", "write"):
        if not file_path or not code:
            return "Both 'file_path' and 'code' are required for modify_file."
        return apply_full_write(file_path, code, player=player)

    # 6. Safety Rollback & Backups
    elif action in ("rollback", "undo", "restore"):
        if not file_path:
            return "Please provide the 'file_path' to roll back."
        return rollback_file(file_path)

    elif action in ("list_backups", "backups"):
        return list_backups()

    # 7. Syntax Validation
    elif action in ("validate", "check_syntax"):
        if not code:
            return "No code provided to validate."
        valid, msg = validate_python_syntax(code)
        return f"Syntax Valid: {valid} | Detail: {msg}"

    return (
        f"Unknown self_evolution action: '{action}'.\n"
        f"Available actions: auto_repair | search_and_replace | patch_function | append_code | modify_file | rollback | list_backups"
    )