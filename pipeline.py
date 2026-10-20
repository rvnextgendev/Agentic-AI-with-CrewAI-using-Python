"""Shared pipeline runner for the CLI and Streamlit UI."""

from threading import Lock

from config.llm import validate_llm_key
import os


STAGES = ("Research", "Draft", "Critique", "Optimized post", "Publishing brief")
_run_lock = Lock()


class PipelineError(ValueError):
    """A pipeline failure whose message is safe to display to the user."""


def create_linkedin_crew(topic, agents, tasks, verbose=True):
    from crewai import Crew
    return Crew(agents=list(agents), tasks=list(tasks), verbose=verbose,
                memory=False, max_rpm=8, process="sequential")


def validate_configuration():
    try:
        validate_llm_key()
    except ValueError as exc:
        raise PipelineError(str(exc)) from exc
    key = os.getenv("SERPER_API_KEY", "")
    if not key or key.startswith("your_"):
        raise PipelineError("Set SERPER_API_KEY in .env or Streamlit secrets.")


def run_pipeline(topic, on_stage=None, verbose=False):
    """Report completed tasks through on_stage(index, title, text)."""
    topic = topic.strip()
    if not 3 <= len(topic) <= 200:
        raise PipelineError("Enter a topic between 3 and 200 characters.")
    validate_configuration()
    if not _run_lock.acquire(blocking=False):
        raise PipelineError("Another generation is running. Please try again when it finishes.")
    crew = None
    try:
        # Load the agent stack only when generation starts, so setup and
        # browsing saved results do not initialize CrewAI's native libraries.
        from agents import get_all_agents
        from tasks import get_all_tasks

        agents = get_all_agents()
        tasks = get_all_tasks(agents)
        outputs = {}

        def completed(output):
            index = len(outputs)
            title = STAGES[index]
            text = output.raw_output.strip()
            if not text or "Agent stopped due to iteration limit" in text:
                raise PipelineError(f"{title} reached its iteration limit without a usable answer. Try a more specific topic.")
            outputs[title] = text
            if on_stage:
                on_stage(index, title, text)

        crew = create_linkedin_crew(topic, agents, tasks, verbose=verbose)
        # CrewAI 0.28 overwrites each Task.callback with Crew.task_callback
        # during kickoff. Set the crew-level callback so results are retained.
        crew.task_callback = completed
        for agent in agents:
            agent.verbose = verbose
        crew.kickoff(inputs={"topic": topic})
        if len(outputs) != len(STAGES):
            raise PipelineError("The pipeline finished without returning all stage results. Please retry.")
        return outputs
    finally:
        try:
            if crew is not None:
                controller = getattr(crew, "_rpm_controller", None)
                if controller is not None:
                    controller.stop_rpm_counter()
        finally:
            _run_lock.release()
