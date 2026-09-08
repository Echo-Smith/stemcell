"""Verify a generated plan's incorrect claim in an isolated temporary repo.

No user's notes or repositories are changed. This is a deterministic check of
one operation, not a general verifier for generated implementation plans.
"""

import json
import subprocess
import tempfile
from pathlib import Path


def verify():
    with tempfile.TemporaryDirectory(prefix="stemcell-restore-proof-") as folder:
        root = Path(folder)

        def git(*args):
            return subprocess.check_output(
                [
                    "git",
                    "-c",
                    "user.name=Stemcell review",
                    "-c",
                    "user.email=review@example.invalid",
                    *args,
                ],
                cwd=root,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()

        git("init", "--quiet")
        note = root / "note.md"
        note.write_text("version one\n")
        git("add", "note.md")
        git("commit", "--quiet", "-m", "snapshot one")
        old = git("rev-parse", "HEAD")
        note.write_text("version two\n")
        git("add", "note.md")
        git("commit", "--quiet", "-m", "snapshot two")
        before = note.read_text()
        git("checkout", "--quiet", "-b", "restore-demo", old)
        after = note.read_text()
        return {"before": before, "after": after, "working_file_changed": before != after}


if __name__ == "__main__":
    result = verify()
    assert result["working_file_changed"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
