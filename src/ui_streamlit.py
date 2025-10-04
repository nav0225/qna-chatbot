import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


import streamlit as st
import traceback
from typing import Dict, Any, List

from src.router_api import ChatRouter
from src.personas import list_all_personas, get_persona_by_name
from src.utils import (
    setup_logger, logger,
    sanitize_input, detect_language, translate,
    now_iso, get_theme,
    append_entry_jsonl, append_to_txt_log, load_chat_history,
    call_hooks,
)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Tiny AI QnA Bot",
    page_icon="🤖",
    layout="wide",
)

# Initialize logger for UI
logger = setup_logger("logs/ui.log", verbose=True)

# --- THEME STYLING (dynamic container-based) ---
def apply_theme(theme: Dict[str, str]) -> None:
    st.markdown(
        f"""
        <style>
        html, body {{
            background: {theme['bg']};
            font-family: 'Segoe UI', Arial, sans-serif;
        }}
        .user-bubble {{
            background: {theme['user']};
            color: {theme['user_text']};
            padding: 14px 18px; border-radius: 22px; margin-bottom: 10px;
            font-size: 1.05em; box-shadow: 0 2px 10px #0001;
        }}
        .ai-bubble {{
            background: {theme['ai']};
            color: {theme['ai_text']};
            padding: 14px 18px; border-radius: 22px; margin-bottom: 10px;
            font-size: 1.05em; box-shadow: 0 2px 10px #0001;
        }}
        .meta-info {{
            font-size: 0.85em; color: #888; margin-bottom: 16px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# --- SESSION STATE ---
if "history" not in st.session_state:
    st.session_state["history"] = []
if "chat_router" not in st.session_state:
    st.session_state["chat_router"] = ChatRouter()
if "theme" not in st.session_state:
    st.session_state["theme"] = "light"

theme = get_theme(st.session_state["theme"])
apply_theme(theme)

# --- SIDEBAR: Model, Persona, Theme, Transcript ---
st.sidebar.markdown("## Model Selection")
models = ChatRouter.list_models()
model_options = [m["name"] for m in models]
model_choice = st.sidebar.selectbox("Choose Model", model_options)
selected_model = next((m["id"] for m in models if m["name"] == model_choice), models[0]["id"])

st.sidebar.markdown("## Persona")
personas = list_all_personas()
persona_names = [p["name"] for p in personas]
persona_choice = st.sidebar.selectbox("Persona", persona_names)
persona_obj = get_persona_by_name(persona_choice)
persona_langs = persona_obj.languages.keys()
persona_lang = st.sidebar.selectbox("Persona Language", list(persona_langs))

st.sidebar.markdown("## Theme & UI")
theme_choice = st.sidebar.selectbox(
    "Theme", ["light", "dark"], index=["light", "dark"].index(st.session_state["theme"])
)
if theme_choice != st.session_state["theme"]:
    st.session_state["theme"] = theme_choice
    theme = get_theme(theme_choice)
    apply_theme(theme)

st.sidebar.markdown("## Transcript")
if st.sidebar.button("Download Full Transcript (.txt)"):
    full_log = "\n".join(
        f"[{entry['ts']}] {entry['persona']}: {entry['user']} => {entry['assistant']}"
        for entry in st.session_state["history"]
    )
    st.download_button(
        label="Download",
        data=full_log,
        file_name="chat_transcript.txt",
    )


# --- MAIN CHAT UI ---
st.title("🤖 Tiny AI QnA Bot — Multi-Model, Multi-Persona")

# 2. Input box always at the bottom (no reruns needed)
with st.form(key="chat_input", clear_on_submit=True):
    user_input = st.text_area(
        f"Your question ({persona_obj.style.get('emoji', '🙂')} Persona in {persona_lang}):",
        key="user_input",
        height=80,
        max_chars=2000,
    )
    submit_button = st.form_submit_button(label="Send")

if submit_button and user_input.strip():
    try:
        q = sanitize_input(user_input)
        lang = detect_language(q)
        logger.info(f"User input detected as language: {lang}")

        # Translate input if persona language differs
        if lang != persona_lang:
            q_translated = translate(q, target=persona_lang)
            logger.info(f"Translated user input to {persona_lang}: {q_translated}")
        else:
            q_translated = q

        # Persona system message
        sys_msg = persona_obj.get_prompt(language=persona_lang)
        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": q_translated},
        ]

        with st.spinner("AI is generating an answer..."):
            answer, meta = st.session_state["chat_router"].send_chat(
                messages, model=selected_model
            )

        meta = meta or {}
        logger.info(
            f"AI response (truncated): {answer[:200]}{'...' if len(answer) > 200 else ''}"
        )

        # Translate answer back to user language if different
        if lang != persona_lang:
            answer_display = translate(answer, target=lang)
        else:
            answer_display = answer

        # Store conversation
        entry = {
            "ts": now_iso(),
            "persona": persona_choice,
            "language": lang,
            "user": user_input,
            "assistant": answer_display,
            "meta": meta,
        }
        st.session_state["history"].append(entry)
        append_entry_jsonl("logs/chat_history.jsonl", entry)
        append_to_txt_log(
            "logs/chat_history.txt",
            f"[{entry['ts']}] {entry['persona']}: {user_input} => {answer_display}",
        )

        # Fire hooks (analytics, plugins, etc.)
        call_hooks("on_message", entry)
    
    except Exception as e:
        st.error("An error occurred. See logs for details.")
        logger.exception(f"Streamlit UI error: {e}")
        st.stop()

# 1. Show chat history first (above)
for entry in st.session_state["history"]:
    st.markdown(
        f"""
        <div class="user-bubble">{entry['user']}</div>
        <div class="ai-bubble">{entry['assistant']}</div>
        <div class="meta-info">
            <span>Model: {entry.get('meta', {}).get('model', selected_model)}</span>
            <span>Tokens: {entry.get('meta', {}).get('usage', {}).get('total_tokens', '—')}</span>
            <span>Persona: {entry['persona']} ({entry['language']})</span>
            <span>{entry['ts']}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- FOOTER ---
st.markdown(
    "<div style='margin-top:2em;color:#888;'>Built by Navpreet. Powered by OpenRouter & Streamlit.</div>",
    unsafe_allow_html=True,
)
