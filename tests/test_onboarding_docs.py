"""Exercise the documented onboarding gates, without providers or real secrets."""
from pathlib import Path
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
GUIDES = [ROOT / "docs" / name for name in ("GETTING_STARTED.md", "GETTING_STARTED_CN.md")]
PAGES = [ROOT / name for name in (
    "README.md", "README_CN.md", "docs/README.md", "docs/README_CN.md",
    "docs/SETUP_TUTORIAL.md", "docs/OPENAI_TUNNEL_TEAM_SETUP_CN.md",
    "docs/GETTING_STARTED.md", "docs/GETTING_STARTED_CN.md",
)]
BASH = shutil.which("bash")
POSIX_BASH = os.name == "posix" and BASH is not None


def blocks(path, language="bash"):
    return re.findall(r"^```" + language + r"\n(.*?)^```", path.read_text(encoding="utf-8"), re.M | re.S)


def example(name):
    text = GUIDES[0].read_text(encoding="utf-8")
    found = re.search(r"<!-- example: " + re.escape(name) + r" -->\s*```bash\n(.*?)^```", text, re.M | re.S)
    if not found:
        raise AssertionError("Missing documented example: " + name)
    return found[1]


def execute(name, home, source, extra=None):
    # Deliberately do not inherit the real HOME, GitLab or provider environment.
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home),
           "RF_SOURCE": str(source), "RF_PROFILE": "lab", "RF_TUNNEL_ID": "tunnel_synthetic_lab",
           "RF_PROJECT": "group/approved", "RF_REF": "develop", "RF_FILE": "docs/start.md"}
    env.update(extra or {})
    return subprocess.run([BASH, "-c", example(name)], env=env,
                          capture_output=True, text=True, timeout=15, check=False)


class OnboardingDocsTests(unittest.TestCase):
    def test_bilingual_examples_and_ordered_gates(self):
        self.assertEqual(blocks(GUIDES[0]), blocks(GUIDES[1]))
        self.assertGreaterEqual(len(blocks(GUIDES[0])), 12)
        for guide in GUIDES:
            text = guide.read_text(encoding="utf-8")
            anchors = ["prerequisites", "install-tools", "gitlab-access", "openai-tunnel",
                       "keychain", "profile-and-start", "chatgpt", "first-prompt", "daily-use"]
            positions = [text.index(f'<a id="{anchor}"></a>') for anchor in anchors]
            self.assertEqual(positions, sorted(positions))
            for token in ("GITLAB_ALLOWED_PROJECTS", "CONTROL_PLANE_API_KEY", "resolved_commit_sha",
                          "ready_for_chatgpt_check", "gitlab_whoami", "check_project_access",
                          "get_file", "localhost Assistant", "Terminal A", "Terminal B"):
                self.assertIn(token, text)
        self.assertEqual(blocks(ROOT / "docs/SETUP_TUTORIAL.md"),
                         blocks(ROOT / "docs/OPENAI_TUNNEL_TEAM_SETUP_CN.md"))
        for page in PAGES[:6]:
            self.assertRegex(page.read_text(encoding="utf-8"), r"GETTING_STARTED(?:_CN)?\.md")

    def test_relative_links_resolve_in_real_checkout(self):
        for page in PAGES:
            for raw in re.findall(r"\]\(([^)\s]+)\)", page.read_text(encoding="utf-8")):
                if "://" in raw or raw.startswith(("#", "mailto:")):
                    continue
                relative = unquote(raw.split("#", 1)[0])
                target = (page.parent / relative).resolve()
                with self.subTest(page=str(page.relative_to(ROOT)), target=relative):
                    self.assertTrue(target.is_relative_to(ROOT))
                    self.assertTrue(target.exists(), "Broken relative link")

    @unittest.skipUnless(POSIX_BASH, "Documented shell path is macOS/Linux Bash")
    def test_all_documented_bash_blocks_parse(self):
        for page in PAGES:
            for index, code in enumerate(blocks(page)):
                with self.subTest(page=page.name, block=index):
                    result = subprocess.run([BASH, "-n"], input=code, text=True,
                                            capture_output=True, timeout=5, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(POSIX_BASH, "Documented shell path is macOS/Linux Bash")
    def test_private_config_creation_and_existing_contents_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source = home / "source with spaces"
            source.mkdir()
            template = b"GITLAB_TOKEN=REPLACE_ME\n"
            (source / ".env.example").write_bytes(template)
            cfg = home / ".config/gitlab-agent/.env"
            first = execute("private-config", home, source)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(cfg.read_bytes(), template)
            self.assertEqual(stat.S_IMODE(cfg.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(cfg.parent.stat().st_mode), 0o700)
            preserved = b"existing operator configuration\n"
            cfg.write_bytes(preserved)
            second = execute("private-config", home, source)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(cfg.read_bytes(), preserved)
            self.assertNotIn(preserved.decode().strip(), second.stdout + second.stderr)

    @unittest.skipUnless(POSIX_BASH, "Documented shell path is macOS/Linux Bash")
    def test_private_config_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cfg = home / ".config/gitlab-agent/.env"
            cfg.parent.mkdir(parents=True)
            target = home / "untouched"
            target.write_text("keep", encoding="utf-8")
            cfg.symlink_to(target)
            result = execute("private-config", home, home)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep")
            self.assertTrue(cfg.is_symlink())

    @unittest.skipUnless(POSIX_BASH, "Documented shell path is macOS/Linux Bash")
    def test_profile_init_refuses_placeholder_and_existing_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            bin_dir = home / "bin"
            bin_dir.mkdir()
            calls = home / "calls"
            executable = bin_dir / "tunnel-client"
            executable.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CALLS"\n', encoding="utf-8")
            executable.chmod(0o700)
            extra = {"PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", ""), "CALLS": str(calls)}
            result = execute("profile-init", home, home, {**extra, "RF_TUNNEL_ID": "tunnel_REPLACE_ME"})
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(calls.exists())
            profile = home / ".config/tunnel-client/lab.yaml"
            profile.parent.mkdir(parents=True)
            profile.write_text("preserve", encoding="utf-8")
            result = execute("profile-init", home, home, extra)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(profile.read_text(encoding="utf-8"), "preserve")
            self.assertFalse(calls.exists())
            profile.unlink()  # Only this test's synthetic file.
            result = execute("profile-init", home, home / "source with spaces", extra)
            self.assertEqual(result.returncode, 0, result.stderr)
            argv = calls.read_text(encoding="utf-8").splitlines()
            self.assertNotIn("--force", argv)
            self.assertIn("env:CONTROL_PLANE_API_KEY", argv)
            self.assertIn('bash "' + str(home / "source with spaces/run_mcp.sh") + '"', argv)
            self.assertIn("127.0.0.1:8080", argv)

    @unittest.skipUnless(POSIX_BASH, "Documented shell path is macOS/Linux Bash")
    def test_project_check_stops_for_placeholder_and_clears_stale_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            bin_dir = home / "bin"
            bin_dir.mkdir()
            calls = home / "calls"
            executable = bin_dir / "actual-coder-check-project"
            executable.write_text('#!/bin/sh\n'
                'test -z "${GITLAB_TOKEN+x}${GITLAB_GIT_TOKEN+x}${GITLAB_BASE_URL+x}${GITLAB_ALLOWED_PROJECTS+x}" || exit 9\n'
                'test "$GITLAB_AGENT_ENV_FILE" = "$HOME/.config/gitlab-agent/.env" || exit 8\n'
                'printf "%s\\n" "$@" > "$CALLS"\n', encoding="utf-8")
            executable.chmod(0o700)
            extra = {"PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", ""), "CALLS": str(calls),
                     "GITLAB_TOKEN": "synthetic", "GITLAB_GIT_TOKEN": "synthetic",
                     "GITLAB_BASE_URL": "stale", "GITLAB_ALLOWED_PROJECTS": "stale"}
            result = execute("project-check", home, home, {**extra, "RF_PROJECT": "team/project-a"})
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(calls.exists())
            result = execute("project-check", home, home, extra)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(calls.read_text(encoding="utf-8").splitlines(),
                             ["group/approved", "--ref", "develop", "--require-file", "docs/start.md"])

    @unittest.skipUnless(POSIX_BASH, "Documented shell path is macOS/Linux Bash")
    def test_clone_example_does_not_overwrite_existing_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source = home / "source"
            source.mkdir()
            marker = source / "preserved"
            marker.write_text("keep", encoding="utf-8")
            result = execute("clone", home, source, {"PATH": "/nonexistent"})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Source already exists", result.stdout)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
