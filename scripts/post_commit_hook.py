#!/usr/bin/env python3
"""
Post-commit hook: updates the 'ბოლო commit' line in prompt.md automatically.
Install: cp scripts/post_commit_hook.py .git/hooks/post-commit && chmod +x .git/hooks/post-commit
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPT = ROOT / "prompt.md"

if not PROMPT.exists():
    sys.exit(0)

try:
    last = subprocess.check_output(
        ["git", "log", "-1", "--format=%h — %s"],
        cwd=ROOT, text=True
    ).strip()
except Exception:
    sys.exit(0)

content = PROMPT.read_text(encoding="utf-8")
updated = re.sub(
    r"\*\*ბოლო commit:\*\*.*",
    f"**ბოლო commit:** {last}",
    content,
)

if updated != content:
    PROMPT.write_text(updated, encoding="utf-8")
    subprocess.run(["git", "add", str(PROMPT)], cwd=ROOT)
    subprocess.run(
        ["git", "commit", "--amend", "--no-edit", "--no-verify"],
        cwd=ROOT,
    )
