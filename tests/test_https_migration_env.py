from __future__ import annotations

import unittest

import test_https_migration as fixtures
from gitlab_agent.https_migration import MigrationError


class EffectiveGitEnvironmentTests(unittest.TestCase):
    def test_git_overrides_in_selected_env_are_rejected(self):
        fixture = fixtures.MigrationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        original = fixture.config_file.read_bytes()
        for assignment in ("GIT_SSL_NO_VERIFY=true", "GIT_CONFIG_COUNT=1",
                           "GIT_SSL_CAINFO=/local/ca.pem"):
            with self.subTest(assignment=assignment):
                fixture.config_file.write_bytes(original + (assignment + "\n").encode())
                with self.assertRaises(MigrationError):
                    fixture.plan()


if __name__ == "__main__":
    unittest.main()
