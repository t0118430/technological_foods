#!/bin/bash
# Quick wrapper for conversation explorer
# Usage: ./find_conversation.sh [minutes|hours|session_id]

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ -z "$1" ]; then
    echo "Usage: ./find_conversation.sh [option]"
    echo ""
    echo "Examples:"
    echo "  ./find_conversation.sh 30m     - Last 30 minutes"
    echo "  ./find_conversation.sh 2h      - Last 2 hours"
    echo "  ./find_conversation.sh 1d      - Last 1 day"
    echo "  ./find_conversation.sh SESSION_ID - Specific session"
    echo ""
    exit 1
fi

INPUT="$1"

# Check if input ends with 'm' (minutes)
if [[ $INPUT =~ ^([0-9]+)m$ ]]; then
    MINUTES="${BASH_REMATCH[1]}"
    python "$SCRIPT_DIR/conversation_explorer.py" --minutes-ago "$MINUTES" --format detailed
# Check if input ends with 'h' (hours)
elif [[ $INPUT =~ ^([0-9]+)h$ ]]; then
    HOURS="${BASH_REMATCH[1]}"
    python "$SCRIPT_DIR/conversation_explorer.py" --hours-ago "$HOURS" --format detailed
# Check if input ends with 'd' (days)
elif [[ $INPUT =~ ^([0-9]+)d$ ]]; then
    DAYS="${BASH_REMATCH[1]}"
    python "$SCRIPT_DIR/conversation_explorer.py" --days-ago "$DAYS" --format detailed
# Otherwise treat as session ID
else
    python "$SCRIPT_DIR/conversation_explorer.py" --session-id "$INPUT" --format detailed
fi
