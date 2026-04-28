import operator
from typing import Annotated, List, Optional, TypedDict, Any

class ComplianceIssue(TypedDict):
    '''
    A dictionary representing a compliance issue found in a video.
    '''
    category: str # Type of compliance
    description: str # Specific detail of the compliance
    severity: str # Low, Medium, High
    timestamp: Optional[str] # Timestamp in the video where the issue occurs, if applicable

class VideoAuditState(TypedDict):
    '''
    Defines the data schema for language graph content related to video audits.
    '''
    video_id: str
    video_url: str
    
    # Ingestion and extraction details
    local_file_path: Optional[str]
    video_metadata: Optional[dict] # e.g., duration, resolution, format
    transcript: Optional[str] # speech to text transcription of the video
    ocr_text: List[str] # text extracted from video frames using OCR

    # compliance result
    # list of compliance issues detected by AI agent
    compliance_result : Annotated[list[ComplianceIssue], operator.add] # Annotated lets you enrich a type with additional information

    # final output
    final_status: str # PASS | FAIL
    final_report: str # markdown format

    # system observability
    # list of system level crashes
    errors: Annotated[List[str], operator.add] # list of error messages encountered during processing

    
