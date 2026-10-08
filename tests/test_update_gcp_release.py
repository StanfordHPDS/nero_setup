from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "update_gcp_release.py"
STABLE = json.loads((ROOT / "tests" / "fixtures" / "stable-release.json").read_text())


class UpdaterTests(unittest.TestCase):
    def run_updater(
        self, readme_text: str, payload: dict, *arguments: str
    ) -> tuple[subprocess.CompletedProcess[str], str, str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / "README.md"
            release = root / "release.json"
            output = root / "output.txt"
            readme.write_text(readme_text, encoding="utf-8")
            release.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--release-json",
                    str(release),
                    "--readme",
                    str(readme),
                    "--output",
                    str(output),
                    *arguments,
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            return result, readme.read_text(encoding="utf-8"), (
                output.read_text(encoding="utf-8") if output.exists() else ""
            )

    def test_replaces_every_url_and_preserves_commands(self) -> None:
        original = """\
curl -fsSL https://github.com/StanfordHPDS/gcp_setup_script/releases/download/v1.0.0/setup.sh | bash
curl -fsSL https://github.com/StanfordHPDS/gcp_setup_script/releases/download/v1.1.0/update.sh | bash
curl -fsSL https://github.com/StanfordHPDS/gcp_setup_script/releases/download/v1.0.0/update.sh | bash -s -- --example
"""
        result, updated, output = self.run_updater(
            original, STABLE, "--requested-tag", "v1.2.1"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(updated.count("/v1.2.1/"), 3)
        self.assertNotIn("/v1.0.0/", updated)
        self.assertNotIn("/v1.1.0/", updated)
        self.assertIn("update.sh | bash -s -- --example", updated)
        self.assertEqual(output, "tag=v1.2.1\nchanged=true\n")

    def test_no_op_does_not_rewrite_the_readme(self) -> None:
        original = "\n".join(
            [
                "https://github.com/StanfordHPDS/gcp_setup_script/releases/download/v1.2.1/setup.sh",
                "https://github.com/StanfordHPDS/gcp_setup_script/releases/download/v1.2.1/update.sh",
                "",
            ]
        )
        result, updated, output = self.run_updater(original, STABLE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(updated, original)
        self.assertEqual(output, "tag=v1.2.1\nchanged=false\n")

    def test_missing_asset_fails_without_editing(self) -> None:
        payload = copy.deepcopy(STABLE)
        payload["assets"] = payload["assets"][:1]
        original = self.example_readme()
        result, updated, output = self.run_updater(original, payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing assets: update.sh", result.stderr)
        self.assertEqual(updated, original)
        self.assertEqual(output, "")

    def test_unstable_or_unpublished_release_fails(self) -> None:
        for field, value, message in (
            ("draft", True, "is a draft"),
            ("prerelease", True, "is a prerelease"),
            ("published_at", None, "is not published"),
        ):
            with self.subTest(field=field):
                payload = copy.deepcopy(STABLE)
                payload[field] = value
                original = self.example_readme()
                result, updated, _ = self.run_updater(original, payload)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertEqual(updated, original)

    def test_requested_tag_must_match_release(self) -> None:
        original = self.example_readme()
        result, updated, _ = self.run_updater(
            original, STABLE, "--requested-tag", "v1.2.2"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not requested tag v1.2.2", result.stderr)
        self.assertEqual(updated, original)

    def test_readme_requires_both_wrapper_assets(self) -> None:
        original = (
            "https://github.com/StanfordHPDS/gcp_setup_script/releases/download/"
            "v1.2.0/setup.sh\n"
        )
        result, updated, _ = self.run_updater(original, STABLE)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("README is missing release URLs for: update.sh", result.stderr)
        self.assertEqual(updated, original)

    @staticmethod
    def example_readme() -> str:
        return "\n".join(
            [
                "https://github.com/StanfordHPDS/gcp_setup_script/releases/download/v1.2.0/setup.sh",
                "https://github.com/StanfordHPDS/gcp_setup_script/releases/download/v1.2.0/update.sh",
                "",
            ]
        )


if __name__ == "__main__":
    unittest.main()
