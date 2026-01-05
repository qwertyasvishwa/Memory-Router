"""
Auto-Runner for VS Code Copilot Integration

This script automatically feeds implementation prompts to your VS Code Copilot chat.
Run this script and copy each prompt as it's displayed.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.prompt_executor import PromptExecutor


def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    """Print application banner"""
    print("\n" + "═" * 80)
    print("   🤖 AI TOOLS CREATION APPLICATION - AUTO PROMPT RUNNER")
    print("═" * 80 + "\n")


def print_prompt_box(prompt_text: str, prompt_id: int, title: str):
    """Print prompt in a visually distinct box"""
    print("\n" + "╔" + "═" * 78 + "╗")
    print(f"║  PROMPT #{prompt_id}: {title[:60]}")
    print("╠" + "═" * 78 + "╣")
    print("║")

    # Split prompt into lines and format
    lines = prompt_text.split('\n')
    for line in lines:
        # Wrap long lines
        while len(line) > 76:
            print(f"║  {line[:76]}")
            line = line[76:]
        print(f"║  {line}")

    print("║")
    print("╚" + "═" * 78 + "╝\n")


def run_auto_mode():
    """Run in automatic prompt display mode"""
    executor = PromptExecutor()

    clear_screen()
    print_banner()

    progress = executor.get_progress()
    print(f"📊 Progress: {progress['completed']}/{progress['total']} tasks ({progress['progress_percentage']}%)\n")

    if progress['remaining'] == 0:
        print("✅ All tasks completed! The AI Tools Creation Application is ready.\n")
        return

    print(f"📋 Next executable tasks: {len(progress['next_executable'])}\n")
    for p in progress['next_executable'][:5]:
        status = "▶ CURRENT" if p['id'] == progress.get('current_id') else "  "
        print(f"   {status} #{p['id']}: {p['title']} [{p['priority']}]")

    print("\n" + "─" * 80 + "\n")

    # Get next prompt
    next_prompt_dict = executor.get_next_prompt()
    if not next_prompt_dict:
        print("⚠️  No more executable prompts. Check dependencies or mark tasks as complete.\n")
        return

    prompt_id = next_prompt_dict['id']
    title = next_prompt_dict['title']

    print(f"🎯 Next Task: #{prompt_id} - {title}")
    print(f"⏱️  Estimated Time: {next_prompt_dict['estimated_time']}")
    print(f"🏷️  Category: {next_prompt_dict['category']}")
    print(f"⚡ Priority: {next_prompt_dict['priority'].upper()}\n")

    # Generate the chat prompt
    chat_prompt = executor.generate_chat_prompt(prompt_id)

    # Display in box
    print_prompt_box(chat_prompt, prompt_id, title)

    print("┌─ INSTRUCTIONS " + "─" * 62 + "┐")
    print("│")
    print("│  1. Copy the entire prompt above (from the box)")
    print("│  2. Open VS Code Copilot Chat (Ctrl+Shift+I or Cmd+Shift+I)")
    print("│  3. Paste the prompt into Copilot Chat")
    print("│  4. Let Copilot implement the changes")
    print("│  5. Review and verify the implementation")
    print("│  6. Return here to continue")
    print("│")
    print("└" + "─" * 78 + "┘\n")

    # Mark as current
    executor.mark_current(prompt_id)

    # Wait for user action
    print("\nWhat would you like to do?\n")
    print("  [c] Mark as COMPLETED and continue to next prompt")
    print("  [s] SKIP this prompt (will not block dependent tasks)")
    print("  [r] RESHOW this prompt")
    print("  [p] Show PROGRESS summary")
    print("  [n] Export NEXT 3 prompts to file")
    print("  [q] QUIT and save progress")
    print()

    while True:
        choice = input("Choose an option: ").strip().lower()

        if choice == 'c':
            notes = input("\n📝 Any notes for this task? (optional, press Enter to skip): ").strip()
            executor.mark_completed(prompt_id, notes)
            print(f"\n✅ Task #{prompt_id} marked as COMPLETED!\n")

            # Ask if user wants to continue
            cont = input("Continue to next prompt? [y/n]: ").strip().lower()
            if cont == 'y':
                run_auto_mode()  # Recursive call for next prompt
            else:
                print("\n💾 Progress saved. Run this script again to continue.\n")
            break

        elif choice == 's':
            reason = input("\n❓ Why are you skipping this task? ").strip()
            executor.skip_prompt(prompt_id, reason)
            print(f"\n⏭️  Task #{prompt_id} skipped.\n")

            cont = input("Continue to next prompt? [y/n]: ").strip().lower()
            if cont == 'y':
                run_auto_mode()
            break

        elif choice == 'r':
            run_auto_mode()  # Reshow current prompt
            break

        elif choice == 'p':
            progress = executor.get_progress()
            print("\n" + "─" * 80)
            print("📊 PROGRESS SUMMARY")
            print("─" * 80)
            print(f"\nTotal Tasks: {progress['total']}")
            print(f"Completed: {progress['completed']} ✓")
            print(f"Remaining: {progress['remaining']}")
            print(f"Progress: {progress['progress_percentage']}%")

            if progress.get('remaining_by_priority'):
                print("\nRemaining by Priority:")
                for priority, count in sorted(progress['remaining_by_priority'].items()):
                    print(f"  • {priority.upper()}: {count} tasks")

            print("\n" + "─" * 80 + "\n")
            input("Press Enter to continue...")
            run_auto_mode()
            break

        elif choice == 'n':
            count = executor.export_next_prompts_batch("next_prompts.txt", count=3)
            print(f"\n✓ Exported {count} prompts to 'next_prompts.txt'")
            print("You can open this file and copy prompts from there.\n")
            input("Press Enter to continue...")
            run_auto_mode()
            break

        elif choice == 'q':
            print("\n👋 Goodbye! Your progress has been saved to 'execution_state.json'")
            print("Run this script again anytime to resume.\n")
            break

        else:
            print(f"❌ Invalid option '{choice}'. Please choose c, s, r, p, n, or q.")


def show_help():
    """Display help information"""
    print("\n" + "═" * 80)
    print("   AUTO PROMPT RUNNER - HELP")
    print("═" * 80 + "\n")

    print("This script helps you implement the AI Tools Creation Application by")
    print("automatically generating and feeding prompts to VS Code Copilot.\n")

    print("USAGE:")
    print("  python run_prompts.py           # Interactive mode (recommended)")
    print("  python run_prompts.py progress  # Show progress summary")
    print("  python run_prompts.py next [N]  # Export next N prompts to file")
    print("  python run_prompts.py help      # Show this help\n")

    print("WORKFLOW:")
    print("  1. Run this script in interactive mode")
    print("  2. Copy the displayed prompt")
    print("  3. Paste into VS Code Copilot Chat")
    print("  4. Let Copilot implement the task")
    print("  5. Mark as complete and move to next prompt")
    print("  6. Repeat until all 14 prompts are executed\n")

    print("FILES:")
    print("  • implementation_prompts.json - All generated prompts")
    print("  • docs/auto-implementation/IMPLEMENTATION_PLAN.md - Full execution plan (generated)")
    print("  • execution_state.json        - Your progress (auto-saved)")
    print("  • next_prompts.txt            - Exported prompts for batch copying\n")

    print("TIP: Keep this terminal open alongside VS Code for easy workflow!\n")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == 'help':
            show_help()
        elif command == 'progress':
            executor = PromptExecutor()
            progress = executor.get_progress()
            print("\n📊 Execution Progress:\n")
            print(f"  Total Tasks: {progress['total']}")
            print(f"  Completed: {progress['completed']} ✓")
            print(f"  Remaining: {progress['remaining']}")
            print(f"  Progress: {progress['progress_percentage']}%\n")

            if progress.get('remaining_by_priority'):
                print("  Remaining by priority:")
                for priority, count in sorted(progress['remaining_by_priority'].items()):
                    print(f"    • {priority}: {count}")
                print()
        elif command == 'next':
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            executor = PromptExecutor()
            num = executor.export_next_prompts_batch(count=count)
            print(f"\n✓ Exported {num} prompts to 'next_prompts.txt'\n")
        else:
            print(f"❌ Unknown command: {command}")
            print("Run 'python run_prompts.py help' for usage information.\n")
    else:
        # Interactive mode
        try:
            run_auto_mode()
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user. Progress saved.\n")
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
