"""
CSV Exporter
Handles exporting conversation data from database to CSV files for research analysis.
"""

import csv
import pandas as pd
from datetime import datetime
from src.utils.timezone import fmt_az, now_az
from typing import List, Dict
import os

from src.database.db_manager import DatabaseManager
from src.database.models import Participant, Message, CrisisFlag


class CSVExporter:
    """
    Exports database data to CSV format for research analysis.
    Creates analysis-ready CSV files from conversation data.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize CSV exporter with database manager.
        
        Args:
            db_manager: DatabaseManager instance to get data from
        """
        self.db_manager = db_manager
        self.export_dir = "data/exports/"
        
        # Ensure export directory exists
        os.makedirs(self.export_dir, exist_ok=True)
    
    
     
    # MAIN EXPORT FUNCTIONS
     
    
    def export_all_conversations(self, filename: str = None) -> str:
        """
        Export all conversations to a single CSV file.
        Each row is one message with participant and bot information.
        
        Args:
            filename: Optional custom filename. If None, generates timestamped name.
            
        Returns:
            Path to created CSV file
        """
        # Generate filename if not provided
        if filename is None:
            timestamp = now_az().strftime("%Y%m%d_%H%M%S")
            filename = f"all_conversations_{timestamp}.csv"
        
        filepath = os.path.join(self.export_dir, filename)
        
        # Get all messages from database
        messages = self.db_manager.get_all_messages()
        # Stable ordering by participant, message_num, then id
        try:
            messages.sort(key=lambda m: (m.participant_id, m.message_num, m.id))
        except Exception:
            pass
        
        # Prepare data for CSV
        rows = []
        # Prefetch participants to avoid N+1 queries
        session = self.db_manager.get_session()
        try:
            parts = session.query(Participant).all()
            part_map = {p.id: p for p in parts}
        finally:
            session.close()

        for msg in messages:
            participant = part_map.get(msg.participant_id)
            
            row = {
                'participant_id': msg.participant_id,
                'bot_type': participant.bot_type if participant else 'unknown',
                'watermark_condition': getattr(participant, 'watermark_condition', None) if participant else None,
                'message_num': msg.message_num,
                'sender': msg.sender,
                'message_text': msg.content,
                'timestamp_az': fmt_az(msg.timestamp, "%Y-%m-%d %H:%M:%S"),
                'contains_crisis_keyword': msg.contains_crisis_keyword,
                'conversation_completed': participant.completed if participant else False
            }
            rows.append(row)
        
        # Write to CSV
        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(filepath, index=False, encoding='utf-8')
            print(f"✓ Exported {len(rows)} messages to: {filepath}")
        else:
            print("⚠ No messages to export")
        
        return filepath
    
    
    def export_participant_summary(self, filename: str = None) -> str:
        """
        Export summary information about each participant.
        One row per participant with their statistics.
        
        Args:
            filename: Optional custom filename
            
        Returns:
            Path to created CSV file
        """
        # Generate filename if not provided
        if filename is None:
            timestamp = now_az().strftime("%Y%m%d_%H%M%S")
            filename = f"participant_summary_{timestamp}.csv"
        
        filepath = os.path.join(self.export_dir, filename)
        
        # Get all participants
        participants = self.db_manager.get_all_participants()
        
        # Prepare data
        rows = []
        for p in participants:
            # Calculate conversation duration if completed
            duration_minutes = None
            if p.end_time and p.start_time:
                duration = p.end_time - p.start_time
                duration_minutes = duration.total_seconds() / 60
            
            row = {
                'participant_id': p.id,
                'prolific_id': getattr(p, 'prolific_id', None),
                'bot_type': p.bot_type,
                'watermark_condition': getattr(p, 'watermark_condition', None),
                'start_time_az': fmt_az(p.start_time, "%Y-%m-%d %H:%M:%S"),
                'end_time_az': fmt_az(p.end_time, "%Y-%m-%d %H:%M:%S") if p.end_time else None,
                'duration_minutes': round(duration_minutes, 2) if duration_minutes else None,
                'total_messages': p.total_messages,
                'completed': p.completed,
                'crisis_flagged': p.crisis_flagged,
                'feedback_rating': getattr(p, 'feedback_rating', None),
                'feedback_time_az': fmt_az(getattr(p, 'feedback_time', None), "%Y-%m-%d %H:%M:%S"),
                'feedback_text': getattr(p, 'feedback_text', None)
            }
            rows.append(row)
        
        # Write to CSV
        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(filepath, index=False, encoding='utf-8')
            print(f"✓ Exported {len(rows)} participant summaries to: {filepath}")
        else:
            print("⚠ No participants to export")
        
        return filepath
    
    
    def export_crisis_flags(self, filename: str = None) -> str:
        """
        Export all crisis flag events for review.
        
        Args:
            filename: Optional custom filename
            
        Returns:
            Path to created CSV file
        """
        # Generate filename if not provided
        if filename is None:
            timestamp = now_az().strftime("%Y%m%d_%H%M%S")
            filename = f"crisis_flags_{timestamp}.csv"
        
        filepath = os.path.join(self.export_dir, filename)
        
        # Get all crisis flags
        session = self.db_manager.get_session()
        try:
            crisis_flags = session.query(CrisisFlag).all()
            
            # Prepare data
            rows = []
            for flag in crisis_flags:
                # Get the message content
                message = session.query(Message).filter_by(id=flag.message_id).first()
                
                row = {
                    'participant_id': flag.participant_id,
                    'message_id': flag.message_id,
                    'message_text': message.content if message else 'N/A',
                    'keyword_detected': flag.keyword_detected,
                    'timestamp_az': fmt_az(flag.timestamp, "%Y-%m-%d %H:%M:%S"),
                    'reviewed': flag.reviewed,
                    'notes': flag.notes if flag.notes else ''
                }
                rows.append(row)
            
            # Write to CSV
            if rows:
                df = pd.DataFrame(rows)
                df.to_csv(filepath, index=False, encoding='utf-8')
                print(f"✓ Exported {len(rows)} crisis flags to: {filepath}")
            else:
                print("⚠ No crisis flags to export")
            
        finally:
            session.close()
        
        return filepath
    
    
    def export_bot_comparison(self, filename: str = None) -> str:
        """
        Export data structured for comparing bot types.
        Aggregated statistics per bot type.
        
        Args:
            filename: Optional custom filename
            
        Returns:
            Path to created CSV file
        """
        # Generate filename if not provided
        if filename is None:
            timestamp = now_az().strftime("%Y%m%d_%H%M%S")
            filename = f"bot_comparison_{timestamp}.csv"
        
        filepath = os.path.join(self.export_dir, filename)
        
        # Get statistics by bot type
        bot_types = ['emotional', 'cognitive', 'motivational', 'neutral']
        rows = []
        
        for bot_type in bot_types:
            session = self.db_manager.get_session()
            try:
                # Get participants for this bot type
                participants = session.query(Participant).filter_by(bot_type=bot_type).all()
                
                if not participants:
                    continue
                
                # Calculate statistics
                total_participants = len(participants)
                completed = sum(1 for p in participants if p.completed)
                total_messages = sum(p.total_messages for p in participants)
                avg_messages = total_messages / total_participants if total_participants > 0 else 0
                crisis_flagged = sum(1 for p in participants if p.crisis_flagged)
                
                row = {
                    'bot_type': bot_type,
                    'total_participants': total_participants,
                    'completed_conversations': completed,
                    'completion_rate': round(completed / total_participants * 100, 2) if total_participants > 0 else 0,
                    'total_messages': total_messages,
                    'avg_messages_per_participant': round(avg_messages, 2),
                    'crisis_flags': crisis_flagged
                }
                rows.append(row)
                
            finally:
                session.close()
        
        # Write to CSV
        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(filepath, index=False, encoding='utf-8')
            print(f"✓ Exported bot comparison data to: {filepath}")
        else:
            print("⚠ No data to export")
        
        return filepath
    
    
     
    # CONVENIENCE FUNCTION
     
    
    def export_all(self) -> Dict[str, str]:
        """
        Export all data types at once.
        Creates all standard export files.
        
        Returns:
            Dictionary with keys being export type and values being file paths
        """
        print("Starting full data export...")
        
        exports = {
            'all_conversations': self.export_all_conversations(),
            'participant_summary': self.export_participant_summary(),
            'crisis_flags': self.export_crisis_flags(),
            'bot_comparison': self.export_bot_comparison()
        }
        
        print(f"\n✓ Export complete! All files saved to: {self.export_dir}")
        return exports
    
    
     
    # UTILITY FUNCTIONS
     
    
    def get_conversation_as_dict(self, participant_id: str) -> List[Dict]:
        """
        Get a single conversation formatted as list of dictionaries.
        Useful for individual conversation analysis.
        
        Args:
            participant_id: The participant's ID
            
        Returns:
            List of message dictionaries
        """
        messages = self.db_manager.get_conversation(participant_id)
        
        conversation = []
        for msg in messages:
            conversation.append({
                'message_num': msg.message_num,
                'sender': msg.sender,
                'content': msg.content,
                'timestamp': msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return conversation