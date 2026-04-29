import uuid
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

from dotenv import load_dotenv
load_dotenv(override=True)

from backend.src.api.telemetry import setup_telemetry
from backend.src.graph.workflow import app as compliance_graph
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("compliance_qa_pipeline")

app = FastAPI(title="Compliance QA Pipeline API",
              description="API for video compliance auditing using AI agents",
              version="1.0.0")

# define pydantic model for request body
class VideoAuditRequest(BaseModel):
    video_url: str

class ComplianceIssue(BaseModel):
    category: str
    description: str
    severity: str
    timestamp: Optional[str]

class AuditResponse(BaseModel):
    session_id: str
    video_id: str
    status: str
    final_report: str
    compliance_result: Optional[list[ComplianceIssue]]

@app.post("/audit_video", response_model=AuditResponse)
async def audit_video(request: VideoAuditRequest) -> Any:
    '''
    Endpoint to initiate the video audit process.
    '''
    session_id = str(uuid.uuid4())
    logger.info(f"Received audit request for video: {request.video_url} with session ID: {session_id}")

    try:
        # Initialize the graph state
        initial_state = {
            "video_url": request.video_url,
            "video_id": f"vid_{session_id[:8]}", # generate a unique video ID based on session ID
            "compliance_result": [], # initialize empty compliance result list
            "errors": [] # initialize empty errors list for observability
        }

        # Run the compliance graph workflow
        final_state = compliance_graph.invoke(initial_state)

        # Prepare the response
        response = AuditResponse(
            session_id=session_id,
            video_id=final_state.get("video_id", ""),
            status=final_state.get("final_status", "UNKNOWN"),
            final_report=final_state.get("final_report", "No report generated."),
            compliance_result=final_state.get("compliance_result", [])
        )

        logger.info(f"Completed audit for session ID: {session_id} with status: {response.status}")
        return response

    except Exception as e:
        logger.error(f"Error processing audit for session ID: {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")

# health check endpoint
@app.get("/health")
def health_check():
    '''
    Health check endpoint to verify that the API is running.
    '''
    return {"status": "healthy"}