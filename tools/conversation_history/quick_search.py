#!/usr/bin/env python3
"""
Quick search helper for finding recent conversations
Usage: python quick_search.py
"""

import sys
from pathlib import Path

# Import from the main module
from conversation_explorer import (
    JSONLConversationRepository,
    ConversationExplorerService,
    TimeRangeFilter,
    DetailedFormatter,
    SummaryFormatter
)


def find_conversation_from_minutes_ago(minutes: int, detailed: bool = False):
    """Find and display conversations from N minutes ago"""
    history_path = Path.home() / '.claude' / 'history.jsonl'

    try:
        # Initialize
        repository = JSONLConversationRepository(history_path)
        service = ConversationExplorerService(repository)

        # Get recent session
        recent_session = service.get_recent_session(minutes_ago=minutes)

        if not recent_session:
            print(f"\n❌ No conversations found from the last {minutes} minutes.")
            print("\nTry increasing the time range or check if history file exists:")
            print(f"   {history_path}")
            return

        # Display session info
        print("\n" + "="*80)
        print(f"✅ Found conversation from {recent_session.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Session ID: {recent_session.session_id}")
        print(f"Duration: {recent_session.duration}")
        print(f"Messages: {recent_session.message_count}")
        print(f"Project: {recent_session.project}")
        print("="*80 + "\n")

        if detailed:
            # Show all messages
            print("MESSAGES:")
            print("-" * 80)
            for i, msg in enumerate(recent_session.messages, 1):
                time_str = msg.datetime.strftime('%H:%M:%S')
                print(f"\n[{time_str}] Message {i} ({msg.time_ago}):")
                print(f"{msg.display}")

                if msg.pasted_contents:
                    print(f"  📎 Has {len(msg.pasted_contents)} pasted content(s)")
        else:
            # Show summary with first 3 messages
            print("RECENT MESSAGES (first 3):")
            print("-" * 80)
            for i, msg in enumerate(recent_session.messages[:3], 1):
                time_str = msg.datetime.strftime('%H:%M:%S')
                preview = msg.display[:150] + "..." if len(msg.display) > 150 else msg.display
                print(f"\n[{time_str}] {preview}")

            if recent_session.message_count > 3:
                print(f"\n... and {recent_session.message_count - 3} more messages")

        print("\n" + "="*80)
        print("\n💡 To see full details, run:")
        print(f"   python conversation_explorer.py --session-id {recent_session.session_id} --format detailed")
        print("\n")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure Claude Code history file exists at:")
        print(f"   {history_path}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


def interactive_search():
    """Interactive search menu"""
    print("\n" + "="*80)
    print("🔍 Claude Code Conversation History - Quick Search")
    print("="*80)
    print("\nWhat do you want to search for?")
    print("\n1. Conversation from 30 minutes ago")
    print("2. Conversation from 1 hour ago")
    print("3. Conversation from 2 hours ago")
    print("4. Conversation from 6 hours ago")
    print("5. All conversations from today")
    print("6. Custom time range (minutes)")
    print("0. Exit")

    choice = input("\nEnter your choice (0-6): ").strip()

    if choice == "0":
        print("Goodbye!")
        return

    detailed = input("\nShow full details? (y/n, default=n): ").strip().lower() == 'y'

    minutes_map = {
        "1": 30,
        "2": 60,
        "3": 120,
        "4": 360,
        "5": 1440  # 24 hours
    }

    if choice in minutes_map:
        find_conversation_from_minutes_ago(minutes_map[choice], detailed)
    elif choice == "6":
        try:
            custom_minutes = int(input("Enter minutes: ").strip())
            find_conversation_from_minutes_ago(custom_minutes, detailed)
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
    else:
        print("❌ Invalid choice.")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # Command-line usage
        try:
            minutes = int(sys.argv[1])
            detailed = len(sys.argv) > 2 and sys.argv[2] in ['-d', '--detailed']
            find_conversation_from_minutes_ago(minutes, detailed)
        except ValueError:
            print("Usage: python quick_search.py [minutes] [-d|--detailed]")
            print("Example: python quick_search.py 30 -d")
    else:
        # Interactive mode
        interactive_search()


if __name__ == '__main__':
    main()
