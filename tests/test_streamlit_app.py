import os
import unittest
from unittest.mock import patch
from unittest.mock import Mock
from openai import PermissionDeniedError

from streamlit.testing.v1 import AppTest

from pipeline import STAGES, PipelineError


class StreamlitAppTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"APP_PASSWORD": ""})
        self.env.start()
        self.configuration = patch("pipeline.validate_configuration")
        self.configuration.start()

    def tearDown(self):
        self.configuration.stop()
        self.env.stop()

    def app(self):
        return AppTest.from_file("streamlit_app.py", default_timeout=30).run()

    def test_invalid_topic_does_not_call_provider(self):
        with patch("pipeline.run_pipeline") as run:
            app = self.app()
            app.button[0].click().run()
        run.assert_not_called()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("3 and 200", app.error[0].value)

    def test_completed_report_survives_rerun_and_edit(self):
        def generate(topic, on_stage):
            outputs = {title: f"Output for {title}" for title in STAGES}
            for i, (title, text) in enumerate(outputs.items()):
                on_stage(i, title, text)
            return outputs

        with patch("pipeline.run_pipeline", side_effect=generate) as run:
            app = self.app()
            app.text_area[0].set_value("Python automation")
            app.button[0].click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(app.session_state.report["complete"])
            self.assertEqual(len(app.tabs), 5)
            app.text_area[1].set_value("My edited post").run()
            self.assertEqual(app.session_state.report["stages"]["Optimized post"], "My edited post")
            self.assertEqual(len(app.get("download_button")), 2)
            self.assertEqual(run.call_count, 1)

    def test_failure_keeps_partial_results_and_hides_provider_error(self):
        def fail(topic, on_stage):
            on_stage(0, STAGES[0], "Research collected")
            raise RuntimeError("private-provider-error")

        with patch("pipeline.run_pipeline", side_effect=fail):
            app = self.app()
            app.text_area[0].set_value("Python automation")
            app.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertFalse(app.session_state.report["complete"])
        self.assertEqual(app.session_state.report["stages"], {"Research": "Research collected"})
        self.assertNotIn("private-provider-error", app.error[0].value)

    def test_missing_configuration_blocks_generation(self):
        with patch("pipeline.validate_configuration", side_effect=ValueError("Set GROQ_API_KEY")), patch("pipeline.run_pipeline") as run:
            app = self.app()
            app.text_area[0].set_value("Python automation")
            app.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(app.warning)
        run.assert_not_called()

    def test_incomplete_research_reports_the_real_stage_failure(self):
        with patch("pipeline.run_pipeline", side_effect=PipelineError("Research reached its iteration limit without a usable answer. Try a more specific topic.")):
            app = self.app()
            app.text_area[0].set_value("Python automation")
            app.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Research reached its iteration limit", app.error[0].value)

    def test_rejected_key_explains_ui_configuration(self):
        from openai import AuthenticationError
        error = AuthenticationError("Invalid key", response=Mock(), body={})
        with patch("pipeline.run_pipeline", side_effect=error):
            app = self.app()
            app.text_area[0].set_value("Python automation")
            app.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Cloud Secrets", app.error[0].value)

    def test_model_permission_error_explains_project_setting(self):
        error = PermissionDeniedError("Model blocked", response=Mock(), body={"code": "model_permission_blocked_project"})
        with patch("pipeline.run_pipeline", side_effect=error):
            app = self.app()
            app.text_area[0].set_value("Python automation")
            app.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("settings/project/limits", app.error[0].value)

    def test_password_gate(self):
        with patch.dict(os.environ, {"APP_PASSWORD": "test-password"}):
            app = self.app()
            self.assertEqual(len(app.text_area), 0)
            app.text_input[0].set_value("incorrect")
            app.button[0].click().run()
            self.assertEqual(app.error[0].value, "Incorrect password.")
            app.text_input[0].set_value("test-password")
            app.button[0].click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(app.session_state.authenticated)
            self.assertEqual(len(app.text_area), 1)


if __name__ == "__main__":
    unittest.main()
