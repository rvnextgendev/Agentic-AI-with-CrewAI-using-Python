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
from pipeline import STAGES, run_pipeline, create_linkedin_crew
from config.environment import refresh_local_environment
from utils import logger

refresh_local_environment()


def main():
    """Main entry point."""
    try:
        if "--smoke-test" in sys.argv:
            from config.llm import create_llm
            reply = create_llm().invoke("Reply with exactly: Groq connection successful")
            print(reply.content)
            return reply.content

        # Get topic from user
        topic = input("\n📝 Enter the topic/niche for your LinkedIn post: ").strip()
        
        
        logger.info(f"Starting pipeline for topic: {topic}")
        
        # Create and run crew
        print(f"\n🚀 Processing: {topic}\n")
        outputs = run_pipeline(topic, verbose=True)
        result = outputs[STAGES[-1]]
        
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
