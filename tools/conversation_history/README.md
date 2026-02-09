# Conversation History Explorer

A scalable, SOLID-principle-based tool for exploring Claude Code conversation history.

## Architecture

This tool follows SOLID principles for maintainability and extensibility:

### Single Responsibility Principle (SRP)
- **ConversationMessage** & **ConversationSession**: Domain models (data only)
- **JSONLConversationRepository**: Data access (reading history file)
- **Filters**: Each filter handles one type of filtering
- **Formatters**: Each formatter handles one output format
- **ConversationExplorerService**: Business logic orchestration

### Open/Closed Principle (OCP)
- New filters can be added without modifying existing code
- New formatters can be added without changing the core logic
- Extensible through interfaces (ABC)

### Liskov Substitution Principle (LSP)
- All filters implement `IConversationFilter` and are interchangeable
- All formatters implement `IConversationFormatter` and are interchangeable

### Interface Segregation Principle (ISP)
- Small, focused interfaces: `IConversationRepository`, `IConversationFilter`, `IConversationFormatter`

### Dependency Inversion Principle (DIP)
- `ConversationExplorerService` depends on abstractions (interfaces), not concrete implementations
- Easy to swap implementations (e.g., different storage backends)

## Features

- ✅ Search conversations by time range
- ✅ Filter by project
- ✅ Filter by session ID
- ✅ Multiple output formats (summary, detailed, JSON)
- ✅ Composite filters (combine multiple filters)
- ✅ Human-readable timestamps
- ✅ Session duration tracking
- ✅ Easily extensible

## Usage

### Find conversations from the last 30 minutes
```bash
python conversation_explorer.py --minutes-ago 30
```

### Find conversations from the last 2 hours
```bash
python conversation_explorer.py --hours-ago 2
```

### Find conversations from today
```bash
python conversation_explorer.py --hours-ago 24
```

### Get detailed view of conversations
```bash
python conversation_explorer.py --hours-ago 1 --format detailed
```

### Export to JSON
```bash
python conversation_explorer.py --hours-ago 2 --format json > conversations.json
```

### Filter by project
```bash
python conversation_explorer.py --project "C:\git\technological_foods"
```

### View specific session
```bash
python conversation_explorer.py --session-id "a4deb874-7be0-4565-b5bb-dfa20650b69d" --format detailed
```

### Combine filters
```bash
python conversation_explorer.py --hours-ago 2 --project "C:\git\technological_foods" --format detailed
```

## Extending the Tool

### Add a New Filter

```python
class KeywordFilter(IConversationFilter):
    """Filter sessions containing a keyword"""

    def __init__(self, keyword: str):
        self.keyword = keyword.lower()

    def filter(self, sessions: List[ConversationSession]) -> List[ConversationSession]:
        return [
            s for s in sessions
            if any(self.keyword in msg.display.lower() for msg in s.messages)
        ]
```

### Add a New Formatter

```python
class MarkdownFormatter(IConversationFormatter):
    """Format sessions as Markdown"""

    def format_sessions(self, sessions: List[ConversationSession]) -> str:
        output = ["# Conversation History\n"]
        for session in sessions:
            output.append(f"## Session {session.session_id[:8]}")
            output.append(f"- Started: {session.start_time}")
            output.append(f"- Messages: {session.message_count}\n")
            for msg in session.messages:
                output.append(f"**User**: {msg.display}\n")
        return "\n".join(output)
```

### Add a New Repository (e.g., for database storage)

```python
class DatabaseConversationRepository(IConversationRepository):
    """Read conversations from a database"""

    def __init__(self, db_connection):
        self.db = db_connection

    def read_all_messages(self) -> List[ConversationMessage]:
        # Query database
        pass

    def get_sessions(self) -> List[ConversationSession]:
        # Query and group by session
        pass
```

## API Usage

You can also use this as a library:

```python
from pathlib import Path
from conversation_explorer import (
    JSONLConversationRepository,
    ConversationExplorerService,
    TimeRangeFilter,
    DetailedFormatter
)

# Initialize
history_path = Path.home() / '.claude' / 'history.jsonl'
repository = JSONLConversationRepository(history_path)
service = ConversationExplorerService(repository)

# Search with custom filters
time_filter = TimeRangeFilter(minutes_ago=30)
formatter = DetailedFormatter()
result = service.search_conversations(time_filter, formatter)
print(result)

# Or get the most recent session programmatically
recent_session = service.get_recent_session(minutes_ago=60)
if recent_session:
    print(f"Found session with {recent_session.message_count} messages")
    for msg in recent_session.messages:
        print(f"[{msg.time_ago}] {msg.display}")
```

## Requirements

- Python 3.7+
- No external dependencies (uses only standard library)

## File Structure

```
conversation_history/
├── conversation_explorer.py  # Main tool
├── README.md                 # This file
└── quick_search.py          # Helper script for common searches
```
