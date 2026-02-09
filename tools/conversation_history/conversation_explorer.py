#!/usr/bin/env python3
"""
Conversation History Explorer for Claude Code
Following SOLID principles for scalability and maintainability
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Protocol


# ============================================================================
# Domain Models (Data Transfer Objects)
# ============================================================================

@dataclass
class ConversationMessage:
    """Represents a single conversation message"""
    display: str
    timestamp: int
    project: str
    session_id: str
    pasted_contents: Dict[str, Any]

    @property
    def datetime(self) -> datetime:
        """Convert timestamp to datetime object"""
        return datetime.fromtimestamp(self.timestamp / 1000)

    @property
    def time_ago(self) -> str:
        """Human-readable time difference"""
        now = datetime.now()
        diff = now - self.datetime

        if diff < timedelta(minutes=1):
            return "just now"
        elif diff < timedelta(hours=1):
            mins = int(diff.total_seconds() / 60)
            return f"{mins} minute{'s' if mins != 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"


@dataclass
class ConversationSession:
    """Represents a complete conversation session"""
    session_id: str
    messages: List[ConversationMessage]
    project: str

    @property
    def start_time(self) -> datetime:
        """Get the start time of the session"""
        return min(msg.datetime for msg in self.messages)

    @property
    def end_time(self) -> datetime:
        """Get the end time of the session"""
        return max(msg.datetime for msg in self.messages)

    @property
    def duration(self) -> timedelta:
        """Get the duration of the session"""
        return self.end_time - self.start_time

    @property
    def message_count(self) -> int:
        """Get the number of messages in the session"""
        return len(self.messages)


# ============================================================================
# Repository Pattern (Data Access Layer)
# ============================================================================

class IConversationRepository(ABC):
    """Interface for conversation data access - Dependency Inversion Principle"""

    @abstractmethod
    def read_all_messages(self) -> List[ConversationMessage]:
        """Read all conversation messages"""
        pass

    @abstractmethod
    def get_sessions(self) -> List[ConversationSession]:
        """Get all conversation sessions"""
        pass


class JSONLConversationRepository(IConversationRepository):
    """Reads conversations from JSONL file - Single Responsibility Principle"""

    def __init__(self, history_file_path: Path):
        self.history_file_path = history_file_path

    def read_all_messages(self) -> List[ConversationMessage]:
        """Read and parse all messages from history.jsonl"""
        messages = []

        if not self.history_file_path.exists():
            raise FileNotFoundError(f"History file not found: {self.history_file_path}")

        with open(self.history_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    messages.append(ConversationMessage(
                        display=data.get('display', ''),
                        timestamp=data.get('timestamp', 0),
                        project=data.get('project', ''),
                        session_id=data.get('sessionId', ''),
                        pasted_contents=data.get('pastedContents', {})
                    ))

        return messages

    def get_sessions(self) -> List[ConversationSession]:
        """Group messages by session ID"""
        messages = self.read_all_messages()
        sessions_dict: Dict[str, List[ConversationMessage]] = {}

        for msg in messages:
            if msg.session_id not in sessions_dict:
                sessions_dict[msg.session_id] = []
            sessions_dict[msg.session_id].append(msg)

        sessions = []
        for session_id, msgs in sessions_dict.items():
            # Sort messages by timestamp
            msgs.sort(key=lambda x: x.timestamp)
            sessions.append(ConversationSession(
                session_id=session_id,
                messages=msgs,
                project=msgs[0].project if msgs else ''
            ))

        # Sort sessions by start time (most recent first)
        sessions.sort(key=lambda x: x.start_time, reverse=True)
        return sessions


# ============================================================================
# Filter Strategy Pattern (Open/Closed Principle)
# ============================================================================

class IConversationFilter(ABC):
    """Interface for filtering conversations"""

    @abstractmethod
    def filter(self, sessions: List[ConversationSession]) -> List[ConversationSession]:
        """Filter sessions based on criteria"""
        pass


class TimeRangeFilter(IConversationFilter):
    """Filter sessions by time range"""

    def __init__(self, minutes_ago: Optional[int] = None,
                 hours_ago: Optional[int] = None,
                 days_ago: Optional[int] = None):
        self.time_delta = timedelta(
            minutes=minutes_ago or 0,
            hours=hours_ago or 0,
            days=days_ago or 0
        )

    def filter(self, sessions: List[ConversationSession]) -> List[ConversationSession]:
        """Filter sessions within the specified time range"""
        if self.time_delta.total_seconds() == 0:
            return sessions

        cutoff_time = datetime.now() - self.time_delta
        return [s for s in sessions if s.start_time >= cutoff_time]


class ProjectFilter(IConversationFilter):
    """Filter sessions by project"""

    def __init__(self, project_path: str):
        self.project_path = project_path

    def filter(self, sessions: List[ConversationSession]) -> List[ConversationSession]:
        """Filter sessions for a specific project"""
        return [s for s in sessions if s.project == self.project_path]


class SessionIdFilter(IConversationFilter):
    """Filter by specific session ID"""

    def __init__(self, session_id: str):
        self.session_id = session_id

    def filter(self, sessions: List[ConversationSession]) -> List[ConversationSession]:
        """Filter for a specific session"""
        return [s for s in sessions if s.session_id == self.session_id]


class CompositeFilter(IConversationFilter):
    """Combine multiple filters - Composite Pattern"""

    def __init__(self, filters: List[IConversationFilter]):
        self.filters = filters

    def filter(self, sessions: List[ConversationSession]) -> List[ConversationSession]:
        """Apply all filters in sequence"""
        result = sessions
        for f in self.filters:
            result = f.filter(result)
        return result


# ============================================================================
# Formatter Strategy Pattern (Open/Closed Principle)
# ============================================================================

class IConversationFormatter(ABC):
    """Interface for formatting conversation output"""

    @abstractmethod
    def format_sessions(self, sessions: List[ConversationSession]) -> str:
        """Format sessions for output"""
        pass


class SummaryFormatter(IConversationFormatter):
    """Format sessions as a summary list"""

    def format_sessions(self, sessions: List[ConversationSession]) -> str:
        """Format sessions as a summary"""
        if not sessions:
            return "No conversations found."

        output = [f"\n{'='*80}"]
        output.append(f"Found {len(sessions)} conversation session(s)")
        output.append(f"{'='*80}\n")

        for i, session in enumerate(sessions, 1):
            output.append(f"{i}. Session: {session.session_id[:8]}...")
            output.append(f"   Started: {session.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            output.append(f"   Duration: {self._format_duration(session.duration)}")
            output.append(f"   Messages: {session.message_count}")
            output.append(f"   Project: {session.project}")

            # Show first message preview
            if session.messages:
                first_msg = session.messages[0].display[:100]
                output.append(f"   Preview: {first_msg}...")
            output.append("")

        return "\n".join(output)

    def _format_duration(self, duration: timedelta) -> str:
        """Format duration in a human-readable way"""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


class DetailedFormatter(IConversationFormatter):
    """Format sessions with full message details"""

    def format_sessions(self, sessions: List[ConversationSession]) -> str:
        """Format sessions with all messages"""
        if not sessions:
            return "No conversations found."

        output = []

        for session in sessions:
            output.append(f"\n{'='*80}")
            output.append(f"Session: {session.session_id}")
            output.append(f"Started: {session.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            output.append(f"Project: {session.project}")
            output.append(f"{'='*80}\n")

            for i, msg in enumerate(session.messages, 1):
                output.append(f"[{msg.datetime.strftime('%H:%M:%S')}] Message {i}:")
                output.append(f"{msg.display}")

                if msg.pasted_contents:
                    output.append(f"  (Has {len(msg.pasted_contents)} pasted content(s))")
                output.append("")

        return "\n".join(output)


class JSONFormatter(IConversationFormatter):
    """Format sessions as JSON - Open/Closed Principle"""

    def format_sessions(self, sessions: List[ConversationSession]) -> str:
        """Format sessions as JSON"""
        sessions_data = []

        for session in sessions:
            sessions_data.append({
                'session_id': session.session_id,
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat(),
                'duration_seconds': session.duration.total_seconds(),
                'message_count': session.message_count,
                'project': session.project,
                'messages': [
                    {
                        'display': msg.display,
                        'timestamp': msg.datetime.isoformat(),
                        'pasted_contents': msg.pasted_contents
                    }
                    for msg in session.messages
                ]
            })

        return json.dumps(sessions_data, indent=2)


# ============================================================================
# Service Layer (Business Logic)
# ============================================================================

class ConversationExplorerService:
    """Main service for exploring conversations - Single Responsibility"""

    def __init__(self, repository: IConversationRepository):
        self.repository = repository

    def search_conversations(
        self,
        filter_strategy: Optional[IConversationFilter] = None,
        formatter: Optional[IConversationFormatter] = None
    ) -> str:
        """Search and format conversations"""
        # Get all sessions
        sessions = self.repository.get_sessions()

        # Apply filter if provided
        if filter_strategy:
            sessions = filter_strategy.filter(sessions)

        # Format output
        formatter = formatter or SummaryFormatter()
        return formatter.format_sessions(sessions)

    def get_recent_session(self, minutes_ago: int = 60) -> Optional[ConversationSession]:
        """Get the most recent session within the specified time"""
        sessions = self.repository.get_sessions()
        time_filter = TimeRangeFilter(minutes_ago=minutes_ago)
        filtered = time_filter.filter(sessions)

        return filtered[0] if filtered else None


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """Main entry point for CLI"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Claude Code Conversation History Explorer",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--history-file',
        type=str,
        default=str(Path.home() / '.claude' / 'history.jsonl'),
        help='Path to history.jsonl file'
    )

    parser.add_argument(
        '--minutes-ago',
        type=int,
        help='Filter conversations from the last N minutes'
    )

    parser.add_argument(
        '--hours-ago',
        type=int,
        help='Filter conversations from the last N hours'
    )

    parser.add_argument(
        '--days-ago',
        type=int,
        help='Filter conversations from the last N days'
    )

    parser.add_argument(
        '--session-id',
        type=str,
        help='Show specific session by ID'
    )

    parser.add_argument(
        '--project',
        type=str,
        help='Filter by project path'
    )

    parser.add_argument(
        '--format',
        choices=['summary', 'detailed', 'json'],
        default='summary',
        help='Output format'
    )

    args = parser.parse_args()

    # Initialize repository
    history_path = Path(args.history_file)
    repository = JSONLConversationRepository(history_path)

    # Build filter chain
    filters = []

    if args.minutes_ago or args.hours_ago or args.days_ago:
        filters.append(TimeRangeFilter(
            minutes_ago=args.minutes_ago,
            hours_ago=args.hours_ago,
            days_ago=args.days_ago
        ))

    if args.project:
        filters.append(ProjectFilter(args.project))

    if args.session_id:
        filters.append(SessionIdFilter(args.session_id))

    filter_strategy = CompositeFilter(filters) if filters else None

    # Select formatter
    formatters = {
        'summary': SummaryFormatter(),
        'detailed': DetailedFormatter(),
        'json': JSONFormatter()
    }
    formatter = formatters[args.format]

    # Execute search
    service = ConversationExplorerService(repository)
    result = service.search_conversations(filter_strategy, formatter)

    print(result)


if __name__ == '__main__':
    main()
