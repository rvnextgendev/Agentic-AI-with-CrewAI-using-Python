import os
import unittest
from unittest.mock import patch

from config.llm import create_llm
from runtime_check import check_python


class RuntimeTests(unittest.TestCase):
    def test_python_311_is_supported(self):
        check_python((3, 11, 9))

    def test_unsupported_python_points_to_cloud_setting(self):
        for version in [(3, 12), (3, 14)]:
            with self.subTest(version=version), self.assertRaisesRegex(RuntimeError, "redeploy.*3.11"):
                check_python(version)

    def test_cloud_environment_takes_precedence_over_local_dotenv(self):
        with patch.dict(os.environ, {
            "GROQ_API_KEY": "test-cloud-key", "LLM_PROVIDER": "groq",
            "LLM_MODEL": "qwen/qwen3.8-27b",
        }):
            model = create_llm()
            self.assertEqual(model.openai_api_key, "test-cloud-key")
            self.assertEqual(model.openai_api_base, "https://api.groq.com/openai/v1")

    def test_incompatible_gpt_oss_configuration_is_rejected_before_api_call(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "groq", "LLM_MODEL": "openai/gpt-oss-20b", "GROQ_API_KEY": "test"}):
            with self.assertRaisesRegex(ValueError, "Set LLM_MODEL=qwen"):
                create_llm()


if __name__ == "__main__":
    unittest.main()
