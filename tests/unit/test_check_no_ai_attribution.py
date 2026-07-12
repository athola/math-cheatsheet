"""Regression tests for scripts/check_no_ai_attribution.sh.

Full-review 2026-07-12 blocker B3: the hook is registered at the
pre-commit ``commit-msg`` stage, where the in-progress commit message
file is passed as ``$1``. The script must grep that file — not
``git log -1 HEAD``, which at commit-msg time is the *previous* commit.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_no_ai_attribution.sh"


def _run(msg_file: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), str(msg_file)],
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestCommitMsgHookReadsMessageFile:
    def test_blocks_ai_attribution_in_message_file(self, tmp_path: Path) -> None:
        msg = tmp_path / "COMMIT_EDITMSG"
        msg.write_text(
            "fix: something\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n",
            encoding="utf-8",
        )
        proc = _run(msg)
        assert proc.returncode == 1, (
            "hook must reject the in-progress message passed as $1; "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )

    def test_allows_clean_message_file(self, tmp_path: Path) -> None:
        msg = tmp_path / "COMMIT_EDITMSG"
        msg.write_text("fix: honest human-authored change\n", encoding="utf-8")
        proc = _run(msg)
        assert proc.returncode == 0, (
            f"clean message must pass; stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
