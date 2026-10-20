import unittest
import os
from unittest.mock import patch

from crewai import Agent, Crew, Task
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from pipeline import STAGES, run_pipeline
from streamlit.testing.v1 import AppTest


class PipelineTests(unittest.TestCase):
    def test_real_crew_callbacks_return_all_five_outputs_without_api_calls(self):
        model = FakeListChatModel(responses=["Final Answer: Completed stage"] * 5)
        agents = tuple(Agent(role=f"Agent {i}", goal="Write content", backstory="A concise writer", llm=model, verbose=False, allow_delegation=False) for i in range(5))
        tasks = tuple(Task(description="Write one sentence about {topic}", expected_output="One sentence", agent=agent) for agent in agents)
        crew = Crew(agents=list(agents), tasks=list(tasks), memory=False, verbose=False)
        progress = []
        with patch("pipeline.validate_configuration"), patch("agents.get_all_agents", return_value=agents), patch("tasks.get_all_tasks", return_value=tasks), patch("pipeline.create_linkedin_crew", return_value=crew):
            outputs = run_pipeline("Python", on_stage=lambda i, title, text: progress.append((i, title, text)))
        self.assertEqual(list(outputs), list(STAGES))
        self.assertEqual([row[0] for row in progress], list(range(5)))
        self.assertTrue(all(text == "Completed stage" for text in outputs.values()))

    def test_ui_displays_real_runner_results_and_downloads(self):
        model = FakeListChatModel(responses=["Final Answer: Content ready"] * 5)
        agents = tuple(Agent(role=f"Agent {i}", goal="Write content", backstory="A concise writer", llm=model, verbose=False, allow_delegation=False) for i in range(5))
        tasks = tuple(Task(description="Write about {topic}", expected_output="Content", agent=agent) for agent in agents)
        crew = Crew(agents=list(agents), tasks=list(tasks), memory=False, verbose=False)
        with patch.dict(os.environ, {"APP_PASSWORD": ""}), patch("pipeline.validate_configuration"), patch("agents.get_all_agents", return_value=agents), patch("tasks.get_all_tasks", return_value=tasks), patch("pipeline.create_linkedin_crew", return_value=crew):
            app = AppTest.from_file("streamlit_app.py", default_timeout=30).run()
            app.text_area[0].set_value("Python automation")
            app.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        self.assertTrue(app.session_state.report["complete"])
        self.assertEqual(list(app.session_state.report["stages"]), list(STAGES))
        self.assertEqual(len(app.tabs), 5)
        self.assertEqual(len(app.get("download_button")), 2)


if __name__ == "__main__":
    unittest.main()
