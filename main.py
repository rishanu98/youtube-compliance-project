import logging
import json
import uuid
from pprint import pprint

from dotenv import load_dotenv
load_dotenv()

from backend.src.graph.workflow import app

logger = logging.getLogger("compliance_qa_pipeline")
logger.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def run_cli_simulation():
    """
    Simulate a CLI input for the compliance QA pipeline.
    """
    logger.info("Starting CLI simulation for compliance QA pipeline.")
    
    # Simulated input data
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Example YouTube URL
    video_id = f"vid_{uuid.uuid4().hex[:8]}"  # Generate a unique video ID

    logger.info(f"Simulated input - Video URL: {video_url}, Video ID: {video_id}")

    # Create initial state for the workflow
    initial_state = {
        "video_url": video_url,
        "video_id": video_id,
        "error": [],
        "compliance_issues": []
    }

    print("n-----Initial State for Workflow-----")
    logging.info(f"Initial State: {json.dumps(initial_state, indent=2)}")
    # Run the workflow with the initial state
    try:
        result = app.invoke(initial_state)
        print("n-----Final Result from Workflow-----")
        print("\nCompliance QA Pipeline Result:")
        pprint(result)
    except Exception as e:
        logger.error(f"Error during workflow execution: {str(e)}")
        raise e
    
if __name__ == "__main__":
    run_cli_simulation()