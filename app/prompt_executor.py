"""
Prompt Executor for VS Code Copilot

This module automatically feeds implementation prompts to the user/Copilot
in a sequential manner, tracking completion and managing dependencies.
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class PromptExecutor:
    """Manages sequential execution of implementation prompts"""

    def __init__(self, prompts_file: str = "implementation_prompts.json"):
        self.prompts_file = Path(prompts_file)
        self.state_file = Path("execution_state.json")
        self.prompts: List[Dict] = []
        self.state: Dict = {
            "completed_ids": [],
            "current_id": None,
            "started_at": None,
            "last_updated": None,
            "execution_log": []
        }

        self._load_prompts()
        self._load_state()

    def _load_prompts(self):
        """Load prompts from JSON file"""
        if not self.prompts_file.exists():
            raise FileNotFoundError(f"Prompts file not found: {self.prompts_file}")

        with open(self.prompts_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.prompts = data['prompts']

    def _load_state(self):
        """Load execution state"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self.state = json.load(f)
        else:
            self._save_state()

    def _save_state(self):
        """Persist execution state"""
        self.state['last_updated'] = datetime.now().isoformat()
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2)

    def get_next_prompt(self) -> Optional[Dict]:
        """Get the next executable prompt based on dependencies"""
        completed = set(self.state['completed_ids'])

        for prompt in self.prompts:
            prompt_id = prompt['id']

            # Skip if already completed
            if prompt_id in completed:
                continue

            # Check if all dependencies are completed
            dependencies = set(prompt.get('dependencies', []))
            if dependencies.issubset(completed):
                return prompt

        return None

    def mark_completed(self, prompt_id: int, notes: str = ""):
        """Mark a prompt as completed"""
        if prompt_id not in self.state['completed_ids']:
            self.state['completed_ids'].append(prompt_id)
            self.state['execution_log'].append({
                "prompt_id": prompt_id,
                "completed_at": datetime.now().isoformat(),
                "notes": notes
            })
            self._save_state()

    def mark_current(self, prompt_id: int):
        """Mark a prompt as currently in progress"""
        self.state['current_id'] = prompt_id
        if self.state['started_at'] is None:
            self.state['started_at'] = datetime.now().isoformat()
        self._save_state()

    def skip_prompt(self, prompt_id: int, reason: str = ""):
        """Skip a prompt (won't be executed)"""
        self.state['execution_log'].append({
            "prompt_id": prompt_id,
            "skipped_at": datetime.now().isoformat(),
            "reason": reason
        })
        # Don't add to completed_ids, but mark as processed
        self._save_state()

    def get_progress(self) -> Dict:
        """Get execution progress statistics"""
        total = len(self.prompts)
        completed = len(self.state['completed_ids'])

        # Calculate remaining by priority
        remaining_by_priority = {}
        for prompt in self.prompts:
            if prompt['id'] not in self.state['completed_ids']:
                priority = prompt['priority']
                remaining_by_priority[priority] = remaining_by_priority.get(priority, 0) + 1

        # Get next executable prompts
        next_prompts = []
        completed_set = set(self.state['completed_ids'])
        for prompt in self.prompts:
            if prompt['id'] in completed_set:
                continue
            deps = set(prompt.get('dependencies', []))
            if deps.issubset(completed_set):
                next_prompts.append({
                    'id': prompt['id'],
                    'title': prompt['title'],
                    'priority': prompt['priority']
                })

        return {
            'total': total,
            'completed': completed,
            'remaining': total - completed,
            'progress_percentage': round((completed / total) * 100, 1),
            'remaining_by_priority': remaining_by_priority,
            'next_executable': next_prompts,
            'current_id': self.state['current_id']
        }

    def generate_chat_prompt(self, prompt_id: int) -> str:
        """Generate a formatted chat prompt for VS Code Copilot"""
        prompt = next((p for p in self.prompts if p['id'] == prompt_id), None)
        if not prompt:
            raise ValueError(f"Prompt ID {prompt_id} not found")

        # Format as a natural language instruction for Copilot
        chat_prompt = f"""## Task #{prompt['id']}: {prompt['title']}

**Category:** {prompt['category']}
**Priority:** {prompt['priority']}
**Estimated Time:** {prompt['estimated_time']}

{prompt['prompt']}

**Acceptance Criteria:**
"""
        for criteria in prompt['acceptance_criteria']:
            chat_prompt += f"\n- {criteria}"

        if prompt.get('files_to_create'):
            chat_prompt += "\n\n**Files to Create:**\n"
            for file in prompt['files_to_create']:
                chat_prompt += f"- {file}\n"

        if prompt.get('files_to_modify'):
            chat_prompt += "\n**Files to Modify:**\n"
            for file in prompt['files_to_modify']:
                chat_prompt += f"- {file}\n"

        chat_prompt += "\n\nPlease implement this task now."

        return chat_prompt

    def export_next_prompts_batch(self, output_file: str = "next_prompts.txt", count: int = 3):
        """Export the next N prompts ready for execution to a text file"""
        completed_set = set(self.state['completed_ids'])
        next_prompts = []

        for prompt in self.prompts:
            if len(next_prompts) >= count:
                break
            if prompt['id'] in completed_set:
                continue
            deps = set(prompt.get('dependencies', []))
            if deps.issubset(completed_set):
                next_prompts.append(prompt)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("NEXT IMPLEMENTATION PROMPTS FOR VS CODE COPILOT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Progress: {len(self.state['completed_ids'])}/{len(self.prompts)} completed\n\n")

            for i, prompt in enumerate(next_prompts, 1):
                f.write("=" * 80 + "\n")
                f.write(f"PROMPT {i} of {len(next_prompts)}\n")
                f.write("=" * 80 + "\n\n")
                f.write(self.generate_chat_prompt(prompt['id']))
                f.write("\n\n")

        return len(next_prompts)

    def interactive_mode(self):
        """Run interactive prompt execution"""
        print("\n" + "=" * 80)
        print("🤖 PROMPT EXECUTOR - Interactive Mode")
        print("=" * 80 + "\n")

        progress = self.get_progress()
        print(f"Progress: {progress['completed']}/{progress['total']} ({progress['progress_percentage']}%)")
        print(f"Remaining: {progress['remaining']} tasks\n")

        if not progress['next_executable']:
            print("✅ All tasks completed or blocked by dependencies!")
            return

        print(f"📋 Next executable tasks ({len(progress['next_executable'])}):\n")
        for p in progress['next_executable']:
            print(f"   #{p['id']} - {p['title']} ({p['priority']})")

        print("\n" + "-" * 80 + "\n")

        next_prompt = self.get_next_prompt()
        if not next_prompt:
            print("No executable prompts found.")
            return

        print(f"🚀 Ready to execute: #{next_prompt['id']} - {next_prompt['title']}\n")

        response = input("Execute this prompt? [y/n/s(kip)/q(uit)]: ").strip().lower()

        if response == 'y':
            self.mark_current(next_prompt['id'])
            print("\n" + "=" * 80)
            print("COPY THE PROMPT BELOW TO VS CODE COPILOT CHAT:")
            print("=" * 80 + "\n")
            print(self.generate_chat_prompt(next_prompt['id']))
            print("\n" + "=" * 80 + "\n")

            input("Press Enter after Copilot completes the task...")
            notes = input("Any notes for completion log? (optional): ").strip()
            self.mark_completed(next_prompt['id'], notes)
            print(f"✅ Task #{next_prompt['id']} marked as completed!\n")

            # Continue with next task
            self.interactive_mode()

        elif response == 's':
            reason = input("Reason for skipping: ").strip()
            self.skip_prompt(next_prompt['id'], reason)
            print(f"⏭️  Task #{next_prompt['id']} skipped.\n")
            self.interactive_mode()

        elif response == 'q':
            print("\n👋 Exiting. Progress saved to execution_state.json\n")
            return

        else:
            print("Cancelled.\n")


def main():
    """Main entry point"""
    import sys

    executor = PromptExecutor()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "progress":
            progress = executor.get_progress()
            print("\n📊 Execution Progress:\n")
            print(f"Total Tasks: {progress['total']}")
            print(f"Completed: {progress['completed']}")
            print(f"Remaining: {progress['remaining']}")
            print(f"Progress: {progress['progress_percentage']}%\n")

            if progress['remaining_by_priority']:
                print("Remaining by priority:")
                for priority, count in sorted(progress['remaining_by_priority'].items()):
                    print(f"  {priority}: {count}")

            print(f"\nNext executable: {len(progress['next_executable'])} tasks")

        elif command == "next":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            num_exported = executor.export_next_prompts_batch(count=count)
            print(f"\n✓ Exported {num_exported} prompts to next_prompts.txt")
            print("Copy prompts from next_prompts.txt and paste into VS Code Copilot Chat.\n")

        elif command == "complete":
            if len(sys.argv) < 3:
                print("Usage: python prompt_executor.py complete <prompt_id> [notes]")
                return

            prompt_id = int(sys.argv[2])
            notes = sys.argv[3] if len(sys.argv) > 3 else ""
            executor.mark_completed(prompt_id, notes)
            print(f"✅ Task #{prompt_id} marked as completed!")

        elif command == "reset":
            if input("Reset all progress? [y/n]: ").strip().lower() == 'y':
                executor.state = {
                    "completed_ids": [],
                    "current_id": None,
                    "started_at": None,
                    "last_updated": None,
                    "execution_log": []
                }
                executor._save_state()
                print("✓ Progress reset.")

        else:
            print(f"Unknown command: {command}")
            print("\nAvailable commands:")
            print("  progress        - Show execution progress")
            print("  next [count]    - Export next N prompts to file")
            print("  complete <id>   - Mark prompt as completed")
            print("  reset           - Reset all progress")

    else:
        # Interactive mode
        executor.interactive_mode()


if __name__ == "__main__":
    main()
