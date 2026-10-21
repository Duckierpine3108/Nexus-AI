"""
Actions: Autonomous Single-File Code Assistant (Production 3.8 Edition)
High-precision coding, execution, optimization, and debugging:
  1. Full Gemini 3.8 Flash coding engine with 3.5 Flash-Lite fast fallback
  2. In-memory AST pre-flight verification for Python scripts
  3. Non-blocking subprocess execution (stdin protection against input() deadlocks)
  4. Precise exit-code & traceback-based error classification (no false positives)
  5. Multi-monitor in-memory screen debugging without desktop file clutter
  6. Smart path resolution supporting shortcuts (desktop, downloads, project)
  7. Live dual-channel telemetry (Terminal + Nexus UI cards)
"""

import os
import sys
import json
import re
import time
import ast
import shlex
import tempfile
import subprocess
from pathlib import Path

# ── Paths & Configuration ────────────────────────────────────────────────────
def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR           = get_base_dir()
API_CONFIG_PATH    = BASE_DIR / "config" / "api_keys.json"
DESKTOP            = Path.home() / "Desktop"
MAX_BUILD_ATTEMPTS = 3

MODEL_PRIMARY  = "gemini-3.8-flash"
MODEL_FAST     = "gemini-3.5-flash-lite"

_ACTIVE_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
]

_CACHED_CLIENT = None

def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]

def _get_client():
    global _CACHED_CLIENT
    if _CACHED_CLIENT is not None:
        return _CACHED_CLIENT
    from google import genai
    _CACHED_CLIENT = genai.Client(api_key=_get_api_key())
    return _CACHED_CLIENT

def _ai_call(prompt: str, preferred_model: str = MODEL_PRIMARY) -> str:
    """Resilient generation wrapper with verified fallback models."""
    client = _get_client()
    models_to_try = [preferred_model] + [m for m in _ACTIVE_MODELS if m != preferred_model]
    last_err = None

    for model in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                return (response.text or "").strip()
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str:
                    time.sleep(2 * (attempt + 1))
                    continue
                if "503" in err_str or "overloaded" in err_str:
                    time.sleep(1.5)
                    continue
                if "404" in err_str or "not found" in err_str:
                    break
                break

    raise last_err or RuntimeError("CodeHelper AI generation failed.")

def _clean_code(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text)
    text = re.sub(r"\r?\n?```\s*$", "", text)
    return text.strip()

# ── Path Resolution with Shortcuts ───────────────────────────────────────────
def _resolve_path(raw_path: str, language: str = "python") -> Path:
    ext_map = {
        "python": ".py", "py": ".py",
        "javascript": ".js", "js": ".js",
        "typescript": ".ts", "ts": ".ts",
        "html": ".html", "css": ".css",
        "java": ".java", "cpp": ".cpp", "c": ".c",
        "bash": ".sh", "powershell": ".ps1", "sql": ".sql",
        "json": ".json", "rust": ".rs", "go": ".go",
    }
    if not raw_path:
        ext = ext_map.get((language or "python").lower(), ".py")
        return DESKTOP / f"nexus_script{ext}"

    clean = raw_path.strip().strip('"').strip("'")
    shortcuts = {
        "desktop":   Path.home() / "Desktop",
        "downloads": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "project":   BASE_DIR,
        "nexus":     BASE_DIR,
    }

    norm = clean.replace("\\", "/")
    head, sep, rest = norm.partition("/")
    if sep and head.lower() in shortcuts:
        return (shortcuts[head.lower()] / rest.strip("/")).resolve()

    if clean.lower() in shortcuts:
        return shortcuts[clean.lower()].resolve()

    p = Path(clean).expanduser()
    return p if p.is_absolute() else (DESKTOP / p).resolve()

def _read_file(file_path: str) -> tuple[str, str, Path | None]:
    if not file_path:
        return "", "No file path provided.", None
    p = _resolve_path(file_path)
    if not p.exists():
        return "", f"File not found: {p}", p
    try:
        return p.read_text(encoding="utf-8", errors="replace"), "", p
    except Exception as e:
        return "", f"Could not read file: {e}", p

def _save_file(path: Path, content: str) -> str:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Saved to: {path}"
    except Exception as e:
        return f"Could not save file: {e}"

def _preview(code: str, lines: int = 12) -> str:
    all_lines = code.splitlines()
    preview = "\n".join(all_lines[:lines])
    suffix = f"\n... ({len(all_lines) - lines} more lines)" if len(all_lines) > lines else ""
    return preview + suffix

# ── High-Accuracy Error Verification (No False Positives) ────────────────────
def _has_error(returncode: int, output: str, stderr: str) -> bool:
    if returncode != 0:
        return True
    combined = (output + "\n" + stderr).lower()
    error_patterns = [
        "traceback (most recent call last):",
        "syntaxerror:", "nameerror:", "typeerror:", "valueerror:",
        "importerror:", "modulenotfounderror:", "attributeerror:",
        "zerodivisionerror:", "indexerror:", "keyerror:", "runtimeerror:",
        "uncaught exception", "referenceerror:", "fatal error"
    ]
    return any(p in combined for p in error_patterns)

# ── AST Syntax Pre-flight Linting ────────────────────────────────────────────
def _validate_python_syntax(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"

# ── Safe Process Execution ───────────────────────────────────────────────────
def _run_file(path: Path, args: list | str = None, timeout: int = 30) -> tuple[int, str]:
    interpreters = {
        ".py":  [sys.executable],
        ".js":  ["node"],
        ".ts":  ["ts-node"],
        ".sh":  ["bash"],
        ".ps1": ["powershell", "-ExecutionPolicy", "Bypass", "-File"],
        ".rb":  ["ruby"],
        ".php": ["php"],
    }
    interp = interpreters.get(path.suffix.lower())
    if not interp:
        return 1, f"No interpreter configured for extension '{path.suffix}'."

    # Parse args cleanly with shlex if string
    cli_args = []
    if isinstance(args, str) and args.strip():
        cli_args = shlex.split(args, posix=(os.name != "nt"))
    elif isinstance(args, list):
        cli_args = [str(a) for a in args]

    cmd = interp + [str(path)] + cli_args
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(path.parent),
            stdin=subprocess.DEVNULL,  # Prevent input() hangs
        )
        stdout = res.stdout.strip()
        stderr = res.stderr.strip()

        combined = []
        if stdout: combined.append(f"STDOUT:\n{stdout}")
        if stderr: combined.append(f"STDERR:\n{stderr}")

        output_str = "\n\n".join(combined) if combined else "Executed successfully with zero console output."
        return res.returncode, output_str

    except subprocess.TimeoutExpired:
        return 1, f"Process timed out after {timeout} seconds (execution safety ceiling)."
    except FileNotFoundError:
        return 1, f"Interpreter executable '{interp[0]}' not found on system PATH."
    except Exception as e:
        return 1, f"Execution failure: {e}"

# ── Intent Auto-Detection ────────────────────────────────────────────────────
def _detect_intent(description: str, file_path: str, code: str) -> str:
    desc = (description or "").strip().lower()
    path_exists = bool(file_path) and _resolve_path(file_path).exists()

    # Fast heuristic checks (saves API roundtrip)
    if any(k in desc for k in ("run", "execute", "launch", "start")):
        return "run"
    if any(k in desc for k in ("explain", "what does this do", "understand", "read")):
        return "explain"
    if any(k in desc for k in ("optimize", "refactor", "speed up", "clean up")):
        return "optimize"
    if any(k in desc for k in ("fix", "debug", "repair", "error")):
        return "screen_debug" if "screen" in desc else "edit"
    if any(k in desc for k in ("edit", "modify", "change", "update", "add to")):
        return "edit"
    if any(k in desc for k in ("build", "create and test", "iterate")):
        return "build"
    if any(k in desc for k in ("write", "create", "make", "generate", "code")):
        return "write"

    if path_exists:
        return "edit" if desc else "explain"
    if code:
        return "explain"
    return "write"

# ── Action Implementations ───────────────────────────────────────────────────
def _write_action(description: str, language: str, output_path: str, player=None, raw_code: str = "") -> str:
    lang = language or "python"
    target_path = _resolve_path(output_path, lang)

    # If the AI already wrote the code directly, save it immediately!
    if raw_code and not description:
        clean = _clean_code(raw_code)
        _save_file(target_path, clean)
        return f"Code saved directly to: {target_path}\n\nPreview:\n{_preview(clean)}"

    if not description:
        return "Please describe what script you want me to write, sir."

    lang = language or "python"
    target_path = _resolve_path(output_path, lang)

    if player and hasattr(player, "write_log"):
        player.write_log(f"CODE: 📝 Generating {lang.upper()} script: '{target_path.name}'...")

    prompt = f"""You are a Senior {lang} Developer using Gemini 3.8 Flash.
Write clean, modern, fully functional, production-ready {lang} code for this requirement:

Requirement: {description}

Directives:
- Output ONLY raw executable code. Zero markdown, zero backticks, zero preamble.
- Add concise, professional comments explaining non-trivial logic.
- Include proper error handling and input validation.
- If Python, include `if __name__ == '__main__':` guard.

Code:"""

    code = _clean_code(_ai_call(prompt, MODEL_PRIMARY))

    # In-memory AST syntax verification for Python
    if lang.lower() in ("python", "py"):
        valid, err = _validate_python_syntax(code)
        if not valid:
            print(f"[CodeHelper] ⚠️ AST syntax error ({err}). Auto-correcting...")
            fix_prompt = f"Fix this Python syntax error ({err}) in the code below. Return ONLY corrected code:\n{code}"
            code = _clean_code(_ai_call(fix_prompt, MODEL_PRIMARY))

    _save_file(target_path, code)
    print(f"[CodeHelper] ✅ Written: {target_path}")

    return f"Code written successfully.\nSaved to: {target_path}\n\nPreview:\n{_preview(code)}"

def _edit_action(file_path: str, instruction: str, player=None) -> str:
    if not file_path:
        return "Please provide the file path to edit, sir."
    if not instruction:
        return "Please describe the changes you want made, sir."

    content, err, p = _read_file(file_path)
    if err:
        return err

    if player and hasattr(player, "write_log"):
        player.write_log(f"CODE: 🔧 Editing file '{p.name}'...")

    lang = p.suffix.lstrip(".") or "code"
    prompt = f"""You are a Lead Software Engineer. Apply the requested modification to the existing code.

Requested Change: {instruction}

Original File ({p.name}):
{content}

Directives:
- Output ONLY the complete, updated, ready-to-run code. Zero markdown backticks.
- Preserve all existing correct functionality and formatting.
- Fix any related imports or method signatures affected by this change.

Updated Code:"""

    edited = _clean_code(_ai_call(prompt, MODEL_PRIMARY))

    if lang.lower() in ("python", "py"):
        valid, syn_err = _validate_python_syntax(edited)
        if not valid:
            fix_prompt = f"Fix this Python syntax error ({syn_err}) in the code below. Return ONLY valid code:\n{edited}"
            edited = _clean_code(_ai_call(fix_prompt, MODEL_PRIMARY))

    _save_file(p, edited)
    print(f"[CodeHelper] ✅ Edited: {p}")
    return f"File updated successfully.\nSaved to: {p}\n\nPreview:\n{_preview(edited)}"

def _explain_action(file_path: str, code: str, player=None) -> str:
    p = None
    if file_path and not code:
        code, err, p = _read_file(file_path)
        if err:
            return err

    if not code:
        return "Please provide code or a file path to explain, sir."

    if player and hasattr(player, "write_log"):
        player.write_log(f"CODE: 🧠 Explaining logic ({p.name if p else 'snippet'})...")

    prompt = f"""Explain this code with executive clarity:
1. Core Objective: What does this code achieve?
2. Architecture & Flow: How does data move through it?
3. Edge Cases / Dependencies: Notable libraries or safety precautions.

Be concise and direct (3-5 bullet points).

Code:
{code[:6000]}"""

    return _ai_call(prompt, MODEL_FAST)

def _run_action(file_path: str, args: list | str, timeout: int, player=None) -> str:
    if not file_path:
        return "Please provide a file path to execute, sir."

    p = _resolve_path(file_path)
    if not p.exists():
        return f"File does not exist: {p}"

    if player and hasattr(player, "write_log"):
        player.write_log(f"CODE: 🚀 Running '{p.name}' (timeout={timeout}s)...")

    retcode, output = _run_file(p, args, timeout)
    status = "SUCCESS" if retcode == 0 else f"FAILED (exit code {retcode})"
    return f"Execution Result: {status}\n\n{output}"

def _optimize_action(file_path: str, code: str, language: str, output_path: str, player=None) -> str:
    p = None
    if file_path and not code:
        code, err, p = _read_file(file_path)
        if err:
            return err

    if not code:
        return "Please provide code or a file path to optimize, sir."

    lang = language or (p.suffix.lstrip(".") if p else "python")
    target = p or _resolve_path(output_path, lang)

    if player and hasattr(player, "write_log"):
        player.write_log(f"CODE: ⚡ Optimizing {lang.upper()} code for performance & clean architecture...")

    prompt = f"""You are a Principal Software Engineer and Performance Architect.
Optimize the following {lang} code for:
1. Execution Performance: Lower algorithmic time and memory complexity.
2. Code Cleanliness: Modern idioms, strict typing, dead code removal.
3. Resilience: Solid edge-case handling.

Return ONLY the complete optimized code. Zero markdown, zero explanation.

Original Code:
{code[:7000]}

Optimized Code:"""

    optimized = _clean_code(_ai_call(prompt, MODEL_PRIMARY))

    if lang.lower() in ("python", "py"):
        valid, syn_err = _validate_python_syntax(optimized)
        if not valid:
            fix_prompt = f"Fix this Python syntax error ({syn_err}) in the code below. Return ONLY valid code:\n{optimized}"
            optimized = _clean_code(_ai_call(fix_prompt, MODEL_PRIMARY))

    _save_file(target, optimized)
    orig_lines = len(code.splitlines())
    opt_lines = len(optimized.splitlines())
    diff = orig_lines - opt_lines
    sign = "−" if diff > 0 else "+"

    return f"Optimization complete.\nSaved to: {target}\nLine Metrics: {orig_lines} → {opt_lines} ({sign}{abs(diff)} lines)\n\nPreview:\n{_preview(optimized)}"

def _build_action(description: str, language: str, output_path: str, args: list | str, timeout: int, speak=None, player=None) -> str:
    if not description:
        return "Please describe what script you want me to build and verify, sir."

    lang = language or "python"
    target_path = _resolve_path(output_path, lang)

    if player and hasattr(player, "write_log"):
        player.write_log(f"CODE: 🏗️ Autonomous Build & Test loop initiated: '{target_path.name}'")

    # Step 1: Initial Write
    prompt = f"""You are an elite {lang} developer. Write a complete, robust, runnable {lang} script.
Goal: {description}

Return ONLY raw code without markdown backticks:"""

    code = _clean_code(_ai_call(prompt, MODEL_PRIMARY))
    _save_file(target_path, code)

    # Step 2: Iterative Self-Repair Loop
    last_output = ""
    for attempt in range(1, MAX_BUILD_ATTEMPTS + 1):
        if player and hasattr(player, "write_log"):
            player.write_log(f"CODE: 🔄 Verifying execution (attempt {attempt}/{MAX_BUILD_ATTEMPTS})...")

        retcode, last_output = _run_file(target_path, args, timeout)

        if not _has_error(retcode, last_output, ""):
            msg = f"Build succeeded in {attempt} attempt(s).\nSaved to: {target_path}\n\nExecution Output:\n{last_output}"
            if speak: speak(f"Script verified and working, sir.")
            return msg

        if attempt == MAX_BUILD_ATTEMPTS:
            break

        # Step 3: Self-Correction Prompt
        fix_prompt = f"""You are an expert debugger. Fix this {lang} script.
Objective: {description}

Execution Output / Traceback:
{last_output[:2500]}

Current Code:
{code}

Return ONLY the corrected, complete {lang} code:"""

        code = _clean_code(_ai_call(fix_prompt, MODEL_PRIMARY))
        _save_file(target_path, code)

    fail_msg = f"Build could not be fully verified after {MAX_BUILD_ATTEMPTS} attempts.\nLast script saved at: {target_path}\n\nLast Output:\n{last_output[:800]}"
    if speak: speak("Build loop concluded with errors, sir.")
    return fail_msg

def _screen_debug_action(description: str, file_path: str, player=None, speak=None) -> str:
    if player and hasattr(player, "write_log"):
        player.write_log("CODE: 📸 Capturing screen error for visual diagnosis...")

    # High-Performance In-Memory Screen Capture via mss
    img_bytes = None
    try:
        import mss
        import mss.tools
        with mss.mss() as sct:
            monitors = sct.monitors
            target = monitors[1] if len(monitors) > 1 else monitors[0]
            shot = sct.grab(target)
            img_bytes = mss.tools.to_png(shot.rgb, shot.size)
    except Exception as e:
        return f"Screen capture failed: {e}. Please ensure mss is installed."

    file_content = ""
    target_p = None
    if file_path:
        file_content, _, target_p = _read_file(file_path)

    from google.genai import types
    client = _get_client()

    user_query = description or "Identify any code, terminal, or runtime error on screen and explain how to fix it."
    context = f"\n\nAssociated File Content ({target_p.name}):\n```{file_content[:3500]}```" if file_content else ""

    analysis_prompt = f"""You are a Principal Software Debugger analyzing a visual screen capture.

Task: {user_query}{context}

Directives:
1. Identify the exact error, stack trace, or buggy visual state on screen.
2. Quote the exact line numbers or exception messages visible.
3. Provide a clear diagnosis and the exact corrected code.
"""

    try:
        response = client.models.generate_content(
            model=MODEL_PRIMARY,
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                analysis_prompt
            ]
        )
        analysis = (response.text or "").strip()

        # Auto-patch local file if code block detected and target file provided
        if target_p and target_p.exists():
            match = re.search(r"```(?:\w+)?\r?\n(.*?)```", analysis, re.DOTALL)
            if match:
                patched = match.group(1).strip()
                _save_file(target_p, patched)
                analysis += f"\n\n✅ Automatically patched and saved: {target_p.name}"

        return analysis
    except Exception as e:
        return f"Visual screen debugging failed: {e}"

# ── Central Action Dispatcher ────────────────────────────────────────────────
def code_helper(
    parameters: dict | None = None,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """
    Unified entry point called from main.py.
    Matches schema in TOOL_DECLARATIONS.
    """
    p = parameters or {}
    action = str(p.get("action", "auto")).lower().strip()
    description = str(p.get("description", "")).strip()
    language = str(p.get("language", "python")).strip()
    output_path = str(p.get("output_path", "")).strip()
    file_path = str(p.get("file_path", "")).strip()
    code = str(p.get("code", "")).strip()
    args = p.get("args", [])
    timeout = int(p.get("timeout", 30))

    if action == "auto":
        action = _detect_intent(description, file_path, code)
        print(f"[CodeHelper] 🤖 Auto-routed action to: '{action}'")

    if action == "write":
        return _write_action(description, language, output_path, player, raw_code=code)

    elif action == "edit":
        return _edit_action(file_path, description or p.get("instruction", ""), player)

    elif action == "explain":
        return _explain_action(file_path, code, player)

    elif action == "run":
        return _run_action(file_path, args, timeout, player)

    elif action == "build":
        return _build_action(description, language, output_path, args, timeout, speak, player)

    elif action == "optimize":
        return _optimize_action(file_path, code, language, output_path, player)

    elif action == "screen_debug":
        return _screen_debug_action(description, file_path, player, speak)

    else:
        return f"Unknown code_helper action: '{action}'. Available: write, edit, explain, run, build, optimize, screen_debug."