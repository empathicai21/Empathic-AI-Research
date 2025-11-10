"""
Database Manager
Handles all database operations including creating tables, saving data, and retrieving information.
"""

import sqlite3
from sqlalchemy import create_engine, inspect, text, func
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import List, Optional, Dict
import os

# Import our database models
from src.database.models import Base, Participant, Message, CrisisFlag, ExportLog


class DatabaseManager:
    """
    Manages all database operations for the research platform.
    Handles creating, reading, updating data in SQLite database.
    """
    
    def __init__(self, db_path: str = "data/database/conversations.db", db_url: str | None = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file (ignored if DATABASE_URL is set or db_url provided)
            db_url: Optional full SQLAlchemy URL (e.g., postgresql+psycopg2://user:pass@host:5432/db)
        """
        # Prefer explicit URL parameter, then environment variable; also support Streamlit Secrets
        env_url = os.getenv("DATABASE_URL")
        if not env_url:
            try:
                import streamlit as st  # type: ignore
                env_url = st.secrets.get("DATABASE_URL") if hasattr(st, "secrets") else None
            except Exception:
                env_url = None
        url = db_url if db_url else env_url

        if not url:
            # If db_path looks like a URL already, use it directly
            if "://" in db_path:
                url = db_path
            elif db_path == ":memory:":
                # Handle in-memory SQLite database
                url = "sqlite:///:memory:"
            else:
                # Default to SQLite file; ensure directory exists
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                url = f"sqlite:///{db_path}"

        # Create database engine
        self.engine = create_engine(url, echo=False, pool_pre_ping=True)
        
        # Create all tables if they don't exist
        Base.metadata.create_all(self.engine)
        # Apply lightweight schema migrations (non-destructive)
        self._apply_migrations()
        # Create helpful indexes (best-effort)
        self._create_indexes()
        
        # Create session factory for database operations
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Friendly notice (avoid printing secrets)
        try:
            if url.startswith("sqlite:///"):
                print(f"✓ Database initialized at: {db_path}")
            else:
                scheme = url.split(":", 1)[0]
                print(f"✓ Database initialized via {scheme} (DATABASE_URL)")
        except UnicodeEncodeError:
            # Fallback for terminals that don't support Unicode
            if url.startswith("sqlite:///"):
                print(f"[OK] Database initialized at: {db_path}")
            else:
                scheme = url.split(":", 1)[0]
                print(f"[OK] Database initialized via {scheme} (DATABASE_URL)")
    
    
    def get_session(self) -> Session:
        """
        Get a new database session for operations.
        
        Returns:
            SQLAlchemy session object
        """
        return self.SessionLocal()
    
    
     
    # PARTICIPANT OPERATIONS
     
    
    def create_participant(self, participant_id: str, bot_type: str, prolific_id: Optional[str] = None, watermark_condition: Optional[str] = None) -> Participant:
        """
        Create a new participant in the database.
        
        Args:
            participant_id: Unique ID (e.g., "P001")
            bot_type: Which bot assigned ("emotional", "cognitive", "motivational", "neutral")
            
        Returns:
            Created Participant object
        """
        session = self.get_session()
        
        try:
            # Create new participant
            participant = Participant(
                id=participant_id,
                bot_type=bot_type,
                watermark_condition=(watermark_condition or 'visible'),
                start_time=datetime.utcnow(),
                total_messages=0,
                completed=False,
                crisis_flagged=False,
                prolific_id=prolific_id
            )
            
            # Add to database
            session.add(participant)
            session.commit()
            session.refresh(participant)
            
            print(f"✓ Created participant: {participant_id} with {bot_type} bot")
            return participant
            
        except Exception as e:
            session.rollback()
            print(f"✗ Error creating participant: {e}")
            raise
        finally:
            session.close()

    def set_participant_prolific_id(self, participant_id: str, prolific_id: str) -> None:
        """Update or set the Prolific ID for a participant."""
        session = self.get_session()
        try:
            p = session.query(Participant).filter_by(id=participant_id).first()
            if p:
                p.prolific_id = prolific_id
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_participant_by_prolific(self, prolific_id: str) -> Optional[Participant]:
        """Find a participant via Prolific ID."""
        session = self.get_session()
        try:
            return session.query(Participant).filter_by(prolific_id=prolific_id).first()
        finally:
            session.close()

    def set_participant_feedback(self, participant_id: str, text: Optional[str], rating: Optional[int] = None) -> None:
        """Store optional feedback for a participant and timestamp it."""
        session = self.get_session()
        try:
            p = session.query(Participant).filter_by(id=participant_id).first()
            if not p:
                return
            p.feedback_text = (text or '').strip() or None
            try:
                p.feedback_rating = int(rating) if rating is not None else None
            except Exception:
                p.feedback_rating = None
            p.feedback_time = datetime.utcnow()
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _apply_migrations(self):
        """Lightweight, safe migrations: add columns if missing."""
        try:
            inspector = inspect(self.engine)
            cols = {c['name'] for c in inspector.get_columns('participants')}
            if 'prolific_id' not in cols:
                # Add prolific_id column; NULLABLE
                with self.engine.connect() as conn:
                    # Works for Postgres and SQLite
                    conn.execute(text('ALTER TABLE participants ADD COLUMN prolific_id VARCHAR'))
                    conn.commit()
            # Feedback columns (all nullable, additive)
            if 'feedback_text' not in cols:
                with self.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE participants ADD COLUMN feedback_text TEXT'))
                    conn.commit()
            if 'feedback_rating' not in cols:
                with self.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE participants ADD COLUMN feedback_rating INTEGER'))
                    conn.commit()
            if 'feedback_time' not in cols:
                with self.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE participants ADD COLUMN feedback_time TIMESTAMP'))
                    conn.commit()
            # Add watermark_condition column for 2x4 design if missing
            if 'watermark_condition' not in cols:
                with self.engine.connect() as conn:
                    # Use TEXT/VARCHAR without NOT NULL for broad dialect compatibility
                    conn.execute(text("ALTER TABLE participants ADD COLUMN watermark_condition VARCHAR"))
                    conn.commit()
        except Exception:
            # If anything fails (e.g., permissions), we ignore; Base metadata still works for new DBs
            pass

    def _create_indexes(self):
        """Create helpful indexes if they don't exist (best-effort)."""
        stmts = [
            # Messages lookup and ordering
            "CREATE INDEX IF NOT EXISTS ix_messages_participant_id ON messages (participant_id)",
            "CREATE INDEX IF NOT EXISTS ix_messages_participant_id_message_num ON messages (participant_id, message_num)",
            # Participants filters in admin
            "CREATE INDEX IF NOT EXISTS ix_participants_bot_type ON participants (bot_type)",
            "CREATE INDEX IF NOT EXISTS ix_participants_completed ON participants (completed)",
            # Crisis flags workflow
            "CREATE INDEX IF NOT EXISTS ix_crisis_flags_reviewed ON crisis_flags (reviewed)",
            "CREATE INDEX IF NOT EXISTS ix_crisis_flags_timestamp ON crisis_flags (timestamp)"
        ]
        try:
            with self.engine.connect() as conn:
                for stmt in stmts:
                    try:
                        conn.execute(text(stmt))
                    except Exception:
                        # Some dialects (older SQLite) may not support IF NOT EXISTS for indexes; ignore failures
                        pass
                try:
                    conn.commit()
                except Exception:
                    pass
        except Exception:
            # Best-effort only
            pass
    
    
    def get_participant(self, participant_id: str) -> Optional[Participant]:
        """
        Retrieve participant from database.
        
        Args:
            participant_id: The participant's ID
            
        Returns:
            Participant object or None if not found
        """
        session = self.get_session()
        
        try:
            participant = session.query(Participant).filter_by(id=participant_id).first()
            return participant
        finally:
            session.close()
    
    
    def update_participant_completion(self, participant_id: str, completed: bool = True):
        """
        Mark participant's conversation as completed.
        
        Args:
            participant_id: The participant's ID
            completed: Whether they completed the full conversation
        """
        session = self.get_session()
        
        try:
            participant = session.query(Participant).filter_by(id=participant_id).first()
            
            if participant:
                participant.completed = completed
                participant.end_time = datetime.utcnow()
                session.commit()
                print(f"✓ Updated participant {participant_id} completion status")
            
        except Exception as e:
            session.rollback()
            print(f"✗ Error updating participant: {e}")
        finally:
            session.close()

    # Backward-compatible alias used by app.py
    def mark_participant_completed(self, participant_id: str):
        """Mark participant as completed (alias)."""
        return self.update_participant_completion(participant_id, completed=True)
    
    
    def get_all_participants(self) -> List[Participant]:
        """
        Get all participants from database.
        
        Returns:
            List of all Participant objects
        """
        session = self.get_session()
        
        try:
            participants = session.query(Participant).all()
            return participants
        finally:
            session.close()
    
    
     
    # MESSAGE OPERATIONS
     
    
    def save_message(self, participant_id: str, message_num: int, 
                    sender: str, content: str, 
                    contains_crisis_keyword: bool = False) -> Message:
        """
        Save a single message to the database.
        
        Args:
            participant_id: Which participant sent/received this message
            message_num: Message number (1-20)
            sender: "user" or "bot"
            content: The actual message text
            contains_crisis_keyword: Does this message contain crisis keywords?
            
        Returns:
            Created Message object
        """
        session = self.get_session()
        
        try:
            # Create new message
            message = Message(
                participant_id=participant_id,
                message_num=message_num,
                sender=sender,
                content=content,
                timestamp=datetime.utcnow(),
                contains_crisis_keyword=contains_crisis_keyword
            )
            
            # Add to database
            session.add(message)
            
            # Update participant's total message count (count user turns only)
            participant = session.query(Participant).filter_by(id=participant_id).first()
            if participant:
                if sender == 'user':
                    participant.total_messages += 1
                
                # If crisis keyword detected, flag participant
                if contains_crisis_keyword:
                    participant.crisis_flagged = True
            
            session.commit()
            session.refresh(message)
            
            print(f"✓ Saved message {message_num} from {sender}")
            return message
            
        except Exception as e:
            session.rollback()
            print(f"✗ Error saving message: {e}")
            raise
        finally:
            session.close()
    
    
    def get_conversation(self, participant_id: str) -> List[Message]:
        """
        Get all messages for a specific participant (entire conversation).
        
        Args:
            participant_id: The participant's ID
            
        Returns:
            List of Message objects ordered by message number
        """
        session = self.get_session()
        
        try:
            # Order by message number and stable ID so user then bot with same number stays in sequence
            messages = (
                session.query(Message)
                .filter_by(participant_id=participant_id)
                .order_by(Message.message_num.asc(), Message.id.asc())
                .all()
            )
            return messages
        finally:
            session.close()
    
    
    def get_all_messages(self) -> List[Message]:
        """
        Get ALL messages from ALL participants.
        
        Returns:
            List of all Message objects
        """
        session = self.get_session()
        
        try:
            messages = session.query(Message).all()
            return messages
        finally:
            session.close()
    
    
     
    # CRISIS FLAG OPERATIONS
     
    
    def create_crisis_flag(self, participant_id: str, message_id: int, 
                          keyword_detected: str) -> CrisisFlag:
        """
        Create a crisis flag when crisis keywords are detected.
        
        Args:
            participant_id: Which participant
            message_id: Which message triggered the flag
            keyword_detected: Which crisis keyword was found
            
        Returns:
            Created CrisisFlag object
        """
        session = self.get_session()
        
        try:
            crisis_flag = CrisisFlag(
                participant_id=participant_id,
                message_id=message_id,
                keyword_detected=keyword_detected,
                flag_type="automatic",
                timestamp=datetime.utcnow(),
                reviewed=False
            )
            
            session.add(crisis_flag)
            session.commit()
            session.refresh(crisis_flag)
            
            print(f"⚠ Crisis flag created for participant {participant_id}")
            return crisis_flag
            
        except Exception as e:
            session.rollback()
            print(f"✗ Error creating crisis flag: {e}")
            raise
        finally:
            session.close()
    
    
    def get_unreviewed_crisis_flags(self) -> List[CrisisFlag]:
        """
        Get all crisis flags that haven't been reviewed yet.
        
        Returns:
            List of unreviewed CrisisFlag objects
        """
        session = self.get_session()
        
        try:
            flags = session.query(CrisisFlag)\
                .filter_by(reviewed=False)\
                .order_by(CrisisFlag.timestamp.desc())\
                .all()
            return flags
        finally:
            session.close()

    def mark_crisis_flag_reviewed(self, flag_id: int) -> None:
        """Mark a crisis flag as reviewed."""
        session = self.get_session()
        try:
            flag = session.query(CrisisFlag).filter_by(id=flag_id).first()
            if flag and not flag.reviewed:
                flag.reviewed = True
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    
     
    # STATISTICS & ANALYTICS
     
    
    def get_statistics(self) -> Dict:
        """
        Get overall statistics about the study.
        
        Returns:
            Dictionary with various statistics
        """
        session = self.get_session()
        
        try:
            total_participants = session.query(Participant).count()
            completed_conversations = session.query(Participant).filter_by(completed=True).count()
            total_messages = session.query(Message).count()
            crisis_flags = session.query(CrisisFlag).count()
            
            # Count by bot type dynamically (handles any bot type variations)
            bot_counts = {}
            rows = (
                session.query(Participant.bot_type, func.count(Participant.id))
                .group_by(Participant.bot_type)
                .all()
            )
            for bot_type, count in rows:
                bot_counts[bot_type] = count
            
            stats = {
                'total_participants': total_participants,
                'completed_conversations': completed_conversations,
                'total_messages': total_messages,
                'crisis_flags': crisis_flags,
                'bot_distribution': bot_counts
            }
            
            return stats
            
        finally:
            session.close()

    def get_distinct_bot_types(self) -> List[str]:
        """Return a list of distinct bot types present in the database."""
        session = self.get_session()
        try:
            types = [row[0] for row in session.query(Participant.bot_type).distinct().all()]
            return sorted(t for t in types if t)
        finally:
            session.close()
    
    
     
    # DATABASE MAINTENANCE
     
    
    def close(self):
        """Close database connection."""
        self.engine.dispose()
        print("✓ Database connection closed")