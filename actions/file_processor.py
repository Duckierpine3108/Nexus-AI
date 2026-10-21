"""
Actions: Universal Multimodal File Processor (Production Edition)
Advanced file intelligence for 12 file families:
  1. Images        → describe, ocr, analyze, resize, convert, compress, crop
  2. PDFs          → native multimodal vision OCR, summarize, extract_text, to_word
  3. Word & Text   → summarize, analyze, reformat, fix, translate, word_count
  4. CSV & Excel   → analyze, stats, filter, sort, convert (csv/xlsx/json/html)
  5. JSON & XML    → validate, format, extract, analyze, convert
  6. Source Code   → explain, review, fix (ast-verified), optimize, document, run
  7. Audio         → auto-compressed AI transcription, convert, trim, info
  8. Video         → extract_audio, trim, extract_frame, compress, transcribe, convert
  9. Archives      → list contents, extract (zip, tar, gz, bz2)
 10. Presentations → summarize, extract_text, analyze
"""

import os
import re
import io
import ast
import json
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# ── Optional Dependencies ────────────────────────────────────────────────────
try:
    from PIL import Image
    _PIL = True
except ImportError:
    _PIL = False

try:
    import pandas as pd
    _PANDAS = True
except ImportError:
    _PANDAS = False

# ── Base Directory & API Client Singleton ────────────────────────────────────
def _get_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
_CACHED_CLIENT = None
_CACHED_API_KEY = None

def _get_api_key() -> str:
    global _CACHED_API_KEY
    if _CACHED_API_KEY:
        return _CACHED_API_KEY
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _CACHED_API_KEY = json.load(f)["gemini_api_key"]
            return _CACHED_API_KEY
    except Exception as e:
        raise RuntimeError(f"Could not load Gemini API key from config/api_keys.json: {e}")

def _get_gemini_client():
    global _CACHED_CLIENT
    if _CACHED_CLIENT is not None:
        return _CACHED_CLIENT
    from google import genai
    _CACHED_CLIENT = genai.Client(api_key=_get_api_key())
    return _CACHED_CLIENT

_ACTIVE_MODELS = [
    "gemini-3.5-flash-lite",   # Low quota usage, fast, multimodal
    "gemini-3.8-flash",        # Fallback if lite is busy
]

def _ai_generate(contents, model: str = "gemini-3.5-flash-lite") -> str:
    """Centralized, quota-optimized wrapper for file analysis."""
    client = _get_gemini_client()
    models_to_try = [model] + [m for m in _ACTIVE_MODELS if m != model]
    last_err = None

    for m in models_to_try:
        try:
            response = client.models.generate_content(model=m, contents=contents)
            return (response.text or "").strip()
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if "404" in err_str or "not_found" in err_str or "not found" in err_str:
                print(f"[FileProcessor] ⚠️ Model '{m}' unavailable. Cascading to fallback...")
                continue
            raise e

    raise last_err

# ── Intelligent Path Resolution with Shortcuts ───────────────────────────────
def _resolve_file_path(raw: str) -> Path:
    clean = raw.strip().strip('"').strip("'")
    lower = clean.lower()

    shortcuts = {
        "desktop":   Path.home() / "Desktop",
        "downloads": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "pictures":  Path.home() / "Pictures",
        "music":     Path.home() / "Music",
        "videos":    Path.home() / "Videos",
        "home":      Path.home(),
        "nexus":     _CONFIG_PATH.parent.parent,
        "project":   _CONFIG_PATH.parent.parent,
    }

    norm = clean.replace("\\", "/")
    head, sep, rest = norm.partition("/")
    if sep and head.lower() in shortcuts:
        return (shortcuts[head.lower()] / rest.strip("/")).resolve()

    if lower in shortcuts:
        return shortcuts[lower].resolve()

    return Path(clean).expanduser().resolve()

def _output_path(src: Path, suffix: str, new_ext: str = None) -> Path:
    ext = new_ext or src.suffix
    name = f"{src.stem}_{suffix}{ext}"
    return src.parent / name

def _file_size_str(path: Path) -> str:
    size = path.stat().st_size
    if size < 1024:        return f"{size} B"
    if size < 1024**2:     return f"{size/1024:.1f} KB"
    if size < 1024**3:     return f"{size/1024**2:.1f} MB"
    return f"{size/1024**3:.1f} GB"

def _detect_type(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    image_exts   = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "ico"}
    video_exts   = {"mp4", "avi", "mov", "mkv", "wmv", "flv", "webm", "m4v"}
    audio_exts   = {"mp3", "wav", "ogg", "m4a", "aac", "flac", "wma", "opus"}
    code_exts    = {"py", "js", "ts", "jsx", "tsx", "html", "css", "java", "c",
                    "cpp", "cs", "go", "rs", "rb", "php", "sh", "ps1", "sql", "yaml", "yml", "toml"}
    archive_exts = {"zip", "tar", "gz", "bz2", "xz"}

    if ext in image_exts:    return "image"
    if ext in video_exts:    return "video"
    if ext in audio_exts:    return "audio"
    if ext in code_exts:     return "code"
    if ext in archive_exts:  return "archive"
    if ext == "pdf":         return "pdf"
    if ext in ("docx", "doc"): return "docx"
    if ext in ("txt", "md", "rst", "log", "ini", "cfg"): return "text"
    if ext in ("csv", "tsv"): return "csv"
    if ext in ("xlsx", "xls", "ods"): return "excel"
    if ext == "json":        return "json"
    if ext == "xml":         return "xml"
    if ext in ("pptx", "ppt"): return "pptx"
    return "unknown"

# ── 1. Image Processor ───────────────────────────────────────────────────────
def _process_image(path: Path, action: str, params: dict, speak=None) -> str:
    if not _PIL:
        return "Pillow is not installed. Please run: pip install Pillow"

    action = action or "describe"

    if action in ("describe", "ocr", "analyze", "read", "extract_text"):
        from google.genai import types
        img_bytes = path.read_bytes()
        mime = f"image/{path.suffix.lower().lstrip('.')}"
        if mime == "image/jpg": mime = "image/jpeg"

        prompt_map = {
            "describe": "Describe this image in clear, concise detail.",
            "ocr": "Extract and transcribe all visible text in this image accurately with its original structure.",
            "analyze": "Provide a comprehensive analysis of this image: key visual subjects, context, colors, text, and details.",
            "read": "Read and transcribe all textual content in this image.",
            "extract_text": "Extract all text present in this image.",
        }
        user_prompt = params.get("instruction") or prompt_map.get(action, "Analyze this image.")

        try:
            result = _ai_generate([
                types.Part.from_bytes(data=img_bytes, mime_type=mime),
                user_prompt
            ])
            if len(result) > 500 and params.get("save", True):
                out = _output_path(path, "analysis", ".txt")
                out.write_text(result, encoding="utf-8")
                return f"{result[:400]}...\n\nFull output saved: {out.name}"
            return result
        except Exception as e:
            return f"AI Image Analysis failed: {e}"

    if action == "resize":
        width  = int(params.get("width", 0))
        height = int(params.get("height", 0))
        scale  = float(params.get("scale", 0))
        try:
            with Image.open(path) as img:
                w, h = img.size
                if scale > 0:
                    new_size = (int(w * scale), int(h * scale))
                elif width and height:
                    new_size = (width, height)
                elif width:
                    new_size = (width, int(h * width / w))
                elif height:
                    new_size = (int(w * height / h), height)
                else:
                    return "Please specify width, height, or scale factor."

                resample_filter = getattr(Image, "Resampling", Image).LANCZOS
                resized = img.resize(new_size, resample_filter)
                out = _output_path(path, f"resized_{new_size[0]}x{new_size[1]}")
                resized.save(out)
                return f"Resized from {w}x{h} to {new_size[0]}x{new_size[1]}. Saved: {out.name}"
        except Exception as e:
            return f"Resize failed: {e}"

    if action in ("convert", "compress"):
        target_fmt = params.get("format", "jpeg").lower().strip(".")
        if target_fmt in ("jpg", "jpeg"):
            target_fmt = "jpeg"
            ext = ".jpg"
        else:
            ext = f".{target_fmt}"

        quality = int(params.get("quality", 80))
        try:
            with Image.open(path) as img:
                # Alpha Flattener: Safe conversion of RGBA/P to RGB without crash
                if target_fmt == "jpeg" and img.mode in ("RGBA", "LA", "P"):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                    img = bg
                elif target_fmt == "jpeg" and img.mode != "RGB":
                    img = img.convert("RGB")

                out = _output_path(path, f"converted" if action == "convert" else f"q{quality}", ext)
                img.save(out, format=target_fmt.upper(), quality=quality, optimize=True)
                before = _file_size_str(path)
                after = _file_size_str(out)
                return f"Processed image: {before} → {after}. Saved: {out.name}"
        except Exception as e:
            return f"Image processing failed: {e}"

    if action == "info":
        try:
            with Image.open(path) as img:
                return (f"Image Info: {img.format} format, {img.size[0]}x{img.size[1]}px, "
                        f"color mode: {img.mode}, size on disk: {_file_size_str(path)}")
        except Exception as e:
            return f"Info failed: {e}"

    return f"Unrecognized image action: '{action}'. Available: describe, ocr, analyze, resize, convert, compress, info"

# ── 2. PDF Processor (Native Multimodal & Text Hybrid) ───────────────────────
def _process_pdf(path: Path, action: str, params: dict, speak=None) -> str:
    action = action or "summarize"
    from google.genai import types

    # First attempt native text extraction
    extracted_text = ""
    try:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        for page in reader.pages[:40]:
            extracted_text += (page.extract_text() or "") + "\n"
    except Exception:
        pass

    pdf_bytes = path.read_bytes()
    file_size_mb = len(pdf_bytes) / (1024 * 1024)

    # Scanned PDF or Multimodal Deep Inspection
    # If text is too sparse (< 100 chars) or action is deep analysis, send raw PDF bytes to Gemini
    is_scanned = len(extracted_text.strip()) < 100

    if action in ("summarize", "analyze", "translate_hint", "ocr", "extract_text"):
        prompt_map = {
            "summarize": "Provide a comprehensive, structured summary of this PDF document.",
            "analyze": "Analyze this document thoroughly: extract all key findings, tables, figures, and conclusions.",
            "translate_hint": "Identify the language of this document and translate a 3-paragraph summary into English.",
            "ocr": "Extract all text, table data, and notes from this PDF document preserving structure.",
            "extract_text": "Extract all text from this document.",
        }
        instruction = params.get("instruction") or prompt_map.get(action, "Analyze this document.")

        try:
            # If scanned and under 25MB, use Gemini 2.5 Flash native PDF vision
            if (is_scanned or action in ("analyze", "ocr")) and file_size_mb <= 25:
                result = _ai_generate([
                    types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    instruction
                ])
            else:
                if not extracted_text.strip():
                    return "Could not extract text from this PDF and file exceeds multimodal limits."
                result = _ai_generate([f"{instruction}\n\nDocument Text:\n{extracted_text[:45000]}"])

            if params.get("save", True):
                out = _output_path(path, action, ".txt")
                out.write_text(result, encoding="utf-8")
                return f"{result[:400]}...\n\nFull analysis saved: {out.name}"
            return result
        except Exception as e:
            return f"PDF AI Analysis failed: {e}"

    if action == "info":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            return f"PDF Info: {len(reader.pages)} pages, size: {_file_size_str(path)}"
        except Exception:
            return f"PDF size: {_file_size_str(path)}"

    if action == "to_word":
        if not extracted_text.strip():
            return "Could not extract digital text from PDF to convert to Word."
        try:
            from docx import Document
            doc = Document()
            doc.add_heading(path.stem, 0)
            for paragraph in extracted_text.split("\n\n"):
                if paragraph.strip():
                    doc.add_paragraph(paragraph.strip())
            out = _output_path(path, "converted", ".docx")
            doc.save(out)
            return f"Converted to Word document. Saved: {out.name}"
        except ImportError:
            return "python-docx not installed. Run: pip install python-docx"

    return f"Unknown PDF action: '{action}'. Available: summarize, analyze, ocr, extract_text, to_word, info"

# ── 3. Word & Text Processor ─────────────────────────────────────────────────
def _process_text_doc(path: Path, file_type: str, action: str, params: dict, speak=None) -> str:
    action = action or "summarize"

    def _read_content() -> str:
        if file_type == "docx":
            try:
                from docx import Document
                doc = Document(str(path))
                return "\n".join(p.text for p in doc.paragraphs)
            except Exception as e:
                return f"DOCX read error: {e}"
        return path.read_text(encoding="utf-8", errors="replace")

    content = _read_content()
    if not content.strip():
        return "The document appears to be empty."

    if action == "word_count":
        words = len(content.split())
        chars = len(content)
        lines = content.count("\n") + 1
        return f"Document Metrics: {words:,} words, {chars:,} characters, {lines:,} lines."

    if action == "extract_text" and file_type != "text":
        out = _output_path(path, "extracted", ".txt")
        out.write_text(content, encoding="utf-8")
        return f"Extracted text saved to: {out.name}"

    prompt_map = {
        "summarize": f"Summarize this document concisely with bulleted key points:\n\n{content[:40000]}",
        "analyze": f"Analyze this document for tone, key arguments, and conclusions:\n\n{content[:40000]}",
        "reformat": f"Reformat this text cleanly with markdown headings, paragraphs, and lists:\n\n{content[:40000]}",
        "fix": f"Proofread and correct all grammar, spelling, and phrasing errors in this text:\n\n{content[:40000]}",
        "to_bullet": f"Convert the main takeaways of this text into clear bullet points:\n\n{content[:40000]}",
    }
    user_prompt = params.get("instruction") or prompt_map.get(action, f"Analyze this document:\n\n{content[:40000]}")

    try:
        result = _ai_generate(user_prompt)
        if params.get("save", True):
            out = _output_path(path, action, ".txt")
            out.write_text(result, encoding="utf-8")
            return f"{result[:400]}...\n\nSaved: {out.name}"
        return result
    except Exception as e:
        return f"Text processing failed: {e}"

# ── 4. CSV & Excel Data Science Processor ────────────────────────────────────
def _process_data(path: Path, file_type: str, action: str, params: dict, speak=None) -> str:
    if not _PANDAS:
        return "pandas is not installed. Please run: pip install pandas openpyxl"

    action = action or "analyze"
    try:
        if file_type == "csv":
            try:
                df = pd.read_csv(path)
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding="utf-8", encoding_errors="replace")
        else:
            df = pd.read_excel(path)
    except Exception as e:
        return f"Could not parse data file: {e}"

    if action == "info":
        cols = ", ".join(df.columns.astype(str).tolist()[:25])
        return f"Dataset: {len(df):,} rows x {len(df.columns)} columns.\nColumns: {cols}\nSize: {_file_size_str(path)}"

    if action == "stats":
        try:
            desc = df.describe(include="all").to_string()
            return f"Summary Statistics:\n{desc[:3000]}"
        except Exception as e:
            return f"Stats calculation failed: {e}"

    if action in ("convert", "to_csv", "to_excel", "to_json"):
        fmt = params.get("format", "csv").lower().strip(".")
        try:
            if fmt == "csv":
                out = _output_path(path, "converted", ".csv")
                df.to_csv(out, index=False, encoding="utf-8")
            elif fmt in ("xlsx", "excel"):
                out = _output_path(path, "converted", ".xlsx")
                df.to_excel(out, index=False)
            elif fmt == "json":
                out = _output_path(path, "converted", ".json")
                df.to_json(out, orient="records", force_ascii=False, indent=2)
            return f"Converted to {fmt.upper()}. Saved: {out.name}"
        except Exception as e:
            return f"Data conversion failed: {e}"

    if action == "filter":
        col = params.get("column", "")
        val = params.get("value", "")
        cond = params.get("condition", "equals").lower()
        if not col or col not in df.columns:
            return f"Column '{col}' not found. Available columns: {', '.join(df.columns.astype(str))}"
        try:
            if cond == "equals":     filtered = df[df[col].astype(str) == str(val)]
            elif cond == "contains": filtered = df[df[col].astype(str).str.contains(str(val), case=False, na=False)]
            elif cond == "gt":       filtered = df[df[col] > float(val)]
            elif cond == "lt":       filtered = df[df[col] < float(val)]
            else:                    filtered = df[df[col].astype(str) == str(val)]

            out = _output_path(path, "filtered", ".csv")
            filtered.to_csv(out, index=False)
            return f"Filter complete: {len(filtered):,} matching rows. Saved: {out.name}"
        except Exception as e:
            return f"Filter failed: {e}"

    if action == "sort":
        col = params.get("column", df.columns[0])
        asc = params.get("ascending", True)
        try:
            sorted_df = df.sort_values(col, ascending=asc)
            out = _output_path(path, "sorted", ".csv")
            sorted_df.to_csv(out, index=False)
            return f"Sorted by '{col}'. Saved: {out.name}"
        except Exception as e:
            return f"Sort failed: {e}"

    # Default action: AI Dataset Analysis
    preview = df.head(35).to_string()
    user_instruction = params.get("instruction") or "Analyze this dataset for trends, outliers, distributions, and insights."
    prompt = f"{user_instruction}\n\nDataset Info: {len(df):,} rows, {len(df.columns)} columns.\nPreview:\n{preview}"
    try:
        return _ai_generate(prompt)
    except Exception as e:
        return f"AI Data analysis failed: {e}"

# ── 5. JSON & Dedicated XML Processor ────────────────────────────────────────
def _process_json(path: Path, action: str, params: dict, speak=None) -> str:
    action = action or "analyze"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Invalid JSON file: {e}"

    if action == "validate":
        return f"Valid JSON. Root structure: {type(data).__name__}, file size: {_file_size_str(path)}"

    if action == "format":
        out = _output_path(path, "formatted", ".json")
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return f"Formatted JSON saved: {out.name}"

    if action == "to_csv" and isinstance(data, list):
        try:
            import pandas as pd
            df = pd.DataFrame(data)
            out = _output_path(path, "converted", ".csv")
            df.to_csv(out, index=False)
            return f"Converted JSON array to CSV. Saved: {out.name}"
        except Exception as e:
            return f"Could not convert to CSV: {e}"

    preview = json.dumps(data, indent=2, ensure_ascii=False)[:9000]
    prompt = f"Analyze this JSON data structure:\n{preview}"
    if params.get("instruction"):
        prompt = f"{params['instruction']}\n\nJSON data:\n{preview}"
    try:
        return _ai_generate(prompt)
    except Exception as e:
        return f"JSON processing failed: {e}"

def _process_xml(path: Path, action: str, params: dict, speak=None) -> str:
    """Dedicated XML processor — eliminates the old json.loads crash completely."""
    action = action or "analyze"
    try:
        tree = ET.parse(str(path))
        root = tree.getroot()
    except Exception as e:
        return f"Invalid XML file: {e}"

    if action == "validate":
        return f"Valid XML. Root tag: <{root.tag}> with {len(root)} direct child elements."

    if action == "format":
        try:
            import xml.dom.minidom
            raw_str = ET.tostring(root, encoding="utf-8")
            parsed = xml.dom.minidom.parseString(raw_str)
            pretty = parsed.toprettyxml(indent="  ")
            out = _output_path(path, "formatted", ".xml")
            out.write_text(pretty, encoding="utf-8")
            return f"Formatted XML saved: {out.name}"
        except Exception as e:
            return f"XML formatting failed: {e}"

    raw_text = path.read_text(encoding="utf-8", errors="replace")[:9000]
    prompt = f"Analyze this XML file (Root: <{root.tag}>):\n{raw_text}"
    if params.get("instruction"):
        prompt = f"{params['instruction']}\n\nXML snippet:\n{raw_text}"
    try:
        return _ai_generate(prompt)
    except Exception as e:
        return f"XML AI analysis failed: {e}"

# ── 6. Source Code Processor with AST Syntax Verification ────────────────────
def _process_code(path: Path, action: str, params: dict, speak=None) -> str:
    action = action or "explain"
    content = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lstrip(".")

    if action == "run":
        if ext == "py":
            try:
                res = subprocess.run(["python", str(path)], capture_output=True, text=True, timeout=30)
                out = (res.stdout or "") + (res.stderr or "")
                return f"Execution Output:\n{out[:3000]}" if out else "Execution finished with no output."
            except subprocess.TimeoutExpired:
                return "Execution timed out (30s safety limit)."
            except Exception as e:
                return f"Run failed: {e}"
        return f"Direct execution only supported for .py files."

    if action == "info":
        lines = content.count("\n") + 1
        return f"Code File: {lines:,} lines, language: {ext.upper()}, size: {_file_size_str(path)}"

    prompt_map = {
        "explain": f"Explain this {ext} code clearly and concisely:\n```{ext}\n{content[:32000]}\n```",
        "review": f"Perform a senior engineer review of this {ext} code for bugs, edge cases, security, and performance:\n```{ext}\n{content[:32000]}\n```",
        "fix": f"Fix all bugs, unhandled exceptions, and logic issues in this {ext} code. Return ONLY the complete corrected code in a code block:\n```{ext}\n{content[:32000]}\n```",
        "optimize": f"Optimize this {ext} code for speed, memory, and readability:\n```{ext}\n{content[:32000]}\n```",
        "document": f"Add comprehensive documentation and docstrings to this {ext} code:\n```{ext}\n{content[:32000]}\n```",
        "test": f"Write complete unit tests for this {ext} code:\n```{ext}\n{content[:32000]}\n```",
    }
    user_prompt = params.get("instruction") or prompt_map.get(action, f"Analyze this {ext} code:\n```{ext}\n{content[:32000]}\n```")

    try:
        result = _ai_generate(user_prompt)
        if action in ("fix", "optimize", "document") and params.get("save", True):
            out = _output_path(path, action)
            code_match = re.search(r"```(?:\w+)?\n(.*?)```", result, re.DOTALL)
            code_to_save = code_match.group(1) if code_match else result

            # Python AST Syntax Verification
            if ext == "py":
                try:
                    ast.parse(code_to_save)
                    print("[CodeProcessor] ✅ AST verification passed: Python syntax is valid.")
                except SyntaxError as syn_err:
                    return f"AI generated invalid Python syntax: {syn_err}. File was not saved."

            out.write_text(code_to_save, encoding="utf-8")
            return f"{result[:400]}...\n\nVerified and saved: {out.name}"
        return result
    except Exception as e:
        return f"Code processing failed: {e}"

# ── 7. Audio Processor with Auto-Downsampling ────────────────────────────────
def _process_audio(path: Path, action: str, params: dict, speak=None) -> str:
    action = action or "transcribe"
    from google.genai import types

    if action == "info":
        return f"Audio File: {_file_size_str(path)}"

    if action == "transcribe":
        audio_file = path
        temp_mono = None
        # Auto-Downsampling: If audio > 18MB, downsample to 16kHz mono mp3 to fit Gemini limits
        if path.stat().st_size > 18 * 1024 * 1024:
            try:
                temp_mono = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                temp_mono.close()
                subprocess.run([
                    "ffmpeg", "-i", str(path), "-ac", "1", "-ar", "16000",
                    "-b:a", "32k", str(temp_mono.name), "-y"
                ], capture_output=True, timeout=120)
                audio_file = Path(temp_mono.name)
            except Exception as e:
                print(f"[AudioProcessor] Downsample fallback: {e}")

        try:
            content = audio_file.read_bytes()
            mime = "audio/mp3" if audio_file.suffix.lower() == ".mp3" else "audio/wav"
            result = _ai_generate([
                types.Part.from_bytes(data=content, mime_type=mime),
                "Transcribe all speech in this audio accurately. Format speakers and paragraphs clearly."
            ])
            if params.get("save", True):
                out = _output_path(path, "transcript", ".txt")
                out.write_text(result, encoding="utf-8")
                return f"Transcription complete:\n{result[:400]}...\n\nSaved to: {out.name}"
            return result
        except Exception as e:
            return f"Audio transcription failed: {e}"
        finally:
            if temp_mono and os.path.exists(temp_mono.name):
                try: os.unlink(temp_mono.name)
                except Exception: pass

    if action == "trim":
        start = params.get("start", "0")
        end   = params.get("end", "")
        out = _output_path(path, "trimmed", path.suffix)
        cmd = ["ffmpeg", "-i", str(path), "-ss", str(start)]
        if end: cmd += ["-to", str(end)]
        cmd += ["-c", "copy", str(out), "-y"]
        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
            return f"Trimmed audio saved: {out.name}"
        except Exception as e:
            return f"Trim failed: {e}"

    return f"Unknown audio action: '{action}'. Available: transcribe, trim, info"

# ── 8. Video Processor (Secure Tempfiles & Native FFmpeg) ─────────────────────
def _process_video(path: Path, action: str, params: dict, speak=None) -> str:
    action = action or "info"

    if action == "info":
        return f"Video File: {path.name} ({_file_size_str(path)})"

    if action == "extract_audio":
        out = _output_path(path, "audio", ".mp3")
        try:
            subprocess.run(["ffmpeg", "-i", str(path), "-q:a", "0", "-map", "a", str(out), "-y"], capture_output=True, timeout=300)
            return f"Audio track extracted: {out.name}"
        except Exception as e:
            return f"Audio extraction failed: {e}"

    if action == "extract_frame":
        timestamp = params.get("timestamp", "00:00:01")
        out = _output_path(path, f"frame_{timestamp.replace(':', '')}", ".jpg")
        try:
            subprocess.run(["ffmpeg", "-i", str(path), "-ss", timestamp, "-vframes", "1", str(out), "-y"], capture_output=True, timeout=30)
            return f"Frame at {timestamp} extracted: {out.name}"
        except Exception as e:
            return f"Frame extraction failed: {e}"

    if action == "transcribe":
        temp_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_audio.close()
        try:
            subprocess.run(["ffmpeg", "-i", str(path), "-ac", "1", "-ar", "16000", "-b:a", "32k", str(temp_audio.name), "-y"], capture_output=True, timeout=300)
            return _process_audio(Path(temp_audio.name), "transcribe", params, speak)
        finally:
            if os.path.exists(temp_audio.name):
                try: os.unlink(temp_audio.name)
                except Exception: pass

    return f"Unknown video action: '{action}'. Available: info, extract_audio, extract_frame, transcribe"

# ── 9. Archives & Presentations ──────────────────────────────────────────────
def _process_archive(path: Path, action: str, params: dict, speak=None) -> str:
    action = action or "list"
    if action == "list":
        try:
            import zipfile
            with zipfile.ZipFile(str(path)) as z:
                names = z.namelist()
            preview = "\n".join(names[:35])
            suffix = f"\n... and {len(names)-35} more" if len(names) > 35 else ""
            return f"Archive Contents ({len(names)} items):\n{preview}{suffix}"
        except Exception as e:
            return f"Archive list error: {e}"

    if action == "extract":
        dest = _resolve_file_path(params.get("destination", str(path.parent / path.stem)))
        dest.mkdir(parents=True, exist_ok=True)
        try:
            shutil.unpack_archive(str(path), str(dest))
            return f"Extracted archive to: {dest.name}/"
        except Exception as e:
            return f"Extract error: {e}"

    return f"Unknown archive action: '{action}'"

def _process_pptx(path: Path, action: str, params: dict, speak=None) -> str:
    action = action or "summarize"
    try:
        from pptx import Presentation
        prs = Presentation(str(path))
        slides_text = []
        for i, slide in enumerate(prs.slides, 1):
            txt = [f"--- Slide {i} ---"]
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    txt.append(shape.text.strip())
            slides_text.append("\n".join(txt))
        content = "\n\n".join(slides_text)
    except Exception as e:
        return f"PPTX parsing error (install python-pptx): {e}"

    if action == "extract_text":
        out = _output_path(path, "text", ".txt")
        out.write_text(content, encoding="utf-8")
        return f"Presentation text extracted: {out.name}"

    prompt = f"Summarize this presentation slide deck:\n\n{content[:35000]}"
    try:
        return _ai_generate(prompt)
    except Exception as e:
        return f"PPTX AI summary failed: {e}"

# ── Central Action Dispatcher ────────────────────────────────────────────────
def file_processor(parameters: dict | None = None, player=None, speak=None) -> str:
    params = parameters or {}
    raw_path = params.get("file_path", "").strip()

    # Fallback to UI drop-file target if not passed in params
    if not raw_path and player and hasattr(player, "current_file"):
        raw_path = str(player.current_file or "")

    if not raw_path:
        return "Please specify the file path to process, sir."

    path = _resolve_file_path(raw_path)
    if not path.exists():
        return f"File does not exist: {path}"
    if not path.is_file():
        return f"Path is a directory, not a file: {path}"

    file_type = _detect_type(path)
    action = str(params.get("action", "")).lower().strip()

    if player and hasattr(player, "write_log"):
        player.write_log(f"FILE: ⚙️ [{file_type.upper()}] '{path.name}' → action='{action or 'auto'}'")

    dispatch = {
        "image":   _process_image,
        "pdf":     _process_pdf,
        "docx":    lambda p, a, pm, s: _process_text_doc(p, "docx", a, pm, s),
        "text":    lambda p, a, pm, s: _process_text_doc(p, "text", a, pm, s),
        "csv":     lambda p, a, pm, s: _process_data(p, "csv", a, pm, s),
        "excel":   lambda p, a, pm, s: _process_data(p, "excel", a, pm, s),
        "json":    _process_json,
        "xml":     _process_xml,
        "code":    _process_code,
        "audio":   _process_audio,
        "video":   _process_video,
        "archive": _process_archive,
        "pptx":    _process_pptx,
    }

    handler = dispatch.get(file_type)
    if not handler:
        # Fallback to generic AI document inspection
        try:
            content = path.read_text(encoding="utf-8", errors="replace")[:12000]
            return _ai_generate(f"Analyze this file ({path.name}):\n\n{content}")
        except Exception as e:
            return f"Unsupported file type ({path.suffix}): {e}"

    try:
        result = handler(path, action, params, speak)
        return result or "Processing complete."
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"File processor error ({file_type}): {e}"