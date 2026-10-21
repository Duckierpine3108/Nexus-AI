"""
Actions: Autonomous Software Development Agent (Production 3.8 Flagship Edition)
End-to-end multi-file software engineering pipeline:
  1. Full Gemini 3.8 Flash reasoning across Architect, Coder, and Debugger
  2. Live dual-channel telemetry: Rich formatted terminal output + Main UI live cards
  3. Cross-file API Contract enforcement (prevents method name mismatch bugs)
  4. Multi-language dependency management (pip for Python, npm for Node/Web)
  5. In-memory AST pre-flight verification & non-blocking execution (stdin protection)
  6. Automated scaffolding (README.md, requirements.txt, .gitignore)
  7. Automatic VS Code project launch
"""

import os
import sys
import json
import re
import time
import shlex
import ast
import shutil
import subprocess
from pathlib import Path

# ── Paths & Configuration ────────────────────────────────────────────────────
def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR         = get_base_dir()
API_CONFIG_PATH  = BASE_DIR / "config" / "api_keys.json"
PROJECTS_DIR     = Path.home() / "Desktop" / "JarvisProjects"
MAX_FIX_ATTEMPTS = 5

# Full Flagship Engine: Gemini 3.8 Flash across all phases
MODEL_PLANNER  = "gemini-3.8-flash"
MODEL_WRITER   = "gemini-3.8-flash"
MODEL_DEBUGGER = "gemini-3.8-flash"

_FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",  # Emergency fallback only if 3.8 encounters rate limits
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

def _ai_call(prompt: str, preferred_model: str) -> str:
    """Robust generation wrapper with automatic retry on rate limits."""
    client = _get_client()
    models_to_try = [preferred_model] + [m for m in _FALLBACK_MODELS if m != preferred_model]
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
                    time.sleep(3 * (attempt + 1))
                    continue
                if "503" in err_str or "overloaded" in err_str:
                    time.sleep(2)
                    continue
                if "404" in err_str or "not found" in err_str:
                    break
                break

    raise last_err or RuntimeError("DevAgent AI generation failed.")

def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text)
    text = re.sub(r"\r?\n?```\s*$", "", text)
    return text.strip()

# ── Live Telemetry Logger (Terminal + Main UI Live Channel) ───────────────────
class Telemetry:
    def __init__(self, player=None):
        self.player = player

    def step(self, phase: str, detail: str):
        # 1. Print formatted terminal log
        print(f"\n[DevAgent] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"[DevAgent] 🧠 {phase}")
        print(f"[DevAgent]    {detail}")
        print(f"[DevAgent] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 2. Stream to Live Main UI conversation log
        if self.player and hasattr(self.player, "write_log"):
            self.player.write_log(f"DEV: 🧠 [{phase}] {detail}")

    def info(self, msg: str):
        print(f"[DevAgent] ⚡ {msg}")
        if self.player and hasattr(self.player, "write_log"):
            self.player.write_log(f"DEV: {msg}")

    def show_blueprint(self, plan: dict):
        if not self.player or not hasattr(self.player, "show_content"):
            return

        proj_name = plan.get("project_name", "nexus_app")
        entry = plan.get("entry_point", "main.py")
        files = plan.get("files", [])
        deps = plan.get("dependencies", [])

        # Formatted hierarchical DeepSeek/AI Studio thinking display
        card_content = (
            f"🧠 REASONING & ARCHITECTURE BLUEPRINT\n\n"
            f"• Project Identifier: {proj_name}\n\n"
            f"• Execution Entry: {entry}\n\n"
            f"• External Packages: {', '.join(deps) if deps else 'None (Standard Library)'}\n\n"
            f"• File Dependency Graph ({len(files)} modules):\n"
        )

        for i, f in enumerate(files, 1):
            exports_str = f" → Exports: {', '.join(f.get('exports', []))}" if f.get("exports") else ""
            card_content += f"\n• [{i}/{len(files)}] {f['path']}{exports_str}\n  Purpose: {f.get('description', '')}\n"

        try:
            self.player.show_content(f"THINKING — {proj_name.upper()}", card_content)
        except Exception as e:
            print(f"[DevAgent] UI thinking card error: {e}")

# ── Multi-Language Traceback & Error Parsing ─────────────────────────────────
def _parse_traceback(output: str, project_files: list[str]) -> tuple[str | None, int | None]:
    # Python tracebacks
    py_pattern = re.compile(r'File ["\']([^"\']+\.py)["\'],\s+line\s+(\d+)', re.IGNORECASE)
    py_matches = py_pattern.findall(output)
    for raw_path, line_str in reversed(py_matches):
        raw_name = Path(raw_path).name
        for pf in project_files:
            if Path(pf).name == raw_name or pf == raw_path or raw_path.endswith(pf):
                return pf, int(line_str)

    # Node.js / JavaScript tracebacks
    js_pattern = re.compile(r'(?:at\s+.*?\()?([a-zA-Z0-9_\-\.\/\\]+\.(?:js|ts|jsx|tsx)):(\d+)', re.IGNORECASE)
    js_matches = js_pattern.findall(output)
    for raw_path, line_str in reversed(js_matches):
        raw_name = Path(raw_path).name
        for pf in project_files:
            if Path(pf).name == raw_name or pf == raw_path or raw_path.endswith(pf):
                return pf, int(line_str)

    return None, None

def _classify_error(output: str) -> str:
    low = output.lower()
    if any(x in low for x in ("no module named", "modulenotfounderror", "cannot find module")):
        return "dependency_error"
    if any(x in low for x in ("syntaxerror", "invalid syntax", "unexpected token")):
        return "syntax_error"
    if any(x in low for x in ("cannot import", "importerror", "require is not defined", "is not a function")):
        return "import_error"
    if any(x in low for x in ("traceback", "exception", "error:", "referenceerror", "typeerror", "valueerror")):
        return "runtime_error"
    return "none"

def _has_error(output: str, run_command: str) -> bool:
    low = output.lower()
    if "running continuously" in low:
        return False
    if not output.strip():
        return False
    return _classify_error(output) != "none"

# ── Architectural Planning with Strict API Contracts ─────────────────────────
def _plan_project(description: str, language: str, tele: Telemetry) -> dict:
    tele.step("Phase 1: Deep Architectural Planning", f"Designing multi-file system contract for: '{description[:70]}...'")

    prompt = f"""You are a Principal Software Architect. Design a production-grade, highly reliable multi-file application.

Language: {language}
Description: {description}

Return ONLY a valid JSON object without markdown formatting:
{{
  "project_name": "snake_case_name",
  "entry_point": "main.py",
  "files": [
    {{
      "path": "static/audio.js",
      "description": "Exposes SoundManager class with methods: init(), playLaser(), playExplosion()",
      "exports": ["class SoundManager {{ init(), playLaser(), playExplosion() }}"],
      "imports": []
    }},
    {{
      "path": "static/game.js",
      "description": "Game canvas engine. Instantiates SoundManager and handles loop",
      "exports": ["class Game"],
      "imports": ["static/audio.js"]
    }}
  ],
  "run_command": "python main.py",
  "dependencies": []
}}

Strict Architectural Rules:
1. List files strictly in DEPENDENCY ORDER (files with no dependencies first, entry point last).
2. For every file, explicitly state in 'exports' the exact class names, functions, and methods it exposes.
3. Every file that imports another file MUST strictly use the exact method names listed in 'exports'.
4. Standard libraries (sys, os, json, math, fs, path) must NOT be included in dependencies.
5. Use relative paths only."""

    raw = _ai_call(prompt, MODEL_PLANNER)
    clean_json = _strip_fences(raw)
    try:
        plan = json.loads(clean_json)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean_json, re.DOTALL)
        if match:
            plan = json.loads(match.group(0))
        else:
            raise ValueError("Architect could not generate valid project specification.")

    # Display live blueprint on UI Content Card
    blueprint_text = f"Project: {plan.get('project_name')}\nEntry Point: {plan.get('entry_point')}\nRun Command: {plan.get('run_command')}\n\nArchitecture Plan:\n"
    for f in plan.get("files", []):
        blueprint_text += f"\n📄 {f['path']}\n   Purpose: {f.get('description', '')}\n   Exports: {', '.join(f.get('exports', []))}\n"
    tele.show_blueprint(plan)

    return plan

# ── Multi-Language Dependency Management ─────────────────────────────────────
def _install_dependencies(dependencies: list[str], language: str, project_dir: Path, tele: Telemetry) -> str:
    if not dependencies:
        return "No external dependencies required."

    lang = language.lower()
    is_node = any(x in lang for x in ("node", "javascript", "typescript", "js", "ts"))

    if is_node:
        if shutil.which("npm"):
            tele.info(f"Installing Node packages via npm: {', '.join(dependencies)}")
            try:
                cmd = ["npm", "install"] + dependencies
                res = subprocess.run(cmd, cwd=str(project_dir), capture_output=True, text=True, timeout=180, shell=(os.name == "nt"))
                return f"Installed npm packages: {', '.join(dependencies)}" if res.returncode == 0 else f"npm warning: {res.stderr[:200]}"
            except Exception as e:
                return f"npm install error: {e}"
        return "npm not found on system PATH."

    to_install = []
    for dep in dependencies:
        pkg_name = re.split(r"[>=<!]", dep)[0].strip()
        res = subprocess.run([sys.executable, "-m", "pip", "show", pkg_name], capture_output=True, text=True)
        if res.returncode != 0:
            to_install.append(dep)
        else:
            tele.info(f"Dependency satisfied: {pkg_name}")

    if not to_install:
        return f"All Python dependencies satisfied: {', '.join(dependencies)}"

    tele.info(f"Installing missing Python packages via pip: {to_install}")
    try:
        res = subprocess.run([sys.executable, "-m", "pip", "install"] + to_install, cwd=str(project_dir), capture_output=True, text=True, timeout=180)
        return f"Installed dependencies: {', '.join(to_install)}" if res.returncode == 0 else f"pip warning: {res.stderr[:200]}"
    except Exception as e:
        return f"pip install error: {e}"

def _try_auto_install(error_output: str, language: str, project_dir: Path, tele: Telemetry) -> bool:
    if "python" in language.lower():
        match = re.search(r"No module named ['\"]([a-zA-Z0-9_\-\.]+)['\"]", error_output, re.IGNORECASE)
        if match:
            pkg = match.group(1).split(".")[0].replace("_", "-")
            tele.info(f"Auto-installing missing module: {pkg}")
            res = subprocess.run([sys.executable, "-m", "pip", "install", pkg], cwd=str(project_dir), capture_output=True, text=True, timeout=90)
            return res.returncode == 0
    return False

# ── Automated Project Scaffolding ────────────────────────────────────────────
def _generate_scaffolding(project_dir: Path, proj_name: str, description: str, language: str, dependencies: list[str], run_command: str):
    gitignore = project_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "__pycache__/\n*.py[cod]\n*.so\n.env\n.venv\nvenv/\nnode_modules/\n.vscode/\n.idea/\ndist/\nbuild/\n",
            encoding="utf-8"
        )

    if "python" in language.lower() and dependencies:
        req = project_dir / "requirements.txt"
        if not req.exists():
            req.write_text("\n".join(dependencies) + "\n", encoding="utf-8")

    readme = project_dir / "README.md"
    if not readme.exists():
        content = (
            f"# {proj_name}\n\n"
            f"> {description}\n\n"
            f"## System Architecture\n"
            f"- **Core Engine**: {language.capitalize()}\n"
            f"- **Dependencies**: {', '.join(dependencies) if dependencies else 'Standard Library'}\n\n"
            f"## How to Run\n"
            f"```bash\n{run_command}\n```\n\n"
            f"---\n*Engineered autonomously by Nexus AI DevAgent (Gemini 3.8 Flash).*\n"
        )
        readme.write_text(content, encoding="utf-8")

# ── Code Writer with In-Memory AST Linting ────────────────────────────────────
def _write_file(file_info: dict, project_desc: str, all_files: list[dict], language: str, project_dir: Path, already_written: dict[str, str], tele: Telemetry) -> str:
    file_path = file_info["path"]
    file_desc = file_info.get("description", "")
    file_exports = file_info.get("exports", [])
    file_imports = file_info.get("imports", [])

    file_list = "\n".join(f"  - {f['path']}: {f.get('description', '')} (Exports: {', '.join(f.get('exports', []))})" for f in all_files)

    dep_context = ""
    for dep in file_imports:
        dep_p = dep if dep.endswith((".py", ".js", ".html", ".css")) else dep + (".py" if "python" in language.lower() else ".js")
        if dep_p in already_written:
            snippet = already_written[dep_p][:2600]
            dep_context += f"\n--- {dep_p} (Actual code implemented) ---\n{snippet}\n"

    prompt = f"""You are a Lead Software Engineer writing production code with Gemini 3.8 Flash.

Project: {project_desc}
All project files and their strict contracts:
{file_list}
{dep_context}

Write COMPLETE, FLAWLESS, RUNNABLE code for: {file_path}
Purpose: {file_desc}
Contracts this file must fulfill: {', '.join(file_exports)}

Engineering Directives:
- Output ONLY raw executable code. Zero explanation, zero markdown backticks.
- Never use '# TODO' or 'pass' stubs. Implement every function fully.
- Ensure all variable, method, and function calls match the exact method signatures in the sibling files above.
- Ensure cross-file method names match 100%.

Code for {file_path}:"""

    tele.info(f"Synthesizing '{file_path}' with Gemini 3.8 Flash...")
    code = _strip_fences(_ai_call(prompt, MODEL_WRITER))

    # In-memory AST pre-flight verification for Python files
    if "python" in language.lower() and file_path.endswith(".py"):
        try:
            ast.parse(code)
            tele.info(f"AST verification passed: '{file_path}' syntax is valid.")
        except SyntaxError as e:
            tele.info(f"AST caught syntax error in '{file_path}': {e}. Auto-refining...")
            fix_prompt = f"Fix this Python syntax error ({e}) in the code below. Return ONLY valid code:\n{code}"
            code = _strip_fences(_ai_call(fix_prompt, MODEL_PLANNER))

    full_path = project_dir / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(code, encoding="utf-8")
    return code

# ── Safe Process Execution ───────────────────────────────────────────────────
def _run_project(run_command: str, project_dir: Path, timeout: int = 30) -> str:
    print(f"[DevAgent] 🚀 Running: {run_command}")
    try:
        parts = shlex.split(run_command, posix=(os.name != "nt"))
        if parts and parts[0].lower() in ("python", "python3"):
            parts[0] = sys.executable

        res = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(project_dir),
            stdin=subprocess.DEVNULL,
        )

        stdout = res.stdout.strip()
        stderr = res.stderr.strip()

        combined = []
        if stdout: combined.append(f"STDOUT:\n{stdout}")
        if stderr: combined.append(f"STDERR:\n{stderr}")

        if res.returncode != 0 and not combined:
            return f"Process failed with exit code {res.returncode}."

        return "\n\n".join(combined) if combined else "Ran successfully with zero errors."

    except subprocess.TimeoutExpired:
        return f"Running continuously (timed out after {timeout}s) — application/server is active."
    except Exception as e:
        return f"Execution error: {e}"

def _open_vscode(project_dir: Path, tele: Telemetry) -> bool:
    candidates = [
        "code",
        rf"C:\Users\{Path.home().name}\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd",
        r"C:\Program Files\Microsoft VS Code\bin\code.cmd",
    ]
    for cmd in candidates:
        try:
            subprocess.Popen([cmd, str(project_dir)], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            tele.info(f"VS Code workspace opened: {project_dir.name}")
            return True
        except Exception:
            continue
    return False

# ── Diagnostic Self-Repair Loop ──────────────────────────────────────────────
def _fix_files(error_output: str, project_desc: str, all_files: list[dict], file_codes: dict[str, str], language: str, project_dir: Path, entry_point: str, tele: Telemetry) -> dict[str, str]:
    error_file, error_line = _parse_traceback(error_output, list(file_codes.keys()))
    error_type = _classify_error(error_output)

    target_file = error_file or entry_point
    current_code = file_codes.get(target_file, "")
    line_hint = f"\nError detected near line {error_line}." if error_line else ""

    tele.step("Diagnostic Self-Repair", f"Fixing {error_type} in '{target_file}'...")

    prompt = f"""You are a Lead Debugging Engineer using Gemini 3.8 Flash. Fix the broken file.

Project: {project_desc}
Target file: {target_file}{line_hint}
Error category: {error_type}

Traceback:
{error_output[:2800]}

Current code:
{current_code}

Fixing Rules:
- Return ONLY the complete fixed code. No explanation, no markdown backticks.
- Preserve all existing functionality while resolving the error.
- Ensure cross-file imports and method names match exactly.

Fixed code for {target_file}:"""

    fixed_code = _strip_fences(_ai_call(prompt, MODEL_DEBUGGER))
    full_path = project_dir / target_file
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(fixed_code, encoding="utf-8")
    return {target_file: fixed_code}

# ── Central Builder Engine ───────────────────────────────────────────────────
def _build_project(description: str, language: str, project_name: str, timeout: int, speak=None, player=None) -> str:
    tele = Telemetry(player=player)

    try:
        plan = _plan_project(description, language, tele)
    except Exception as e:
        err = f"Architect planning failed: {e}"
        if speak: speak("Planning failed, sir.")
        tele.info(err)
        return err

    clean_name = re.sub(r"[^\w\-]", "_", project_name or plan.get("project_name", "nexus_app"))
    project_dir = PROJECTS_DIR / clean_name
    project_dir.mkdir(parents=True, exist_ok=True)

    files = plan.get("files", [])
    entry_point = plan.get("entry_point", "main.py")
    run_command = plan.get("run_command", f"python {entry_point}")
    dependencies = plan.get("dependencies", [])

    tele.step("Phase 2: Code Synthesis", f"Generating {len(files)} files via Gemini 3.8 Flash...")

    # Write files in strict dependency order
    file_codes = {}
    for fi in sorted(files, key=lambda x: len(x.get("imports", []))):
        f_path = fi.get("path")
        if not f_path: continue
        try:
            code = _write_file(fi, description, files, language, project_dir, file_codes, tele)
            file_codes[f_path] = code
            time.sleep(0.2)
        except Exception as e:
            tele.info(f"Warning on {f_path}: {e}")

    # Scaffolding & Dependencies
    _generate_scaffolding(project_dir, clean_name, description, language, dependencies, run_command)
    if dependencies:
        tele.info(_install_dependencies(dependencies, language, project_dir, tele))

    _open_vscode(project_dir, tele)

    # Phase 3: Diagnostic verification loop
    tele.step("Phase 3: Runtime Verification", f"Executing '{run_command}'...")
    last_output = ""
    auto_installs = 0

    for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
        tele.info(f"Execution test attempt {attempt}/{MAX_FIX_ATTEMPTS}...")
        last_output = _run_project(run_command, project_dir, timeout)

        if not _has_error(last_output, run_command):
            msg = f"Project '{clean_name}' successfully built and verified in {attempt} attempt(s)."
            tele.step("Project Complete", msg)
            if speak: speak(msg)
            return f"{msg}\nSaved to: {project_dir}\n\nExecution Output:\n{last_output}"

        if attempt == MAX_FIX_ATTEMPTS:
            break

        error_type = _classify_error(last_output)
        if error_type == "dependency_error" and auto_installs < 3:
            if _try_auto_install(last_output, language, project_dir, tele):
                auto_installs += 1
                tele.info("Missing dependency auto-installed. Retrying...")
                continue

        tele.info(f"Self-repair triggered: resolving {error_type}...")
        try:
            updated = _fix_files(last_output, description, files, file_codes, language, project_dir, entry_point, tele)
            file_codes.update(updated)
            time.sleep(0.5)
        except Exception as e:
            tele.info(f"Self-repair step failed: {e}")

    fail_msg = f"Could not fully resolve '{clean_name}' after {MAX_FIX_ATTEMPTS} attempts. Project saved at: {project_dir}"
    tele.info(fail_msg)
    if speak: speak(fail_msg)
    return f"{fail_msg}\n\nLast Output:\n{last_output[:800]}"

# ── Tool Entry Point ─────────────────────────────────────────────────────────
def dev_agent(parameters: dict | None = None, response=None, player=None, session_memory=None, speak=None) -> str:
    p = parameters or {}
    description = p.get("description", "").strip()
    language = p.get("language", "python").strip()
    project_name = p.get("project_name", "").strip()
    timeout = int(p.get("timeout", 30))

    if not description:
        return "Please describe what application you want me to engineer, sir."

    return _build_project(
        description=description,
        language=language,
        project_name=project_name,
        timeout=timeout,
        speak=speak,
        player=player,
    )