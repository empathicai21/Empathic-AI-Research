"""
Empathy Bots - OpenAI ChatGPT API Only
Defines the 4 chatbot types and handles generating responses via OpenAI API.
"""

import os
from typing import Optional, Dict, List
from datetime import datetime


class EmpathyBot:
    """
    Base class for all empathy chatbots using OpenAI ChatGPT API.
    Handles common functionality like API calls and prompt loading.
    """
    
    def __init__(self, bot_type: str, api_key: str, model: str = "gpt-4"):
        """
        Initialize empathy bot with OpenAI.
        
        Args:
            bot_type: Type of bot ("emotional", "cognitive", "motivational", "neutral")
            api_key: OpenAI API key
            model: OpenAI model to use (gpt-4, gpt-3.5-turbo, etc.)
        """
        self.bot_type = bot_type
        self.model = model
        self.system_prompt = self._load_prompt()
        self.conversation_history = []  # Store conversation context
        
        # Initialize OpenAI client
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
        
        print(f"✓ Initialized {bot_type} empathy bot with OpenAI {model}")
    
    
    def _load_prompt(self) -> str:
        """
        Load system prompt from file based on bot type.
        
        Returns:
            System prompt text
        """
        # Map bot types to prompt files
        prompt_files = {
            'emotional': 'config/emotional_empathy_prompt.txt',
            'cognitive': 'config/cognitive_empathy_prompt.txt',
            'motivational': 'config/motivational_empathy_prompt.txt',
            'neutral': 'config/neutral_empathy_prompt.txt'
        }
        
        prompt_file = prompt_files.get(self.bot_type)
        
        # Load prompt from file
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt = f.read().strip()
            print(f"  ✓ Loaded prompt from {prompt_file}")
            return prompt
        except Exception as e:
            print(f"  ✗ Error loading prompt file: {e}")
            return ""
    
    
    def add_to_history(self, role: str, content: str):
        """
        Add message to conversation history for context.
        
        Args:
            role: "user" or "assistant"
            content: Message text
        """
        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow()
        })
    
    
    def get_conversation_context(self, max_messages: int = 10) -> List[Dict]:
        """
        Get recent conversation history for context.
        
        Args:
            max_messages: Maximum number of recent messages to include
            
        Returns:
            List of message dictionaries
        """
        # Return last N messages for context
        return self.conversation_history[-max_messages:]
    
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        print(f"  ✓ Cleared conversation history")
    
    
    def generate_response(self, user_message: str, crisis_mode: bool = False) -> str:
        """
        Generate response using OpenAI ChatGPT API.
        
        Args:
            user_message: User's message
            crisis_mode: If True, return crisis response
            
        Returns:
            Bot's response text
        """
        try:
            # If crisis mode, return crisis response immediately
            if crisis_mode:
                with open('config/crisis_response.txt', 'r') as f:
                    return f.read().strip()
            
            # Add user message to history
            self.add_to_history('user', user_message)
            
            # Prepare messages for OpenAI API
            messages = []
            
            # Add system prompt if exists (not for neutral bot)
            if self.system_prompt:
                messages.append({
                    "role": "system",
                    "content": self.system_prompt
                })
            
            # Add conversation history
            context = self.get_conversation_context(max_messages=10)
            for msg in context:
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            # Extract response text
            bot_response = response.choices[0].message.content
            
            # Add to history
            self.add_to_history('assistant', bot_response)
            
            return bot_response
            
        except Exception as e:
            print(f"✗ Error generating response: {e}")
            return "I apologize, but I'm having trouble responding right now. Please try again."


class OpenAIEmpathyBot(EmpathyBot):
    """
    OpenAI-powered empathy bot (simplified version).
    """
    
    def __init__(self, bot_type: str, api_key: str, model: str = "gpt-4"):
        """
        Initialize OpenAI empathy bot.
        
        Args:
            bot_type: Type of bot
            api_key: OpenAI API key  
            model: OpenAI model to use
        """
        super().__init__(bot_type, api_key, model)
    
    

def create_bot(bot_type: str, api_key: str, model: str = None) -> EmpathyBot:
    """
    Factory function to create OpenAI empathy bot.
    
    Args:
        bot_type: Type of empathy bot ("emotional", "cognitive", "motivational", "neutral")
        api_key: OpenAI API key
        model: Optional specific model to use (defaults to gpt-4)
        
    Returns:
        Initialized OpenAI bot instance
    """
    model = model or "gpt-4"
    return OpenAIEmpathyBot(bot_type, api_key, model)