from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def test_update_workflow_contract(self) -> None:
        workflow = (ROOT / ".github/workflows/update-gcp-release.yml").read_text()
        for required in (
            "repository_dispatch:",
            "gcp_setup_released",
            "workflow_dispatch:",
            "permissions:\n  contents: read",
            "concurrency:",
            "cancel-in-progress: false",
            "releases/latest",
            "releases/tags/$requested_tag",
            "--requested-tag",
            "scripts/update_gcp_release.py",
            "secrets.NERO_UPDATE_TOKEN",
            "gh auth setup-git",
            "git ls-remote --exit-code --heads",
            "--force-with-lease",
            "automation/update-gcp-release",
        ):
            self.assertIn(required, workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("pull-requests: write", workflow)

    def test_ci_runs_the_updater_tests(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("python3 -m unittest discover -s tests -v", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)


if __name__ == "__main__":
    unittest.main()
