from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkflowVisibilityTests(unittest.TestCase):
    def test_zip_artifact_upload_is_fail_closed_for_public_repositories(self) -> None:
        workflow = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
        self.assertIn("id: repository-visibility", workflow)
        self.assertIn('gh api "repos/$GITHUB_REPOSITORY" --jq .private', workflow)
        self.assertIn('echo "private=false" >> "$GITHUB_OUTPUT"', workflow)
        self.assertIn("if: steps.repository-visibility.outputs.private == 'true'", workflow)
        self.assertIn("Upload ZIP artifact (private repositories only)", workflow)


if __name__ == "__main__":
    unittest.main()
