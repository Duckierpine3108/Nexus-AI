# ==============================================================================
#            ACTIONS: ENTERPRISE MULTI-STAGE REASONING CORE (v5.0)
#          Dual-Pass Agentic Reflection Engine via gemini-3.5-flash-lite
# ==============================================================================

import json
import os
import re
import sys
from pathlib import Path
from google import genai
from google.genai import types

def _get_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    p = Path(__file__).resolve().parent
    if p.name == "actions":
        return p.parent
    return p

ROOT_DIR = _get_project_root()
CONFIG_PATH = ROOT_DIR / "config" / "api_keys.json"

def _get_api_key() -> str:
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("gemini_api_key", "").strip()
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "").strip()

def _get_thinking_settings() -> tuple[int, str]:
    """Reads thinking level from config and returns (token_budget, label)."""
    try:
        level = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("thinking_level", "medium").lower()
        if level in ("low", "fast", "lite"):
            return 1024, "FAST REFLECTION"
        elif level in ("high", "deep"):
            return 8192, "DEEP ENTERPRISE"
        else:
            return 4096, "BALANCED ARCHITECT"
    except Exception:
        return 2048, "BALANCED ARCHITECT"

def _resolve_file_context(file_path_raw: str) -> str:
    """Safely extracts content if deep_think was asked to analyze a local file."""
    if not file_path_raw:
        return ""
    clean = file_path_raw.strip().replace("\\", "/")
    target = (ROOT_DIR / clean).resolve()
    if not (target.exists() and target.is_file()):
        target = (ROOT_DIR / "actions" / clean).resolve()
    if target.exists() and target.is_file():
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            return f"\n\n--- LOCAL FILE AUDIT ({target.name}) ---\n{content[:14000]}\n--- END FILE AUDIT ---\n"
        except Exception:
            pass
    return ""

def _call_model(client: genai.Client, candidate_models: list[str], prompt: str, system_prompt: str, temperature: float = 0.2) -> str:
    """Robust caller with automatic fallback across quota-safe models."""
    last_err = None
    for model_name in candidate_models:
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
            )
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if resp and resp.text:
                return resp.text.strip()
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All candidate models failed: {last_err}")


def deep_think(parameters: dict = None, player=None, speak=None) -> str:
    """
    Multi-Stage Agentic Reasoning Core:
      Stage 1: First-Principles Decomposition & Adversarial Red-Teaming (Stress-Test).
      Stage 2: Enterprise Production Synthesis & Decision Matrix.
      Output: Pushes high-fidelity visual blueprint to UI HUD; speaks 2-sentence executive summary.
    """
    params = parameters or {}
    query = str(params.get("query") or params.get("problem") or params.get("prompt") or "").strip()
    file_path = str(params.get("file_path") or params.get("file") or "").strip()
    raw_code = str(params.get("code") or "").strip()

    if not query and not file_path and not raw_code:
        return "Please specify the problem, system architecture, or logic puzzle to analyze, sir."

    api_key = _get_api_key()
    if not api_key:
        return "Gemini API key is missing. Please configure it in Settings."

    budget, level_label = _get_thinking_settings()

    # 1. Non-blocking audio acknowledgment to eliminate dead silence
    if speak and callable(speak):
        try:
            speak("Engaging multi-stage reasoning core. Analyzing first principles and stress-testing architecture now, sir.")
        except Exception:
            pass

    if player and hasattr(player, "write_log"):
        player.write_log(f"SYS: 🧠 Deep Thinking [{level_label}] engaged (Dual-Pass Reflection)...")

    # Ingest code/file context if present
    file_context = _resolve_file_context(file_path)
    if raw_code:
        file_context += f"\n\n--- INLINE CODE SNIPPET ---\n{raw_code}\n--------------------------\n"

    base_input = f"{query}{file_context}"

    # Quota-Safe Model Pool
    candidate_models = [
        "gemini-3.5-flash-lite",  # Primary: Ultra-fast, minimal quota
        "gemini-3.5-flash",       # Fallback 1: Standard
        "gemini-2.0-flash",       # Fallback 2: GA
    ]

    client = genai.Client(api_key=api_key)

    try:
        # ── STAGE 1: FIRST-PRINCIPLES DECOMPOSITION & ADVERSARIAL RED-TEAM ──
        if player and hasattr(player, "write_log"):
            player.write_log("SYS: 🔍 [Stage 1/2] Decomposing requirements & adversarial stress-testing...")

        stage1_sys = (
            "You are a Principal Systems Architect and Adversarial Red-Team Analyst.\n"
            "Your role is to rigorously deconstruct the user's inquiry from first principles and stress-test it:\n"
            "1. Deconstruct the problem to fundamental constraints (latency budgets, frame-time limits, memory footprints, compute complexity).\n"
            "2. Adversarial Red-Team: Attack the idea. Identify failure modes under 100x scale, race conditions, memory leaks, GPU bottlenecks, and architectural traps.\n"
            "3. Identify the pivotal engineering trade-offs (e.g. throughput vs latency, consistency vs availability).\n"
            "Be uncompromisingly technical, rigorous, and direct."
        )

        red_team_analysis = _call_model(
            client=client,
            candidate_models=candidate_models,
            prompt=base_input,
            system_prompt=stage1_sys,
            temperature=0.25
        )

        # ── STAGE 2: ENTERPRISE PRODUCTION SYNTHESIS & DECISION MATRIX ───────
        if player and hasattr(player, "write_log"):
            player.write_log("SYS: ⚡ [Stage 2/2] Synthesizing enterprise production blueprint...")

        stage2_sys = (
            "You are a Distinguished Enterprise Architect and Technical Fellow.\n"
            "Using the first-principles decomposition and adversarial stress-test provided, "
            "synthesize a definitive, company-grade, battle-tested production blueprint.\n\n"
            "CRITICAL OUTPUT FORMATTING:\n"
            "Structure your output into TWO clearly separated sections:\n\n"
            "=== REASONING BLUEPRINT ===\n"
            "Organize into structured phases. Do NOT include leading arrows like '▶' before PHASE (the UI generates them automatically):\n"
            "PHASE 1: [SYSTEM ARCHITECTURE & CORE MECHANICS]\n"
            "◆ [Component/Engine]: Specific technical specifications, architecture role, and baselines\n"
            "PHASE 2: [ADVERSARIAL EVALUATION & RISK MITIGATION]\n"
            "◆ [Bottleneck/Failure Mode]: Concrete mitigation strategy and architectural safeguard\n"
            "PHASE 3: [DECISION MATRIX & IMPLEMENTATION SPECIFICATION]\n"
            "◆ [Decision/Trade-Off]: Concrete technology choice, trade-off rationale, and code/schema pattern\n"
            "PHASE 4: [PRODUCTION DEPLOYMENT & VERIFICATION CHECKLIST]\n"
            "◆ [Milestone/Test]: Clear validation criteria and monitoring thresholds\n\n"
            "=== EXECUTIVE SUMMARY ===\n"
            "Provide exactly 2 authoritative, conversational sentences stating the final verdict and primary recommendation. "
            "Do NOT use markdown, bullets, or code in the Executive Summary."
        )

        stage2_payload = (
            f"--- ORIGINAL USER QUERY ---\n{base_input}\n\n"
            f"--- STAGE 1: FIRST-PRINCIPLES & ADVERSARIAL STRESS TEST ---\n{red_team_analysis}\n\n"
            f"Deliver the final Enterprise Production Blueprint and Executive Summary."
        )

        final_output = _call_model(
            client=client,
            candidate_models=candidate_models,
            prompt=stage2_payload,
            system_prompt=stage2_sys,
            temperature=0.2
        )

    except Exception as e:
        return f"Deep thinking engine encountered an error: {e}"

    # ── PARSE VISUAL BLUEPRINT VS CONVERSATIONAL VOICE SUMMARY ───────────────
    blueprint_match = re.search(r"=== REASONING BLUEPRINT ===\s*(.*?)(?==== EXECUTIVE SUMMARY ===|$)", final_output, re.DOTALL)
    summary_match = re.search(r"=== EXECUTIVE SUMMARY ===\s*(.*)", final_output, re.DOTALL)

    visual_blueprint = blueprint_match.group(1).strip() if blueprint_match else final_output
    spoken_summary = summary_match.group(1).strip() if summary_match else ""

    # Clean double arrows if the model happened to add them
    visual_blueprint = re.sub(r"^[▶\s\-•]+(?=PHASE)", "", visual_blueprint, flags=re.MULTILINE)

    # Clean spoken summary of markdown formatting
    spoken_summary = re.sub(r"[*_#`]", "", spoken_summary).strip()

    # Push Full Multi-Phase Blueprint to UI Screen HUD
    if player and hasattr(player, "show_content") and visual_blueprint:
        ui_title = f"REASONING BLUEPRINT — {query[:32].upper() if query else 'ANALYSIS'}"
        player.show_content(ui_title, visual_blueprint)

    if player and hasattr(player, "write_log"):
        player.write_log("SYS: ✨ Enterprise reasoning blueprint rendered on screen.")

    # Return concise executive summary for Gemini Live speech
    if spoken_summary:
        return f"{spoken_summary} The full enterprise reasoning blueprint is on your display, sir."

    sentences = re.split(r"(?<=[.!?]) +", visual_blueprint)
    short_voice = " ".join(sentences[:2]).strip()
    return f"{short_voice} The complete multi-phase architecture is displayed on screen, sir."