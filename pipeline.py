"""Shared pipeline runner for the CLI and Streamlit UI."""

from threading import Lock

from config.llm import validate_llm_key
import os


STAGES = ("Research", "Draft", "Critique", "Optimized post", "Publishing brief")
_run_lock = Lock()


def validate_configuration():
    validate_llm_key()
    key = os.getenv("SERPER_API_KEY", "")
    if not key or key.startswith("your_"):
        raise ValueError("Set SERPER_API_KEY in .env or Streamlit secrets.")


def run_pipeline(topic, on_stage=None):
    """Report completed tasks through on_stage(index, title, text)."""
    topic = topic.strip()
    if not 3 <= len(topic) <= 200:
        raise ValueError("Enter a topic between 3 and 200 characters.")
    validate_configuration()
    if not _run_lock.acquire(blocking=False):
        raise ValueError("Another generation is running. Please try again when it finishes.")
    try:
        # Load the agent stack only when generation starts, so setup and
        # browsing saved results do not initialize CrewAI's native libraries.
        from agents import get_all_agents
        from tasks import get_all_tasks
        from linkedin_content_manager_advanced import create_linkedin_crew

        agents = get_all_agents()
        tasks = get_all_tasks(agents)
        outputs = {}

        def callback_for(index, title):
            def completed(output):
                text = output.raw_output.strip()
                if not text or "Agent stopped due to iteration limit" in text:
                    raise ValueError(f"{title} did not finish. Please try again.")
                outputs[title] = text
                if on_stage:
                    on_stage(index, title, text)
            return completed

        for index, (title, task) in enumerate(zip(STAGES, tasks)):
            task.callback = callback_for(index, title)
        crew = create_linkedin_crew(topic, agents, tasks)
        crew.verbose = False
        for agent in agents:
            agent.verbose = False
        crew.kickoff(inputs={"topic": topic})
        return outputs
    finally:
        _run_lock.release()
