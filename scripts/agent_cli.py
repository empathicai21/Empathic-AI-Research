# Agent CLI Tester
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.database.db_manager import DatabaseManager
from src.chatbot.bot_manager import BotManager

BOT_CHOICES = ["emotional", "cognitive", "motivational", "neutral"]
BOT_EMOJIS = {"emotional": "", "cognitive": "", "motivational": "", "neutral": ""}

def load_config(config_path="config/app_config.yaml"):
    import yaml
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def print_sep():
    print("\n" + "=" * 70 + "\n")

def choose_bot():
    print("\n Choose empathy modality:")
    print("   1. Cognitive  2. Emotional  3. Motivational  4. Neutral")
    while True:
        c = input("Choice (1-4): ").strip()
        if c == "1": return "cognitive"
        if c == "2": return "emotional"
        if c == "3": return "motivational"
        if c == "4": return "neutral"
        print("Invalid choice.")

def run_interactive(config, args):
    print("=" * 70)
    print(" EMPATHIC AI - TESTING MODE ")
    print("=" * 70)
    
    # Use in-memory database for testing (won't persist)
    db = DatabaseManager(db_url="sqlite:///:memory:")
    bot = BotManager(db, config)
    
    # Determine bot type: command line arg, user choice, or let BotManager assign sequentially
    if args.bot:
        # Explicitly specified via --bot flag
        bot_type = args.bot
        sess = bot.create_new_session(bot_type=bot_type)
    else:
        # Interactive choice
        bot_type = choose_bot()
        sess = bot.create_new_session(bot_type=bot_type)
    
    session_id = sess["session_id"]
    watermark_condition = sess.get("watermark_condition", "unknown")
    watermark_icon = "👁️" if watermark_condition == "visible" else "🔒" if watermark_condition == "hidden" else "❓"
    
    print(f"\n Bot type: {bot_type.upper()}")
    print(f" Watermark: {watermark_condition.upper()} {watermark_icon}")
    print(f" Session ID: {session_id}")
    print(f" Participant ID: {sess.get('participant_id', 'N/A')}")
    
    prompt = bot.prompts.get(bot_type, "")
    print_sep()
    print(" SYSTEM PROMPT:")
    print("-" * 70)
    if args.show_full_prompt:
        print(prompt or "<EMPTY>")
    else:
        print(prompt[:500] + ("..." if len(prompt) > 500 else ""))
    print("-" * 70)
    
    max_msgs = config.get("conversation", {}).get("max_messages", 10)
    print(f"\n {max_msgs} turns. Type quit/exit to end. Type debug to toggle debug.")
    print_sep()
    
    msg_num = 0
    debug_mode = args.debug
    
    while msg_num < max_msgs:
        msg_num += 1
        try:
            user_input = input(f" Message ({msg_num}/{max_msgs}): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n Interrupted.")
            break
        
        if not user_input:
            print("  Empty message.")
            msg_num -= 1
            continue
        
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\n Ending...")
            break
        
        if user_input.lower() == "debug":
            debug_mode = not debug_mode
            print(f" Debug: {'ON' if debug_mode else 'OFF'}")
            msg_num -= 1
            continue
        
        if debug_mode:
            print("\n DEBUG:")
            print("-" * 70)
            print(f"[SYSTEM]: {prompt[:200]}...")
            history = bot.sessions[session_id].get("history", [])
            for msg in history:
                print(f"[{msg['role'].upper()}]: {msg['content'][:150]}...")
            print(f"[USER]: {user_input}")
            print("-" * 70)
        
        emoji = BOT_EMOJIS.get(bot_type, "")
        print(f"\n{emoji} Thinking...")
        try:
            resp = bot.get_bot_response(session_id, user_input, msg_num)
            bot_resp = resp["bot_response"]
            if resp.get("crisis_detected"):
                print("  CRISIS DETECTED!")
            print(f"\n{emoji} {bot_type.upper()}: {bot_resp}")
            print_sep()
        except Exception as e:
            print(f"\n Error: {e}")
            import traceback
            traceback.print_exc()
            break
    
    print_sep()
    print(f" Complete! ({msg_num} messages)")
    print(" NOT saved to database")
    
    history = bot.sessions[session_id].get("history", [])
    print(f"\n SUMMARY: {bot_type.upper()} | {msg_num} turns | {len(history)} messages")
    print("\n Full History:")
    print_sep()
    for msg in history:
        icon = "" if msg["role"] == "user" else BOT_EMOJIS.get(bot_type, "")
        print(f"{icon} {msg['role'].upper()}: {msg['content']}")
        print()
    print_sep()
    print(" Thank you!")
    return 0

def run_single(config, args):
    db = DatabaseManager(db_url="sqlite:///:memory:")
    bot = BotManager(db, config)
    
    # Use explicit bot type if provided, otherwise let BotManager assign sequentially
    bot_type_arg = args.bot if args.bot else None
    sess = bot.create_new_session(bot_type=bot_type_arg)
    
    bot_type = bot.sessions[sess["session_id"]]["bot_type"]
    prompt = bot.prompts.get(bot_type, "")
    
    print("== Setup ==")
    print(f"Bot: {bot_type} | Model: {bot.model}")
    print("-" * 40)
    print(prompt[:400] + ("..." if len(prompt) > 400 else ""))
    print("-" * 40)
    
    if args.debug:
        print("\n== Debug: Messages ==")
        print(f"[SYSTEM]: {prompt[:200]}...")
        print(f"[USER]: {args.message}")
    
    print("\n== Sending ==")
    print(args.message)
    resp = bot.get_bot_response(sess["session_id"], args.message, 1)
    
    print("\n== Reply ==")
    print(resp["bot_response"])
    if resp.get("crisis_detected"):
        print("\n[!] Crisis detected")
    return 0

def test_sequence(config, num_participants):
    """Test sequential assignment with watermark conditions."""
    print("🔍 TESTING SEQUENTIAL ASSIGNMENT WITH WATERMARKS")
    print("=" * 60)
    
    # Use in-memory database for testing (clean slate)
    # Temporarily override DATABASE_URL to force in-memory database
    import os
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ.pop("DATABASE_URL", None)  # Remove to force using db_path
    
    try:
        db = DatabaseManager(db_path=":memory:")
        bot = BotManager(db, config)
    finally:
        # Restore original DATABASE_URL
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
    
    print(f"Bot types: {bot.bot_types}")
    print(f"Expected sequence: {' → '.join(bot.bot_types)}")
    print(f"Testing with {num_participants} participants...\n")
    
    visible_count = 0
    hidden_count = 0
    
    for i in range(num_participants):
        # Create session without specifying bot_type to use sequential assignment
        sess = bot.create_new_session()
        
        participant_id = sess['participant_id']
        bot_type = sess['bot_type']
        watermark = sess['watermark_condition']
        
        # Create participant in database so sequential assignment count increases
        db.create_participant(participant_id, bot_type, watermark_condition=watermark)
        
        # Track watermark distribution
        if watermark == 'visible':
            visible_count += 1
        else:
            hidden_count += 1
        
        # Expected bot type based on sequential assignment
        expected_bot = bot.bot_types[i % 4]
        
        # Visual indicators
        sequence_check = "✓" if bot_type == expected_bot else "✗"
        watermark_icon = "👁️" if watermark == "visible" else "🔒"
        
        print(f"P{i+1:2d}: {participant_id} | {bot_type:12s} | {watermark:7s} {watermark_icon} | {sequence_check}")
        
        # Verify sequential assignment
        if bot_type != expected_bot:
            print(f"    ⚠️  Expected {expected_bot}, got {bot_type}")
    
    print(f"\nResults:")
    print(f"  👁️  Visible watermarks: {visible_count}")
    print(f"  🔒 Hidden watermarks:  {hidden_count}")
    print(f"  📊 Visible ratio: {visible_count/num_participants:.1%}")
    
    # Check if we have both types
    has_both = visible_count > 0 and hidden_count > 0
    print(f"  ✅ Both watermark types present: {has_both}")
    
    return 0

def main():
    parser = argparse.ArgumentParser(description="Test chatbot agent")
    parser.add_argument("--message", "-m", help="Single message mode")
    parser.add_argument("--bot", "-b", choices=BOT_CHOICES, help="Bot type")
    parser.add_argument("--model", help="Override model")
    parser.add_argument("--show-full-prompt", action="store_true", help="Show full prompt")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--test-sequence", "-s", type=int, metavar="N", help="Test sequential assignment with N participants")
    args = parser.parse_args()
    
    config = load_config()
    if args.model:
        config.setdefault("api", {})["model"] = args.model
    
    if args.test_sequence:
        return test_sequence(config, args.test_sequence)
    elif args.message:
        return run_single(config, args)
    else:
        return run_interactive(config, args)

if __name__ == "__main__":
    raise SystemExit(main())
