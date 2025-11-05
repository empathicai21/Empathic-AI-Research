"""
Chat Interface
Creates the Streamlit-based chat interface for participants.
"""

import streamlit as st
from typing import Dict, List
from datetime import datetime
import html as _html
from urllib.parse import quote as _urlquote


class ChatInterface:
    """
    Manages the chat user interface using Streamlit.
    Provides clean, professional chat experience for participants.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize chat interface.
        
        Args:
            config: Application configuration dictionary
        """
        self.config = config
        self.max_messages = config['conversation']['max_messages']
        self.show_counter = config['conversation']['show_message_counter']
    
    
    def display_welcome_page(self) -> bool:
        """
        Display welcome page with consent and instructions.
        
        Returns:
            True if user agreed to participate, False otherwise
        """
        # Try to capture external IDs from URL (Qualtrics/Prolific)
        captured_id = None
        try:
            # Use modern Streamlit API; behaves like a dict-like mapping
            params = st.query_params
            candidates = []
            for key in (
                'prolific_id', 'pid', 'PROLIFIC_PID', 'participant_id',
                'rid', 'response_id', 'ResponseID', 'QUALTRICS_ID'
            ):
                val = params.get(key)
                # Accept either string or list[str] (for backward compatibility)
                if isinstance(val, str):
                    v = val.strip()
                    if v:
                        candidates.append(v)
                elif isinstance(val, list) and val:
                    first = val[0]
                    if isinstance(first, str):
                        v = first.strip()
                        if v:
                            candidates.append(v)
            if candidates:
                captured_id = candidates[0]
                # Initialize session_state if not already set
                if not st.session_state.get('prolific_id'):
                    st.session_state.prolific_id = captured_id
        except Exception:
            pass

        # Watermark and disclaimer for welcome page as well
        ui = self.config.get('ui') if isinstance(self.config.get('ui'), dict) else {}
        wm = ui.get('chat_watermark') if isinstance(ui, dict) else None
        self.render_watermark(wm)
        disc = ui.get('chat_disclaimer') if isinstance(ui, dict) else None
        self.render_disclaimer(disc)

        st.title("Welcome to the Mental Health Support Study")

        st.markdown(f"""
        ### About This Study
        
        You are invited to participate in a research study exploring AI-based mental health support.
        
        **What to expect:**
        - You'll have a conversation with an AI assistant about a mental health concern
        - The conversation will last up to {self.max_messages} messages
        - Your responses will be kept confidential and anonymous
        - You can end the conversation at any time
        
        **Important:**
        - This AI is NOT a replacement for professional mental health care
        - If you're experiencing a crisis, please call 988 (Suicide & Crisis Lifeline)
        - All conversations are recorded for research purposes
        
        **Your participation is voluntary and anonymous.**
        """)
        
        # Prolific/External ID input (can be prefilled from URL)
        lock_input = False
        if isinstance(ui, dict):
            lock_input = bool(ui.get('lock_prolific_input', False))
        default_ext_id = st.session_state.get('prolific_id') or captured_id or ""
        prolific_id = st.text_input(
            "Enter your Prolific ID (if you have one)",
            value=default_ext_id,
            disabled=(lock_input and bool(default_ext_id)),
            key="prolific_id_input",
            help="We'll use this for matching with study records."
        )

        # Consent checkbox
        consent = st.checkbox(
            "I understand this is a research study and agree to participate",
            key="consent_checkbox"
        )
        
        # Start button
        if consent:
            if st.button("Start Conversation", type="primary"):
                # Save prolific ID to session state (may be empty)
                st.session_state.prolific_id = prolific_id.strip() if prolific_id else None
                return True
        
        return False
    
    
    def display_message_counter(self, current: int, maximum: int):
        """
        Display message counter at top of chat.
        
        Args:
            current: Current message number
            maximum: Maximum messages allowed
        """
        if self.show_counter:
            progress = (current / maximum) if maximum else 0
            col_progress, col_label = st.columns([4, 1])
            with col_progress:
                st.progress(progress)
            with col_label:
                st.markdown(
                    f"<div class='msg-counter'>Message {current} of {maximum}</div>",
                    unsafe_allow_html=True,
                )
    
    
    def display_chat_message(self, role: str, content: str, turn: int | None = None, maximum: int | None = None):
        """
        Display a single chat message.
        
        Args:
            role: "user" or "assistant"
            content: Message text
            turn: Optional turn number (for user messages)
            maximum: Optional maximum turns
        """
        with st.chat_message(role):
            # Show a small turn label for user messages only
            if role == "user" and turn is not None and maximum:
                st.caption(f"Turn {turn} of {maximum}")
            st.markdown(content)
    
    
    def display_chat_history(self, messages: List[Dict]):
        """
        Display entire chat history.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
        """
        for message in messages:
            role = message.get('role')
            content = message.get('content')
            turn = message.get('message_num') if role == 'user' else None
            self.display_chat_message(role, content, turn=turn, maximum=self.max_messages)
    
    
    def get_user_input(self, disabled: bool = False) -> str:
        """
        Get user input from chat input box.
        
        Args:
            disabled: Whether input should be disabled
            
        Returns:
            User's message text or empty string
        """
        placeholder = "Type your message here..." if not disabled else "Message limit reached - click 'End Conversation' to proceed"
        
        user_input = st.chat_input(
            placeholder,
            disabled=disabled,
            key="user_input"
        )
        
        return user_input if user_input else ""
    
    
    def display_crisis_warning(self):
        """Display crisis resources warning box."""
        st.warning("""
        **If you're in crisis:**
        - Call or text 988 (Suicide & Crisis Lifeline)
        - Text HOME to 741741 (Crisis Text Line)
        - Call 911 for immediate emergency
        """)
    
    
    def display_completion_page(self, participant_id: str):
        """
        Display conversation completion page.
        
        Args:
            participant_id: Participant's ID
        """
        st.title("Thank You for Participating!")
        
        st.success("✓ Conversation completed")
        
        st.markdown("""
        ### What's Next
        
        Thank you for your participation in this research study. Your responses will help us understand 
        how AI can better support mental health conversations.
        
        **Remember:**
        - This AI is not a substitute for professional mental health care
        - If you need ongoing support, please contact a mental health professional
        - Crisis resources are available 24/7 at 988 or text HOME to 741741
        
        **Your responses have been recorded anonymously.**
        
        You may now close this window.
        """)
        
        # Optional feedback form
        with st.expander("Optional: Share Feedback"):
            # Use widget-specific keys to avoid mutating their session_state entries programmatically
            rating = st.slider(
                "How helpful was this chat? (1 = Not at all, 5 = Very helpful)",
                1, 5, 4,
                key="feedback_rating_input"
            )
            text = st.text_area(
                "Anything you'd like to share?",
                key="feedback_text_input",
                help="Your feedback helps improve the system"
            )

            if st.button("Submit Feedback"):
                # Store under separate keys so we don't conflict with widget-managed keys
                st.session_state.submitted_feedback = True
                st.session_state.submitted_feedback_rating = rating
                st.session_state.submitted_feedback_text = text
                st.success("Thank you for your feedback!")
    
    
    def display_error_page(self, error_message: str):
        """
        Display error page.
        
        Args:
            error_message: Error message to display
        """
        st.error("An error occurred")
        st.write(error_message)
        st.write("Please refresh the page to try again.")
    
    
    def display_typing_indicator(self):
        """Display typing indicator while bot is responding."""
        with st.chat_message("assistant"):
            with st.spinner(""):
                st.write("")  # Placeholder for typing animation
    
    
    def apply_custom_css(self):
        """Apply custom CSS styling to the interface."""
        st.markdown("""
        <style>
    /* v3 - EXTREME top positioning */
    
    /* Remove ALL vertical spacing from root */
    .main > div:first-child {
        padding-top: 0 !important;
    }
    
    .appview-container {
        padding-top: 0 !important;
    }
    
    section.main > div {
        padding-top: 0 !important;
    }
    
    /* Hide Streamlit toolbar and header completely */
    div[data-testid="stToolbar"] { 
        display: none !important;
        height: 0 !important;
    }
    
    header[data-testid="stHeader"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
    }

    /* Hide user avatar/menu and cloud badges (Streamlit Cloud) */
    [data-testid="stUserMenu"],
    [data-testid="stDecoration"],
    .viewerBadge_link__container,
    a.viewerBadge_link__kKQ2J,
    a[href^="https://streamlit.io"],
    a[href*="share.streamlit.io"] {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }
    
    /* Hide Streamlit branding and menu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Force all containers to zero top spacing */
    [data-testid="stAppViewContainer"] {
        padding-top: 0 !important;
    }
    
    [data-testid="stAppViewContainer"] > section {
        padding-top: 0 !important;
    }
    
    .main {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    
    .block-container {
        padding-top: 1rem !important;
        margin-top: 0 !important;
        padding-bottom: 1rem !important;
    }
    
    /* Title styling - minimal top space */
    h1 {
        text-align: center;
        margin-top: 0 !important;
        padding-top: 0 !important;
        margin-bottom: 1rem !important;
        font-size: 1.8rem;
        line-height: 1.2;
    }
    
    /* Progress bar - clean spacing */
    .stProgress {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    .stProgress > div { 
        height: 6px; 
        border-radius: 3px; 
    }
    .stProgress > div > div { 
        border-radius: 3px; 
    }
    
    /* Message counter styling */
    .msg-counter { 
        text-align: right; 
        color: #9aa4af; 
        font-size: 0.9rem; 
        margin-top: 0.5rem;
    }
    
    /* Chat message styling */
    .stChatMessage {
        padding: 0.9rem;
        border-radius: 0.5rem;
        margin-bottom: 0.6rem;
    }
    
    /* Make chat input more prominent */
    .stChatInputContainer {
        border-top: 2px solid #f0f2f6;
        padding-top: 0.75rem;
        margin-top: 0.5rem;
    }
    
    /* Progress bar styling */
    .stProgress > div > div > div {
        background-color: #1f77b4;
    }

            /* Slim progress bar: reduce height and margins */
            .stProgress {
                margin-top: 0rem !important;
                margin-bottom: 0.2rem !important;
            }
            .stProgress > div { height: 4px; border-radius: 4px; }
            .stProgress > div > div { border-radius: 4px; }
            [data-testid="stCaptionContainer"] p {
                margin-top: 0rem !important;
                margin-bottom: 0.2rem !important;
                font-size: 0.85rem !important;
                color: #9aa4af !important;
            }

            /* Inline message counter next to progress */
            .msg-counter { text-align: right; color: #9aa4af; font-size: 0.85rem; margin-top: -2px; }

        /* Watermark is applied directly to .stApp background via inline CSS */

        /* Sticky disclaimer ribbon */
        .disclaimer-ribbon {
            position: fixed;
            bottom: 8px;
            right: 8px;
            z-index: 9999;
            background: rgba(255, 248, 225, 0.95);
            border: 1px solid #f0dba5;
            color: #4a3b18;
            font-size: 12px;
            line-height: 1.3;
            padding: 8px 10px;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            max-width: 360px;
        }
        .disclaimer-ribbon strong { color: #805800; }
        </style>
        """, unsafe_allow_html=True)

    def render_disclaimer(self, text: str | None = None):
        """Render a fixed-position disclaimer ribbon on the chat page."""
        message = text or (
            "This chat is part of a research study. Responses may be recorded for research purposes."
        )
        safe = _html.escape(message)
        st.markdown(
            f"<div class='disclaimer-ribbon'><strong>Research notice:</strong> {safe}</div>",
            unsafe_allow_html=True,
        )

    def render_watermark(self, text: str | None = None):
        """Set a tiled, slanted watermark as the page background (behind all content)."""
        label = text or "This chat is for research purposes"
        # Configurable color (defaults to light so it shows on dark bg)
        ui_cfg = self.config.get('ui') if isinstance(self.config.get('ui'), dict) else {}
        fill_color = None
        if isinstance(ui_cfg, dict):
            fill_color = ui_cfg.get('chat_watermark_color') or ui_cfg.get('watermark_color')
        if not isinstance(fill_color, str) or not fill_color.strip():
            # Light but slightly darker than before for better balance on dark backgrounds
            # Previously 0.16 alpha; nudged to 0.12 to reduce brightness a bit
            fill_color = 'rgba(255,255,255,0.12)'
        # Subtle dark stroke to improve readability on mixed backgrounds
        # Slightly soften stroke so the combined appearance isn't too stark
        stroke_color = 'rgba(0,0,0,0.16)'

        # Trim very long labels to avoid clipping within each tile
        max_len = 40
        short = (label[: max_len - 1] + "…") if len(label) > max_len else label
        esc = _html.escape(short)
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' width='600' height='600'>"
            "<defs><style>@import url('https://fonts.googleapis.com/css2?family=Inter:wght@500');</style></defs>"
            f"<g transform='rotate(-30 300 300)' fill='{fill_color}' stroke='{stroke_color}' stroke-width='0.6' style='paint-order: stroke fill' font-family='Inter, Arial, sans-serif' font-size='26' letter-spacing='1.2px'>"
            f"<text x='300' y='180' text-anchor='middle'>{esc}</text>"
            f"<text x='300' y='330' text-anchor='middle'>{esc}</text>"
            f"<text x='300' y='480' text-anchor='middle'>{esc}</text>"
            "</g></svg>"
        )
        data_url = "data:image/svg+xml;utf8," + _urlquote(svg)
        st.markdown(
            """
            <style>
            .stApp {
                background-image: url('REPLACE_URL');
                background-repeat: repeat;
                background-size: 600px 600px;
                background-attachment: fixed;
            }
            </style>
            """.replace('REPLACE_URL', data_url),
            unsafe_allow_html=True,
        )
    
    
    def initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        # Session management
        if 'session_id' not in st.session_state:
            st.session_state.session_id = None
        
        if 'participant_id' not in st.session_state:
            st.session_state.participant_id = None
        
        if 'bot_type' not in st.session_state:
            st.session_state.bot_type = None
        
        # External id (Prolific) captured at consent
        if 'prolific_id' not in st.session_state:
            st.session_state.prolific_id = None
        
        # Conversation state
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        
        if 'current_message_num' not in st.session_state:
            st.session_state.current_message_num = 0
        
        if 'conversation_active' not in st.session_state:
            st.session_state.conversation_active = False
        
        if 'conversation_complete' not in st.session_state:
            st.session_state.conversation_complete = False
        
        # UI state
        if 'show_welcome' not in st.session_state:
            st.session_state.show_welcome = True