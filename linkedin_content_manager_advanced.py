"""
LinkedIn Content Manager - CLI Version

Main entry point for running the CrewAI pipeline via command line.
Uses modular components: agents, tasks, tools, config, and utils.
"""

from runtime_check import check_python

check_python()

import os
import sys
import asyncio
from dotenv import load_dotenv
from crewai import Crew

# Import modular components
from agents import get_all_agents
from tasks import get_all_tasks
from config import OUTPUT_SETTINGS
from utils import Validators, OutputFormatter, logger

# Load environment variables
load_dotenv()

# ============================================================================
# CREW CREATION & EXECUTION
# ============================================================================

def create_linkedin_crew(topic: str, agents: tuple, tasks: tuple) -> Crew:
    """Create and configure the CrewAI team."""
    return Crew(
        agents=list(agents),
        tasks=list(tasks),
        verbose=True,
        memory=False,
        max_rpm=8,
        process="sequential",
    )


def main():
    """Main entry point."""
    try:
        if "--smoke-test" in sys.argv:
            from config.llm import create_llm
            reply = create_llm().invoke("Reply with exactly: Groq connection successful")
            print(reply.content)
            return reply.content

        from config.llm import validate_llm_key
        validate_llm_key()
        if not Validators.validate_api_keys({"SERPER_API_KEY": os.getenv("SERPER_API_KEY")}):
            sys.exit(1)
        agents = get_all_agents()
        tasks = get_all_tasks(agents)

        # Get topic from user
        topic = input("\n📝 Enter the topic/niche for your LinkedIn post: ").strip()
        
        if not Validators.validate_topic(topic):
            sys.exit(1)
        
        logger.info(f"Starting pipeline for topic: {topic}")
        
        # Create and run crew
        crew = create_linkedin_crew(topic, agents, tasks)
        print(f"\n🚀 Processing: {topic}\n")
        result = crew.kickoff(inputs={"topic": topic})
        
        # Display result
        print("\n" + "=" * 80)
        print("✅ CONTENT GENERATED")
        print("=" * 80)
        print(result)
        print("=" * 80)
        
        logger.info("Pipeline completed successfully")
        return result
        
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
    finally:
        # Clean up event loop and thread pools
        try:
            # Close any pending event loops
            loop = asyncio.get_event_loop()
            if loop and not loop.is_closed():
                loop.close()
        except RuntimeError:
            # Event loop might already be closed or doesn't exist
            pass

if __name__ == "__main__":
    main()
