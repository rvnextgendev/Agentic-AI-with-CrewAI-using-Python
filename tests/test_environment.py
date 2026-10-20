import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from config.environment import refresh_local_environment


class EnvironmentTests(unittest.TestCase):
    def test_local_changes_refresh_but_cloud_values_remain_protected(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ), patch("config.environment._managed", {}), patch("config.environment._protected", set()):
            path = Path(folder) / ".env"
            os.environ.pop("STUDIO_TEST_KEY", None)
            path.write_text("STUDIO_TEST_KEY=old-local\n")
            refresh_local_environment(path)
            path.write_text("STUDIO_TEST_KEY=new-local\n")
            refresh_local_environment(path)
            self.assertEqual(os.environ["STUDIO_TEST_KEY"], "new-local")
            refresh_local_environment(path, protected_keys={"STUDIO_TEST_KEY"})
            path.write_text("STUDIO_TEST_KEY=other-local\n")
            refresh_local_environment(path)
            self.assertEqual(os.environ["STUDIO_TEST_KEY"], "new-local")

    def test_explicit_environment_is_not_overwritten(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, {"STUDIO_TEST_KEY": "explicit"}), patch("config.environment._managed", {}), patch("config.environment._protected", set()):
            path = Path(folder) / ".env"
            path.write_text("STUDIO_TEST_KEY=local\n")
            refresh_local_environment(path)
            self.assertEqual(os.environ["STUDIO_TEST_KEY"], "explicit")
