# Empathic AI Research – End-to-End Test Runbook (Windows PowerShell)

This runbook provides copy‑pasteable commands to validate the system end‑to‑end on Windows using PowerShell. Run all commands from the repository root unless stated otherwise.

Caution:
- Do NOT run the destructive reset steps unless you intend to wipe data. They’re clearly marked as DANGEROUS.
- For managed Postgres (e.g., Supabase), prefer the non‑destructive row clear (TRUNCATE) when you need a clean slate without dropping tables.

## 0) Prereqs

```powershell
# Verify Python is available
python --version

# Optional: Ensure pip is recent
python -m pip install --upgrade pip
```

## 1) Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## 2) Configure environment

- Create a `.env` file at repo root (same folder as `run_app.py`). Add at minimum:

```
OPENAI_API_KEY=YOUR_KEY_HERE
# Optional: point to managed Postgres (e.g., Supabase); leave unset to use local SQLite file
# DATABASE_URL=postgresql+psycopg2://USER:PASS@HOST:PORT/DB?sslmode=require
```

- If you prefer ephemeral session vars (for this PowerShell session only):

```powershell
# Example (edit values)
$env:OPENAI_API_KEY = "sk-your-key"
# $env:DATABASE_URL = "postgresql+psycopg2://USER:PASS@HOST:5432/DB?sslmode=require"
```

## 3) Sanity‑check OpenAI access

```powershell
# Lists chat-capable models your key can access
python scripts/list_openai_models.py

# Quick ping of a known model; prints a tiny reply if usable
python scripts/sanity_check_model.py
```

## 4) Database selection and verification

By default the app uses SQLite at `data/database/conversations.db`. If `DATABASE_URL` is set, that takes precedence (e.g., managed Postgres like Supabase).

### 4.1) Verify current DB connectivity and stats

```powershell
# Lightweight verification (prints counts)
python scripts/setup_database.py --verify
```

### 4.2) Non‑destructive clean slate (clear rows, keep schema)

Pick ONE approach based on your backend.

- Postgres (e.g., Supabase) (TRUNCATE with identity reset):
```powershell
python - << 'PY'
import os
from src.database.db_manager import DatabaseManager
from sqlalchemy import text
# Uses DATABASE_URL if set; otherwise points to local SQLite file
mgr = DatabaseManager("data/database/conversations.db")
with mgr.engine.begin() as conn:
    if mgr.engine.url.get_backend_name().startswith("postgres"):
        conn.execute(text("TRUNCATE TABLE messages, crisis_flags, participants RESTART IDENTITY CASCADE"))
    else:
        raise SystemExit("Not a Postgres URL; see SQLite block below")
print("✓ Cleared rows (Postgres), schema intact")
PY
```

- SQLite (delete rows + reset sequences):
```powershell
python - << 'PY'
from src.database.db_manager import DatabaseManager
from sqlalchemy import text
mgr = DatabaseManager("data/database/conversations.db")
with mgr.engine.begin() as conn:
    conn.execute(text("DELETE FROM messages"))
    conn.execute(text("DELETE FROM crisis_flags"))
    conn.execute(text("DELETE FROM participants"))
    try:
        conn.execute(text("DELETE FROM sqlite_sequence WHERE name IN ('messages','crisis_flags','participants')"))
    except Exception:
        pass
print("✓ Cleared rows (SQLite), schema intact")
PY
```

### 4.3) DANGEROUS: Drop and recreate all tables

Only if you truly need a fresh schema. This will delete EVERYTHING in the database.

```powershell
# Destroys all tables (SQLite or DATABASE_URL) and recreates them
python scripts/setup_database.py --reset --yes
```

## 5) Quick functional checks (print-based tests)

```powershell
python test_functional.py
python test_neutral_fix.py
python test_integration.py
python tests\test_async_db.py
```

Expected highlights:
- Bot rotation is sequential: Cognitive → Emotional → Motivational → Neutral.
- No “control” label in current flows (historical rows may exist in DB but are displayed as Neutral in admin).

## 6) CLI agent testing (no DB writes)

Interactive session (in-memory DB, safe):
```powershell
python scripts/agent_cli.py
```

Single message mode (choose bot and message):
```powershell
python scripts/agent_cli.py --bot neutral --message "I feel overwhelmed with school."
```

Show full prompt and debug:
```powershell
python scripts/agent_cli.py --bot cognitive --message "Having trouble sleeping." --show-full-prompt --debug
```

## 7) Run the participant app (Streamlit)

```powershell
# From repo root
python run_app.py
```

Checklist in the browser:
- Consent → session starts.
- Watermark is visible only if assigned "visible"; disclaimer always shown.
- Send messages up to the configured limit; click “End Conversation” to proceed.

## 8) Run the admin dashboard (Streamlit)

```powershell
python run_admin.py
```

Verify in the dashboard:
- Overview → distribution shows four modalities, “Neutral” includes any historical “control”.
- Participants → table includes the "Watermark" column (visible/hidden).
- Data Export → export conversations and participant summary successfully.

## 9) Programmatic export (optional)

```powershell
python - << 'PY'
from src.database.db_manager import DatabaseManager
from src.database.csv_exporter import CSVExporter
mgr = DatabaseManager("data/database/conversations.db")
exp = CSVExporter(mgr)
paths = exp.export_all()
print(paths)
PY
```

Exports land in `data/exports/`.

## 10) Postgres end‑to‑end check (safe)

Read‑only verification of counts and rotation source, without creating test noise:
```powershell
python - << 'PY'
from src.database.db_manager import DatabaseManager
mgr = DatabaseManager("data/database/conversations.db")
stats = mgr.get_statistics()
print("Participants:", stats.get('total_participants'))
print("Completed:", stats.get('completed_conversations'))
print("Bot distribution:", stats.get('bot_distribution'))
PY
```

If you need to validate sequential assignment with a couple of new rows (be cautious in production):
```powershell
python - << 'PY'
import yaml
from src.database.db_manager import DatabaseManager
from src.chatbot.bot_manager import BotManager
cfg = yaml.safe_load(open('config/app_config.yaml','r',encoding='utf-8'))
mgr = DatabaseManager(cfg['database']['path'])
bm = BotManager(mgr, cfg)
assigned = []
for _ in range(4):
    sd = bm.create_new_session()
    mgr.create_participant(sd['participant_id'], sd['bot_type'], watermark_condition=sd.get('watermark_condition'))
    assigned.append((sd['participant_id'], sd['bot_type'], sd.get('watermark_condition')))
print("Assigned (pid, bot, wm):", assigned)
PY
```

## 11) Troubleshooting quick refs

```powershell
# If Streamlit port is busy, kill stray processes using 8501/8502
Get-Process | Where-Object { $_.ProcessName -like '*python*' } | Select-Object Id, ProcessName, MainWindowTitle
# Then stop by Id (replace 1234 with the actual Id)
Stop-Process -Id 1234 -Force

# Print current env values in this shell
Write-Output $env:OPENAI_API_KEY
Write-Output $env:DATABASE_URL

# Deactivate virtual environment
deactivate
```

## 12) Summary of the expected state

- Rotation: cognitive → emotional → motivational → neutral (deterministic by total participants).
- Watermark condition: randomized visible/hidden; persisted to participants and visible in admin.
- Admin dashboard: shows Watermark column; only four modalities; exports include `watermark_condition`.
- No schema drops unless you explicitly invoked the DANGEROUS reset.
