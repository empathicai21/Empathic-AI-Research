"""
Database Models
Defines the structure of our SQLite database tables for storing conversation data.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

# Base class for all database models
Base = declarative_base()


 
# PARTICIPANTS TABLE
# Stores information about each participant
 
class Participant(Base):
    """
    Represents a single participant in the study.
    Each participant gets one conversation with one bot type.
    """
    __tablename__ = 'participants'
    
    # Primary key - unique identifier for each participant
    id = Column(String, primary_key=True)  # e.g., "P001", "P002"
    
    # Which bot type was assigned (emotional, cognitive, motivational, neutral)
    bot_type = Column(String, nullable=False)

    # Experimental condition: AI watermark visibility ("visible" or "hidden")
    # Added as an additive column to support 2x4 design without changing existing flows
    watermark_condition = Column(String, nullable=True)
    
    # Timestamps for conversation
    start_time = Column(DateTime, default=datetime.utcnow)  # When conversation started
    end_time = Column(DateTime, nullable=True)  # When conversation ended (null until finished)
    
    # Conversation metrics
    total_messages = Column(Integer, default=0)  # Total number of messages exchanged
    completed = Column(Boolean, default=False)  # Did they finish all 20 messages?
    
    # Crisis flag - did this conversation contain crisis keywords?
    crisis_flagged = Column(Boolean, default=False)
    
    # External identifier from Prolific (optional)
    prolific_id = Column(String, nullable=True)

    # Optional feedback at completion
    feedback_text = Column(Text, nullable=True)
    feedback_rating = Column(Integer, nullable=True)
    feedback_time = Column(DateTime, nullable=True)
    
    # Relationship: One participant has many messages
    messages = relationship("Message", back_populates="participant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Participant(id='{self.id}', bot_type='{self.bot_type}', messages={self.total_messages})>"


 
# MESSAGES TABLE
# Stores every individual message in conversations
 
class Message(Base):
    """
    Represents a single message in a conversation.
    Can be from either the user or the bot.
    """
    __tablename__ = 'messages'
    
    # Primary key - auto-incrementing ID
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key - links to participant
    participant_id = Column(String, ForeignKey('participants.id'), nullable=False)
    
    # Message details
    message_num = Column(Integer, nullable=False)  # Which message number (1-20)
    sender = Column(String, nullable=False)  # "user" or "bot"
    content = Column(Text, nullable=False)  # The actual message text
    timestamp = Column(DateTime, default=datetime.utcnow)  # When message was sent
    
    # Crisis detection
    contains_crisis_keyword = Column(Boolean, default=False)  # Does this message contain crisis keywords?
    
    # Relationship: Many messages belong to one participant
    participant = relationship("Participant", back_populates="messages")
    
    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(participant='{self.participant_id}', num={self.message_num}, sender='{self.sender}')>"


 
# CRISIS FLAGS TABLE
# Stores detailed information about crisis detections
 
class CrisisFlag(Base):
    """
    Records when crisis keywords are detected in conversations.
    Allows researchers to quickly identify conversations needing review.
    """
    __tablename__ = 'crisis_flags'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Which participant and message triggered the flag
    participant_id = Column(String, ForeignKey('participants.id'), nullable=False)
    message_id = Column(Integer, ForeignKey('messages.id'), nullable=False)
    
    # What triggered the flag
    keyword_detected = Column(String, nullable=False)  # Which crisis keyword was found
    flag_type = Column(String, default="automatic")  # "automatic" or "manual" if researcher adds
    
    # When and status
    timestamp = Column(DateTime, default=datetime.utcnow)
    reviewed = Column(Boolean, default=False)  # Has researcher reviewed this?
    notes = Column(Text, nullable=True)  # Researcher can add notes
    
    def __repr__(self):
        return f"<CrisisFlag(participant='{self.participant_id}', keyword='{self.keyword_detected}', reviewed={self.reviewed})>"


 
# EXPORT METADATA TABLE (Optional)
# Tracks when data was exported for research analysis
 
class ExportLog(Base):
    """
    Records when data exports were performed.
    Helps track which data was used for which analysis.
    """
    __tablename__ = 'export_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    export_time = Column(DateTime, default=datetime.utcnow)
    export_type = Column(String)  # "csv", "excel", "json"
    num_participants = Column(Integer)  # How many participants were exported
    num_messages = Column(Integer)  # How many total messages
    file_path = Column(String)  # Where the export was saved
    notes = Column(Text, nullable=True)  # Any notes about this export
    
    def __repr__(self):
        return f"<ExportLog(type='{self.export_type}', participants={self.num_participants}, time={self.export_time})>"