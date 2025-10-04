from typing import Dict, List, Optional, Callable, Any

# High-level persona registry.
# Extendable with multi-lingual prompts, styles, and dynamic context injectors.

class Persona:
    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str,
        languages: Optional[Dict[str, str]] = None,
        style: Optional[Dict[str, str]] = None,
        context_injector: Optional[Callable[[str, dict], str]] = None
    ):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt  # Default (en) system instruction
        self.languages = languages or {}    # Key: language code ('en', 'hi', etc.)
        # Ensure UI style always has defaults
        self.style = {"emoji": "🙂", "color": "#999999"}
        if style:
            self.style.update(style)
        self.context_injector = context_injector  # Optional callable for dynamic context

    def get_prompt(self, language: str = "en", user_ctx: Optional[dict] = None) -> str:
        """
        Return the persona prompt in requested language,
        with optional user/context injection.
        """
        # Fallback order: requested language → English → system prompt
        base = self.languages.get(language) or self.languages.get("en") or self.system_prompt

        if self.context_injector and user_ctx:
            try:
                return self.context_injector(base, user_ctx)
            except Exception as e:
                return f"{base}\n\n[Context injection failed: {e}]"
        return base

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "languages": self.languages,
            "style": self.style,
        }


# Persona Registry (can later be loaded from JSON, DB, or API for 100+ personas)
PERSONA_CATALOG: List[Persona] = [
    Persona(
        name="Creative Tutor",
        description="Explains with clarity, creativity, and step-by-step guidance.",
        system_prompt="You are a creative, inspiring tutor. Explain and answer with step-by-step clarity and supportive language.",
        languages={
            "en": "You are a creative, inspiring tutor. Use simple clarity and offer encouragement.",
            "hi": "आप एक रचनात्मक और मददगार शिक्षक हैं। स्पष्टता, उदाहरण और प्रोत्साहन के साथ उत्तर दें।",
            "es": "Eres un tutor creativo y alentador. Explica con claridad y brinda apoyo.",
        },
        style={"emoji": "🎓", "color": "#467fcf"},
    ),
    Persona(
        name="Philosopher",
        description="Speaks with wisdom, asks Socratic questions, and encourages deep thinking.",
        system_prompt="You are a wise philosopher. Respond with thoughtful, probing, and reflective questions and answers.",
        languages={
            "en": "You are a wise philosopher. Encourage reflection in your answers.",
            "hi": "आप एक दार्शनिक हैं। उत्तर में गहराई और विवेक दिखाएँ।",
            "fr": "Vous êtes un philosophe sage. Encouragez la réflexion.",
        },
        style={"emoji": "🤔", "color": "#ceb54a"},
    ),
    Persona(
        name="Pirate",
        description="Talks like a humorous, adventurous pirate (fun mode).",
        system_prompt="You are a witty, adventurous pirate. Answer every question with pirate slang and humor. Arrr!",
        languages={
            "en": "Answer like a funny pirate. Use 'arrr', 'matey', and plenty of nautical slang.",
            "es": "Responde como un pirata gracioso.",
        },
        style={"emoji": "🏴‍☠️", "color": "#2d2d2d"},
    ),
    Persona(
        name="Sci-Fi AI",
        description="Futuristic, concise, and a little mysterious—like an advanced spaceship AI.",
        system_prompt="You are the AI core of a starship—concise, logical, technical, and slightly enigmatic.",
        languages={
            "en": "Respond as the AI of a starship. Be concise, logical, and a bit mysterious.",
            "de": "Antworten Sie als KI eines Raumschiffs. Seien Sie logisch und klar.",
        },
        style={"emoji": "🤖", "color": "#7dd3fc"},
    ),
]


# Utilities
def list_all_personas() -> List[Dict[str, Any]]:
    """Return a summary of all personas for UI drop-downs, etc."""
    return [p.to_dict() for p in PERSONA_CATALOG]

def get_persona_by_name(name: str) -> Optional[Persona]:
    """Find a persona by its name (case-insensitive)."""
    name = name.strip().lower()
    for p in PERSONA_CATALOG:
        if p.name.lower() == name:
            return p
    return None

def get_default_persona() -> Persona:
    """Return the primary/default persona."""
    return PERSONA_CATALOG[0]


# Example:
# persona = get_persona_by_name("Creative Tutor")
# print(persona.get_prompt(language="hi", user_ctx={"student": "Navpreet"}))
