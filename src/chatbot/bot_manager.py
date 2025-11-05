# bot_manager.py
"""
Unified BotManager
- Manages sessions (create_new_session / get_bot_response / end_session)
- Loads empathy prompts (cognitive/emotional/motivational/control)
- Calls provider APIs (OpenAI, Gemini, Anthropic) using modern patterns
- Crisis detection: short-circuits to crisis response
"""

import os
import uuid
import random
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try imports for flexible project layouts
try:
    from crisis_detector import CrisisDetector
except Exception:
    CrisisDetector = None  # Will disable if module not present

# ---- Utility helpers ---------------------------------------------------------

def _get_cfg(cfg: dict, path: List[str], default=None):
    cur = cfg or {}
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur

def _first_existing_path(paths: List[str]) -> Optional[str]:
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None

def _read_text(paths: List[str]) -> str:
    fp = _first_existing_path(paths)
    if not fp:
        return ""
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""

# ---- BotManager --------------------------------------------------------------

class BotManager:
    def __init__(self, db_manager, config: dict):
        self.db = db_manager
        self.config = config or {}

        # API settings (OpenAI only)
        self.api_provider = "openai"
        self.model = _get_cfg(self.config, ["api", "model"], "gpt-4")
        self.temperature = float(_get_cfg(self.config, ["api", "temperature"], 0.7))
        self.max_tokens = int(_get_cfg(self.config, ["api", "max_tokens"], 1024))
        self.max_words = int(_get_cfg(self.config, ["api", "max_words"], 150))

        # Paths (support both ./config and project root)
        self.app_cfg_path = _first_existing_path(["config/app_config.yaml", "app_config.yaml"])
        self.crisis_text_path = _first_existing_path(["config/crisis_response.txt", "crisis_response.txt"])
        self.prompts = {
            "cognitive": _read_text(["config/cognitive_empathy_prompt.txt", "cognitive_empathy_prompt.txt"]),
            "emotional": _read_text(["config/emotional_empathy_prompt.txt", "emotional_empathy_prompt.txt"]),
            "motivational": _read_text(["config/motivational_empathy_prompt.txt", "motivational_empathy_prompt.txt"]),
            "neutral": ""  # neutral baseline
        }
        self.bot_types = ["cognitive", "emotional", "motivational", "neutral"]

        # Sessions (in memory)
        self.sessions: Dict[str, Dict[str, Any]] = {}

        # Crisis detector (optional)
        self.crisis = None
        if CrisisDetector is not None and self.app_cfg_path:
            try:
                self.crisis = CrisisDetector(config_path=self.app_cfg_path)
            except Exception:
                self.crisis = None

        # Initialize provider client
        self._init_client()

    # Public API expected by app.py

    def create_new_session(self, bot_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new session with optional bot_type override.
        Empathy modality assignment remains sequential; watermark visibility is randomized.
        
        Args:
            bot_type: Optional bot type to assign. Must be one of self.bot_types if provided.
            
        Returns:
            Dict with session_id, participant_id, bot_type, and watermark_condition
            
        Raises:
            ValueError: If bot_type is provided but not in valid bot_types list
        """
        session_id = str(uuid.uuid4())
        participant_id = f"P{str(uuid.uuid4())[:8].upper()}"
        
        # Validate bot_type if provided
        if bot_type is not None and bot_type not in self.bot_types:
            raise ValueError(f"Invalid bot_type: '{bot_type}'. Must be one of {self.bot_types}")
        
        # If no bot_type specified, use sequential assignment
        if bot_type is None:
            # Get total participants from database for sequential rotation
            try:
                stats = self.db.get_statistics()
                total_participants = stats.get('total_participants', 0)
                index = total_participants % len(self.bot_types)
                bot_type = self.bot_types[index]
            except Exception:
                # Fallback to random if database unavailable
                bot_type = random.choice(self.bot_types)
        
        # Randomize watermark condition (visible/hidden) independently
        watermark_condition = random.choice(["visible", "hidden"])

        self.sessions[session_id] = {
            "participant_id": participant_id,
            "bot_type": bot_type,
            "watermark_condition": watermark_condition,
            "history": []  # [{"role":"user"/"assistant", "content": "..."}]
        }
        return {
            "session_id": session_id,
            "participant_id": participant_id,
            "bot_type": bot_type,
            "watermark_condition": watermark_condition,
        }

    def get_bot_response(self, session_id: str, user_message: str, message_num: int) -> Dict[str, Any]:
        sess = self.sessions.get(session_id)
        if not sess:
            raise ValueError(f"Session not found: {session_id}")

        # Crisis short-circuit (if configured)
        if self.crisis:
            try:
                is_crisis, detected_keyword = self.crisis.check_message(user_message)
            except Exception:
                is_crisis, detected_keyword = False, None
            if is_crisis:
                return {
                    "bot_response": self._crisis_text(),
                    "crisis_detected": True,
                    "detected_keyword": detected_keyword,
                }

        bot_type = sess["bot_type"]
        base_prompt = self.prompts.get(bot_type, "")
        # Add a concise-length policy so the model ends naturally, plus an anchor to maintain style
        length_policy = (
            f"Please keep responses concise, around {self.max_words} words, and finish your thought with a complete sentence."
        )
        anchor = ""
        if base_prompt:
            anchor = (
                f" Maintain the {bot_type} empathy style consistently throughout this conversation. Do not switch styles or tones."
            )
        # Add anti-repetition instruction
        anti_repeat = (
            " Review the full conversation history before responding. Do not repeat the same advice, suggestions, or phrasing you have already provided. "
            "Build upon previous exchanges and offer new perspectives or information each time."
        )
        system_prompt = (base_prompt + "\n\n" + length_policy + anchor + anti_repeat).strip() if base_prompt else (length_policy + anti_repeat)

        # Build messages (system + FULL history + current) - send ALL conversation history
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        # Send FULL history to maintain context across all 10 turns
        messages.extend(sess["history"])
        messages.append({"role": "user", "content": user_message})

        # Call the model
        reply = self._call_model(messages)
        # Enforce approximate word cap with sentence-aware truncation as a fallback
        reply = self._truncate_words_nicely(reply, self.max_words)

        # Update history
        sess["history"].append({"role": "user", "content": user_message})
        sess["history"].append({"role": "assistant", "content": reply})

        return {
            "bot_response": reply,
            "crisis_detected": False,
            "detected_keyword": None,
        }

    # ---------- Crisis helper (public) ----------

    def check_crisis(self, user_message: str) -> tuple[bool, Optional[str], Optional[str]]:
        """Check a message for crisis keywords and return (is_crisis, keyword, crisis_text)."""
        if not self.crisis:
            return False, None, None
        try:
            is_crisis, detected_keyword = self.crisis.check_message(user_message)
        except Exception:
            return False, None, None
        if is_crisis:
            return True, detected_keyword, self._crisis_text()
        return False, None, None

    # ---------- Streaming responses ----------

    def stream_bot_response(self, session_id: str, user_message: str):
        """Yield assistant text chunks for a response, updating session history at the end.

        This does NOT perform crisis detection; call check_crisis() before invoking streaming.
        """
        sess = self.sessions.get(session_id)
        if not sess:
            raise ValueError(f"Session not found: {session_id}")

        bot_type = sess["bot_type"]
        base_prompt = self.prompts.get(bot_type, "")
        length_policy = (
            f"Please keep responses concise, around {self.max_words} words, and finish your thought with a complete sentence."
        )
        anchor = ""
        if base_prompt:
            anchor = (
                f" Maintain the {bot_type} empathy style consistently throughout this conversation. Do not switch styles or tones."
            )
        # Add anti-repetition instruction
        anti_repeat = (
            " Review the full conversation history before responding. Do not repeat the same advice, suggestions, or phrasing you have already provided. "
            "Build upon previous exchanges and offer new perspectives or information each time."
        )
        system_prompt = (base_prompt + "\n\n" + length_policy + anchor + anti_repeat).strip() if base_prompt else (length_policy + anti_repeat)

        # Build messages (system + FULL history + current) - send ALL conversation history
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        # Send FULL history to maintain context across all 10 turns
        messages.extend(sess["history"])
        messages.append({"role": "user", "content": user_message})

        full = []
        words_seen = 0
        exceeded = False
        try:
            stream = self._client.chat.completions.create(
                model=self.model or "gpt-4",
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = getattr(getattr(chunk, "choices", [None])[0], "delta", None)
                token = getattr(delta, "content", None) if delta else None
                if token:
                    full.append(token)
                    yield token
                    # Word-aware, sentence-friendly stop
                    words_seen = len("".join(full).split())
                    if not exceeded and words_seen >= self.max_words:
                        exceeded = True
                    if exceeded:
                        txt = "".join(full)
                        # If we've crossed the cap and see sentence end, stop
                        if any(p in token for p in (".", "!", "?")):
                            break
                        # Hard stop if we go too far beyond (cap + 25 words)
                        if words_seen >= self.max_words + 25:
                            break
        except Exception as e:
            # On error, yield a single error string
            yield f"I’m sorry, I ran into an error: {e}"

        # Update history after streaming completes (best-effort)
        try:
            final = "".join(full)
            final = self._truncate_words_nicely(final, self.max_words)
            sess["history"].append({"role": "user", "content": user_message})
            sess["history"].append({"role": "assistant", "content": final})
        except Exception:
            pass

    # ---------- Utility ----------

    @staticmethod
    def _truncate_words_nicely(text: str, limit: int) -> str:
        """Truncate around a word limit, preferring to end at sentence punctuation.

        Strategy: if text exceeds `limit`, allow up to +20 extra words and
        cut at the last ., !, or ? if present; otherwise cut at `limit`.
        """
        try:
            text = text or ""
            words = text.split()
            if len(words) <= max(0, limit):
                return text
            # Build a buffer up to limit+20
            upto = " ".join(words[: max(0, limit + 20)])
            # Find last sentence boundary
            last_punct = max(upto.rfind("."), upto.rfind("!"), upto.rfind("?"))
            if last_punct != -1 and last_punct > 0:
                return upto[: last_punct + 1].strip()
            # Fallback: hard cut at limit
            return " ".join(words[: max(0, limit)])
        except Exception:
            return text or ""

    def end_session(self, session_id: str, completed: bool = True):
        # Nothing fancy; just drop in-memory state
        if session_id in self.sessions:
            del self.sessions[session_id]

    # ---------- Provider clients ----------

    def _init_client(self):
        # Initialize OpenAI client only
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                # Fallback to Streamlit secrets when running on Streamlit Cloud
                try:
                    import streamlit as st  # type: ignore
                    api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
                except Exception:
                    api_key = None
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            self._client = OpenAI(api_key=api_key)
            self._provider = "openai"
        except Exception as e:
            raise RuntimeError(f"Failed to init OpenAI client: {e}")

    def _call_model(self, messages: List[Dict[str, str]]) -> str:
        try:
            # OpenAI only - simplified
            resp = self._client.chat.completions.create(
                model=self.model or "gpt-4",
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return (resp.choices[0].message.content or "").strip()



        except Exception as e:
            return f"I’m sorry, I ran into an error: {e}"

    # ---------- Crisis text helper ----------

    def _crisis_text(self) -> str:
        # Prefer CrisisDetector's configured response if available
        if self.crisis and hasattr(self.crisis, "get_crisis_response"):
            try:
                return self.crisis.get_crisis_response()
            except Exception:
                pass
        # Fallback: read file directly
        txt = _read_text([self.crisis_text_path] if self.crisis_text_path else [])
        return txt or (
            "I'm concerned about your safety. If you are in immediate danger, please call your local emergency number. "
            "You can also reach out to a trusted person or a professional helpline available in your area."
        )
