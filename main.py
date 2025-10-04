import sys
import argparse
import os
from typing import Dict, Any, List
from datetime import datetime

try:
    from rich.console import Console
    from rich.markdown import Markdown
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None

try:
    import tiktoken
    HAS_TOKENIZER = True
    ENCODER = tiktoken.get_encoding("cl100k_base")
except ImportError:
    HAS_TOKENIZER = False
    ENCODER = None

from src.router_api import ChatRouter
from src.personas import list_all_personas, get_persona_by_name
from src.utils import (
    setup_logger, logger,
    sanitize_input, detect_language, translate, now_iso,
    append_entry_jsonl, append_to_txt_log, call_hooks, get_theme
)

# === CONFIG ===
MAX_CONTEXT_TURNS = 6
MAX_AI_CHARS = 2000
SESSION_DIR = "logs/sessions"

def count_tokens(messages: List[Dict[str, str]]) -> int:
    """Count tokens using tiktoken if available, else rough char count/4."""
    if not HAS_TOKENIZER or not ENCODER:
        return int(sum(len(m.get("content", "")) for m in messages) / 4)
    # OpenAI-format prompt encoding
    all_txt = "".join(m.get("content", "") for m in messages)
    return len(ENCODER.encode(all_txt))

def trim_context(messages, max_tokens=2048):
    """Trim messages so their total token count is <= max_tokens."""
    if not messages:
        return []
    if not HAS_TOKENIZER or not ENCODER:
        return messages[-MAX_CONTEXT_TURNS:]
    # Trim from the start
    out = []
    total = 0
    for m in reversed(messages):
        tokens = len(ENCODER.encode(m.get("content","")))
        if total + tokens > max_tokens:
            break
        out.insert(0, m)
        total += tokens
    return out

def show_answer(answer):
    if HAS_RICH:
        try:
            console.print(Markdown(answer))
        except Exception:
            console.print(answer, style="bold cyan")
    else:
        print(answer)

def print_help():
    print("""
Commands:
    :exit, :quit......Exit the chat
    :clear............Clear in-memory chat context
    :save [filename]..Save history to file
    :tokens...........Show current context token usage
    :help, :commands..Show this help
    """)

def main():
    parser = argparse.ArgumentParser(description="Tiny AI QnA Bot CLI")
    parser.add_argument("--ui", action="store_true", help="Launch Streamlit UI")
    parser.add_argument("--model", type=str, help="Model ID or index")
    parser.add_argument("--persona", type=str, help="Persona name or index")
    parser.add_argument("--lang", type=str, help="Language code (e.g., en, hi, es)")
    parser.add_argument("--max-context", type=int, default=2048, help="Context window in tokens")
    args = parser.parse_args()

    if args.ui:
        import subprocess
        subprocess.run(["streamlit", "run", "src/ui_streamlit.py"])
        return

    logger.info("Launching TINY-AI-QNA-BOT CLI (PRO)")
    print("\n===============================")
    print("   TINY AI QnA BOT — Terminal")
    print("===============================")
    if HAS_RICH:
        console.print("Type :help for commands and tips.", style="bold green")

    # Model/persona selection
    models = ChatRouter.list_models()
    if args.model:
        try:
            model = models[int(args.model)-1]["id"] if args.model.isdigit() else args.model
        except Exception:
            model = models[0]["id"]
    else:
        print("\nAvailable Models:")
        for idx, m in enumerate(models):
            print(f"  {idx+1}. {m['name']}   ({m['id']}) — {m['description']}")
        model = models[int(input("Choose model (number): ").strip())-1]["id"]

    personas = list_all_personas()
    if args.persona:
        persona = get_persona_by_name(args.persona) or get_persona_by_name(personas[0]["name"])
    else:
        print("\nAvailable Personas:")
        for idx, p in enumerate(personas):
            print(f"  {idx+1}. {p['name']} [{p['style'].get('emoji','')}] — {p['description']}")
        persona = get_persona_by_name(personas[int(input("Choose persona (number): ").strip())-1]['name'])

    persona_lang = args.lang or list(persona.languages.keys())[0]

    print(f"\nPersona: {persona.name} ({persona.style.get('emoji','')}, language {persona_lang})")
    print(f"Model: {model}")

    router = ChatRouter()
    os.makedirs(SESSION_DIR, exist_ok=True)
    session_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    history_path = os.path.join(SESSION_DIR, f"chat_{session_id}.jsonl")
    context_max_tokens = args.max_context or 2048

    messages = []
    history = []
    call_hooks("on_start", {"session_id": session_id, "model": model, "persona": persona.name})

    while True:
        try:
            user_input = input("\nYou: ").strip()
            cmd = user_input.lower()
            if cmd in {"exit", "quit", ":exit", ":quit"}:
                print("Exiting. Goodbye!")
                break
            elif cmd == ":clear":
                messages.clear()
                print("[Context cleared]")
                continue
            elif cmd.startswith(":save"):
                fname = cmd.split(" ",1)[1] if " " in cmd else f"chat_{now_iso()}.jsonl"
                tgt = os.path.join(SESSION_DIR, fname)
                try:
                    with open(tgt, "w", encoding="utf-8") as f:
                        for h in history:
                            f.write(f"{h}\n")
                    print(f"[Session saved to {tgt}]")
                except Exception as e:
                    print("[Save failed]", e)
                continue
            elif cmd == ":tokens":
                toks = count_tokens(messages)
                print(f"[Context token usage: {toks} / {context_max_tokens}]")
                continue
            elif cmd in {":help", ":commands"}:
                print_help()
                continue

            user_input = sanitize_input(user_input)
            lang = detect_language(user_input)

            if lang != persona_lang:
                q_translated = translate(user_input, target=persona_lang)
                logger.info(f"Translated {lang}->{persona_lang}: {q_translated}")
            else:
                q_translated = user_input

            sys_msg = persona.get_prompt(language=persona_lang)
            chat_messages = [{"role": "system", "content": sys_msg}]
            # Trim context with token window if available
            trimmed_context = trim_context(messages, max_tokens=context_max_tokens)
            chat_messages.extend(trimmed_context)
            chat_messages.append({"role": "user", "content": q_translated})

            answer, meta = router.send_chat(chat_messages, model=model)
            meta = meta or {}

            if lang != persona_lang:
                answer_disp = translate(answer, target=lang)
            else:
                answer_disp = answer

            # Truncate very long AI outputs for stdout
            out = answer_disp[:MAX_AI_CHARS]
            show_answer(out)
            if len(answer_disp) > MAX_AI_CHARS:
                print("[truncated, see session log for full text]")

            entry: Dict[str, Any] = {
                "ts": now_iso(),
                "persona": persona.name,
                "language": lang,
                "user": user_input,
                "assistant": answer_disp,
                "meta": meta,
            }
            jline = entry.copy()
            append_entry_jsonl(history_path, entry)
            append_to_txt_log("logs/cli_chat_history.txt",
                f"[{entry['ts']}] {entry['persona']}: {user_input[:80]} => {answer_disp[:150]}"
            )
            history.append(jline)
            call_hooks("on_message", entry)

            messages.append({"role": "user", "content": q_translated})
            messages.append({"role": "assistant", "content": answer})

        except KeyboardInterrupt:
            print("\nInterrupted. Exiting chat.")
            break
        except Exception as e:
            print("Error occurred. Check logs for details.")
            logger.exception(f"Exception in main loop: {e}")

    call_hooks("on_exit", {"session_id": session_id})
    logger.info("TINY-AI-QNA-BOT CLI session ended. [Session: %s]", session_id)

if __name__ == "__main__":
    main()
