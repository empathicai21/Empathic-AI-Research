"""
Crisis Detector
Monitors messages for crisis keywords and triggers safety responses.
"""

import re
from typing import List, Tuple, Optional
import yaml


class CrisisDetector:
    """
    Detects crisis-related content in user messages.
    Monitors for keywords indicating suicide risk, self-harm, or immediate danger.
    """
    
    def __init__(self, config_path: str = "config/app_config.yaml"):
        """
        Initialize crisis detector with keywords from config.
        
        Args:
            config_path: Path to application configuration file
        """
        # Load crisis keywords from config
        self.crisis_keywords = self._load_keywords(config_path)
        
        # Compile regex patterns for faster matching
        self.patterns = self._compile_patterns()
        
        print(f"✓ Crisis detector initialized with {len(self.crisis_keywords)} keywords")
    
    
    def _load_keywords(self, config_path: str) -> List[str]:
        """
        Load crisis keywords from configuration file.
        
        Args:
            config_path: Path to config YAML file
            
        Returns:
            List of crisis keywords
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            keywords = config.get('safety', {}).get('crisis_keywords', [])
            
            # Add some default keywords if config is empty
            if not keywords:
                keywords = [
                    'suicide', 'kill myself', 'end it all', 
                    'want to die', 'no reason to live', 'better off dead'
                ]
            
            return keywords
            
        except Exception as e:
            print(f"⚠ Error loading crisis keywords from config: {e}")
            # Return default keywords
            return ['suicide', 'kill myself', 'end it all', 'want to die']
    
    
    def _compile_patterns(self) -> List[re.Pattern]:
        """
        Compile regex patterns for crisis keyword detection.
        Uses word boundaries to avoid false positives.
        
        Returns:
            List of compiled regex patterns
        """
        patterns = []
        
        for keyword in self.crisis_keywords:
            # Create pattern with word boundaries (avoids matching partial words)
            # Case-insensitive matching
            pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
            patterns.append(pattern)
        
        return patterns
    
    
    def check_message(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        Check if message contains crisis keywords.
        
        Args:
            message: User's message text to check
            
        Returns:
            Tuple of (is_crisis, detected_keyword)
            - is_crisis: True if crisis keyword detected
            - detected_keyword: The keyword that was found (or None)
        """
        # Check each pattern
        for pattern, keyword in zip(self.patterns, self.crisis_keywords):
            if pattern.search(message):
                print(f"⚠ CRISIS KEYWORD DETECTED: '{keyword}'")
                return True, keyword
        
        return False, None
    
    
    def get_crisis_response(self) -> str:
        """
        Get the standard crisis response message.
        This should be sent to user if crisis keyword is detected.
        
        Returns:
            Crisis response text
        """
        try:
            # Try to load from crisis_response.txt file
            with open('config/crisis_response.txt', 'r') as f:
                response = f.read().strip()
            return response
        except Exception:
            # Fallback crisis response if file not found
            return """I'm concerned about what you're sharing and want you to know that help is available right now.

If you're in immediate danger, please call 911.

For crisis support:
- Call or text 988 (Suicide & Crisis Lifeline)
- Text HOME to 741741 (Crisis Text Line)

I'm not a licensed therapist, but these trained professionals can provide immediate, specialized support. Your life matters, and there are people who want to help you through this difficult time."""
    
    
    def should_flag_conversation(self, message: str) -> bool:
        """
        Determine if this message should flag the entire conversation for review.
        
        Args:
            message: User's message text
            
        Returns:
            True if conversation should be flagged for researcher review
        """
        is_crisis, _ = self.check_message(message)
        return is_crisis
    
    
    def get_keyword_list(self) -> List[str]:
        """
        Get list of all crisis keywords being monitored.
        
        Returns:
            List of crisis keywords
        """
        return self.crisis_keywords.copy()
    
    
    def add_keyword(self, keyword: str):
        """
        Add a new crisis keyword to monitor.
        
        Args:
            keyword: New keyword to add
        """
        if keyword not in self.crisis_keywords:
            self.crisis_keywords.append(keyword)
            # Recompile patterns
            self.patterns = self._compile_patterns()
            print(f"✓ Added crisis keyword: '{keyword}'")
    
    
    def remove_keyword(self, keyword: str):
        """
        Remove a crisis keyword from monitoring.
        
        Args:
            keyword: Keyword to remove
        """
        if keyword in self.crisis_keywords:
            self.crisis_keywords.remove(keyword)
            # Recompile patterns
            self.patterns = self._compile_patterns()
            print(f"✓ Removed crisis keyword: '{keyword}'")