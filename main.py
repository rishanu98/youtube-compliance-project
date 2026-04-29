import logging
import json
import uuid
from pprint import pprint

from dotenv import load_dotenv
load_dotenv()

from backend.src.graph.workflow import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger("compliance_qa_pipeline")

def run_cli_simulation():
    """
    Simulate a CLI input for the compliance QA pipeline.

    This function orchestrates the entire compliance checking process by:
        1. Simulating a video URL input (e.g., from YouTube).
        2. Generating a unique video ID for tracking.
        3. Creating an initial state for the workflow with the simulated input.
        4. Invoking the workflow with the initial state and printing the compliance results.
    """

    logger.info(f"Starting CLI simulation for compliance QA pipeline")
    
    # Simulated input data
    video_url = "https://www.youtube.com/watch?v=Cyzz4tgLJXE"  # Example YouTube URL
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
    logging.info(f"Initial Payload: {json.dumps(initial_state, indent=2)}")
    # Run the workflow with the initial state
    try:
        result = app.invoke(initial_state) # triggers the langgraph workflow execution with the initial state passes through START -> Indexer-> Auditor -> END
        print("n-----Final Result from Workflow-----")
        print("\nCompliance QA Pipeline Result:")
        print(f'Video ID: {result['video_id']}')
        print(f'Final Status: {result['final_status']}')
        print(f'Compliance Report: {result['compliance_result']}')

        if result.get("compliance_result"):
            print("\nCompliance Issues Detected:")
            for issue in result["compliance_result"]:
                print(f"- Category: {issue['category']}, Severity: {issue['severity']}, Description: {issue['description']}, Timestamp: {issue.get('timestamp', 'N/A')}")
        else:
            print("\nNo compliance issues detected.")
    except Exception as e:
        logger.error(f"Error during workflow execution: {str(e)}")
        raise e
    
if __name__ == "__main__":
    run_cli_simulation()