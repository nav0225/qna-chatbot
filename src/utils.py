import json
import os
import re
import logging
from typing import Optional, List, Any, Dict, Callable
from datetime import datetime

try:
    from googletrans import Translator
    HAS_TRANSLATOR = True
except Exception:
    HAS_TRANSLATOR = False

# === LOGGER SETUP ===
DEFAULT_LOGGER_NAME = "TinyAIChatbot"

def setup_logger(log_path: str = "bot.log", verbose: bool = False) -> logging.Logger:
    """
    Create or return a module-level logger. Safe to call multiple times
    (won't duplicate handlers).
    """
    logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Prevent duplicate handlers on repeated calls
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(log_path)
               for h in logger.handlers if hasattr(h, "baseFilename")):
        # ensure directory
        log_dir = os.path.dirname(log_path) or "."
        os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG if verbose else logging.INFO)

        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        # Add stream handler only once
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            logger.addHandler(stream_handler)

    return logger

# Create a module-level logger for convenience (can be overridden by caller)
logger = setup_logger()

# === TRANSLATOR SINGLETON ===
_TRANSLATOR: Optional["Translator"] = None
if HAS_TRANSLATOR:
    try:
        _TRANSLATOR = Translator()
    except Exception:
        HAS_TRANSLATOR = False
        _TRANSLATOR = None

# === FILE HELPERS ===
def ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)

def robust_write_file(path: str, content: str) -> bool:
    """Write content to file safely (creates parent dirs)."""
    try:
        ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        logger.exception("Failed to write file %s: %s", path, e)
        return False

def robust_read_file(path: str) -> Optional[str]:
    """Read file content or return None on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.debug("robust_read_file failed for %s: %s", path, e)
        return None

# === CHAT HISTORY (JSONL) ===
def save_chat_history(path: str, history: List[Dict[str, Any]]) -> bool:
    """
    Overwrite a history file with a list of entries (JSONL).
    Each entry should be a JSON-serializable dict.
    """
    try:
        ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            for entry in history:
                json.dump(entry, f, ensure_ascii=False)
                f.write("\n")
        return True
    except Exception as e:
        logger.exception("Failed to save chat history to %s: %s", path, e)
        return False

def append_entry_jsonl(path: str, entry: Dict[str, Any]) -> bool:
    """Append a single entry (dict) to a JSONL file."""
    try:
        ensure_dir(path)
        with open(path, "a", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
            f.write("\n")
        return True
    except Exception as e:
        logger.exception("Failed to append entry to %s: %s", path, e)
        return False

def load_chat_history(path: str) -> List[Dict[str, Any]]:
    """Load session history (JSONL) and return list of dicts; returns [] on error."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except Exception as e:
        logger.exception("Failed to load chat history from %s: %s", path, e)
        return []

def append_to_txt_log(path: str, entry: str) -> bool:
    """Append human-readable line to a plain text log."""
    try:
        ensure_dir(path)
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
        return True
    except Exception as e:
        logger.exception("Failed to append to txt log %s: %s", path, e)
        return False

# === MARKDOWN / HTML SAFETY ===
_MD_URL_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_HTML_TAG_RE = re.compile(r"<[^>]+>")  # non-greedy tag stripper

def clean_markdown(md: str) -> str:
    """
    Escape backticks and remove potentially dangerous HTML tags.
    Keeps markdown links intact if they appear to be valid-looking.
    """
    if not isinstance(md, str):
        return ""
    # escape backticks
    md = md.replace("`", "\\`")
    # remove HTML tags
    md = _HTML_TAG_RE.sub("", md)
    # ensure links are preserved (basic sanity)
    md = _MD_URL_PATTERN.sub(lambda m: f"[{m.group(1)}]({m.group(2)})", md)
    return md

def strip_html(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return _HTML_TAG_RE.sub("", text)

# === i18n: language detection & translation ===
def detect_language(text: str) -> str:
    """
    Detect language via googletrans (if available) or using unicode heuristics.
    Returns language code like 'en', 'hi', 'zh'.
    """
    if not isinstance(text, str) or not text.strip():
        return "en"
    if HAS_TRANSLATOR and _TRANSLATOR:
        try:
            detected = _TRANSLATOR.detect(text)
            if hasattr(detected, "lang"):
                return detected.lang
        except Exception as e:
            logger.debug("Translator detection failed: %s", e)
    # fallback heuristics
    if any("\u0900" <= ch <= "\u097F" for ch in text):
        return "hi"
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return "zh"
    return "en"

def translate(text: str, target: str = "en") -> str:
    """Translate text to target if translator available; otherwise return original."""
    if not isinstance(text, str) or not text.strip():
        return text
    if HAS_TRANSLATOR and _TRANSLATOR:
        try:
            translated = _TRANSLATOR.translate(text, dest=target)
            return getattr(translated, "text", text)
        except Exception as e:
            logger.debug("Translation failed: %s", e)
            return text
    return text

# === THEME HELPERS ===
PRESET_THEMES = {
    "light": {
        "primary": "#4267b2",
        "bg": "#f6f8ff",                  # Slightly off-white blue-tinted: better for eyes
        "user": "#d1e7ff",                # Vibrant blue for user bubble
        "ai": "#f3e5f5",                  # Light lavender for AI bubble
        "user_text": "#222",              # Near-black for best contrast
        "ai_text": "#222"
    },
    "dark": {
        "primary": "#282828",
        "bg": "#181818",
        "user": "#232c36",
        "ai": "#36314c",
        "user_text": "#efefef",           # High contrast white text
        "ai_text": "#efefef"
    }
}


def get_theme(theme: str) -> Dict[str, str]:
    return PRESET_THEMES.get(theme, PRESET_THEMES["light"])

# === SANITIZATION ===
def sanitize_input(user_input: str, max_length: int = 3000) -> str:
    """
    Remove non-printable characters, trim whitespace, collapse multiple spaces,
    and cap length to max_length.
    """
    if not isinstance(user_input, str):
        return ""
    cleaned = ''.join(c for c in user_input if c.isprintable())
    # collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned

# === SESSION HOOKS ===
SESSION_HOOKS: Dict[str, List[Callable]] = {}

def register_hook(event: str, fn: Callable) -> None:
    SESSION_HOOKS.setdefault(event, []).append(fn)

def call_hooks(event: str, *args, **kwargs) -> None:
    """Invoke registered hooks safely (exceptions logged, do not block)."""
    for fn in list(SESSION_HOOKS.get(event, [])):  # iterate copy to allow modifications
        try:
            fn(*args, **kwargs)
        except Exception as e:
            logger.exception("Hook '%s' raised: %s", event, e)

# === TIMESTAMP UTIL ===
def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"
