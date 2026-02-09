# Quick Start Guide

## What We Built

A **scalable conversation history explorer** for Claude Code that follows SOLID principles:

- ✅ Search conversations by time, project, or session
- ✅ Multiple output formats (summary, detailed, JSON)
- ✅ Extensible architecture
- ✅ No external dependencies

## Installation

No installation needed! Just run the Python scripts directly.

## Quick Usage Examples

### 1. Find conversations from the last hour
```bash
python conversation_explorer.py --hours-ago 1
```

### 2. Find conversations from 30 minutes ago (detailed view)
```bash
python conversation_explorer.py --minutes-ago 30 --format detailed
```

### 3. See all conversations from today
```bash
python conversation_explorer.py --hours-ago 24 --format summary
```

### 4. View a specific conversation by session ID
```bash
python conversation_explorer.py --session-id "a4deb874-7be0-4565-b5bb-dfa20650b69d" --format detailed
```

### 5. Export to JSON
```bash
python conversation_explorer.py --hours-ago 2 --format json > my_conversations.json
```

## Your Recent Conversations

Based on your history, you have **3 recent sessions**:

### Session 1: Current Session (Now)
- **ID**: `4f229f5a-c34a-41e9-909d-b2ed9f4a0934`
- **Started**: 2026-02-09 00:26:34
- **Topic**: Building this conversation explorer tool

### Session 2: Business Intelligence Discussion
- **ID**: `55ed202a-c68c-4510-a4e7-093ee3bed4d3`
- **Started**: 2026-02-08 22:25:40
- **Duration**: ~2 hours
- **Topics**:
  - DevOps and GitHub Actions deployment
  - Business intelligence dashboard
  - Dual sensor redundancy system
  - Hot culture crop recommendations
  - Hydroponics automation

### Session 3: Notification System Development
- **ID**: `a4deb874-7be0-4565-b5bb-dfa20650b69d`
- **Started**: 2026-02-08 20:22:19
- **Duration**: ~3.5 hours
- **Topics**:
  - Real-time notifications with ntfy
  - Sensor data alerts and monitoring
  - Preventive alert system
  - Configuration files for different lettuce types
  - Raspberry Pi deployment
  - Two-environment setup (dev & prod)

## Command Reference

```bash
# Time-based filters
--minutes-ago N      # Last N minutes
--hours-ago N        # Last N hours
--days-ago N         # Last N days

# Other filters
--session-id ID      # Specific session
--project PATH       # Specific project path

# Output formats
--format summary     # Brief overview (default)
--format detailed    # Full conversation
--format json        # JSON export
```

## Use as a Library

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

# Get recent session
session = service.get_recent_session(minutes_ago=30)
if session:
    for msg in session.messages:
        print(f"{msg.datetime}: {msg.display}")
```

## File Locations

- **History file**: `~/.claude/history.jsonl` (or `C:\Users\anton\.claude\history.jsonl` on Windows)
- **This tool**: `tools/conversation_history/`

## Tips

1. **Export for backup**: Use `--format json` to export conversations
2. **Combine filters**: You can use multiple filters together
3. **Pipe output**: Redirect output to files for later reference
4. **Check recent work**: Quickly review what you discussed in the last hour

## Next Steps

- Add keyword search filter
- Add Markdown export
- Create web UI
- Add conversation replay feature
- Integrate with Claude Code commands

## Architecture Highlights (SOLID Principles)

- **S**ingle Responsibility: Each class has one job
- **O**pen/Closed: Easy to add new filters/formatters
- **L**iskov Substitution: All filters/formatters are interchangeable
- **I**nterface Segregation: Small, focused interfaces
- **D**ependency Inversion: Service depends on abstractions

See `README.md` for detailed architecture documentation.
