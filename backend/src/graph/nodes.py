import json
import re
import logging
import os
from typing import Any, Dict, List

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from .state import VideoAuditState, ComplianceIssue
from backend.src.services.video_indexer import VideoIndexerService

# configure the logger
logger = logging.getLogger("compliance_qa_pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

#NODE 
def index_video(state:VideoAuditState) -> str:
    """
    Node to index a video using Azure Video Indexer and return the video ID.
    """

    video_url = state.get("video_url")
    video_id_input = state.get("video_id","vid_demo")

    logger.info(f"Starting video indexing for URL: {video_url}")
    
    local_file_name = "temp_audit_video.mp4"

    try:
        # Download the video to a local file
        video_indexer = VideoIndexerService()
        if "youtube.com" in video_url or "youtu.be" in video_url:
            logger.info("Detected YouTube URL, using youtube-dl for downloading.")
            local_path = video_indexer.download_video_youtube(video_url, output_path=local_file_name)

        # Index the video using Azure Video Indexer
        azure_video_id  = video_indexer.upload_video(local_path, video_name= video_id_input)
        logger.info(f"Video uploaded to Azure Video Indexer with ID: {azure_video_id}")

        if os.path.exists(local_file_name):
            os.remove(local_file_name)
            logger.info(f"Temporary file {local_file_name} removed after indexing.")
        
        # wait
        raw_insights = video_indexer.wait_for_processing(azure_video_id)

        # extract insights
        clean_data = video_indexer.extract_insights(raw_insights)
        logger.info(f"Extracted insights for video ID {azure_video_id}")
        return clean_data

    
    except Exception as e:
        logger.error(f"Error during video indexing: {str(e)}")
        return {"error": str(e),
                "video_id": video_id_input,
                "video_url": video_url,
                "status": "FAILED",
                "OCR_text": [],
                }

# node 2 : Compliance check
def compliance_check(state:VideoAuditState) -> Dict[str, Any]:

    '''
    Performs Retrivel Augemented Generation (RAG) to check for compliance issues in the video based on the extracted insights and a predefined set of compliance rules.
    '''
    logger.info(f"Starting compliance check for video ID: {state['video_id']}")
    transcript = state.get("transcripts", "")
    if not transcript:
        logger.warning("No transcript available for compliance check.")
        return {
            "compliance_result": [],
            "final_status": "FAIL",
            "final_report": "No transcript available for analysis."
        }
    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        temperature=0.0
        )
    embedding=AzureOpenAIEmbeddings(
            azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        )
    
    vector_store = AzureSearch(
        azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_key=os.getenv("AZURE_SEARCH_API_KEY"),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
        embedding_function=embedding.embed_query
    )   

    ocr_text = state.get("ocr_text", [])
    query_text = f'{transcript} {"\n".join(ocr_text)}'
    # perform similarity search to retrieve relevant compliance rules
    docs = vector_store.similarity_search(query_text, k=3)
    for doc in docs:
        print("-" * 80)  
        print(f"Source: {doc.metadata['source']}")
        print(f"Chunk Content: {doc.page_content}")
    relevant_rules = "\n\n".join([doc.page_content for doc in docs]) # combine the chunked content
    #
    system_prompt = f"""
        you are a senior brand compliance officer.
        OFFICE REGULATIONS:
        {relevant_rules}
        INSTRUCTIONS:
        1. Analyze the Transcript and OCR text for any potential compliance issues based on the above office regulations.
        2. Identify ANY voilation of the rules in the transcript and OCR text.
        3. Return strictly JSON in the following format:
        {{
            "compliance_issues": [
                {{
                    "category": "Category of the compliance issue based on the office regulations",
                    "description": "Detailed description of the compliance issue identified in the video",
                    "severity": "Severity level of the issue (e.g., Low, Medium, High)",
                    "timestamp": "Timestamp in the video where the issue occurs (if applicable)"
                }},
                ...
            ],
            'status': "FAIL",
            "final_report": "A concise summary of the compliance issues found and any recommendations for addressing them."
        }}
        If no voilations are found, return an empty list for compliance_issues and set status to PASS.
        """
    user_message = f"""
    VIDEO_METADATA: {state.get("video_metadata", {})}
    Transcript: {transcript}
    ON-SCREEN TEXT: {ocr_text}
    """

    try:
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])
        response_content = response.content # This pulls the raw text generated by the LLM.
        logger.info(f"LLM response received for compliance check: {response_content}")
        if "```" in response_content:
            response_content = re.search(r"```json(.*?)```", response_content, re.DOTALL).group(1) # Extract JSON content from markdown code block if present
        result = json.loads(response_content)
        return {
            "compliance_result": result.get("compliance_issues", []),
            "final_status": result.get("status", "FAIL"),
            "final_report": result.get("final_report", "")
        }
    except Exception as e:
        logger.error(f"JSON decoding error: {str(e)} - Response content: {response_content}")
        return {
            "error": str(e),
            "final_status": "FAIL",
            "final_report": "Error parsing LLM response."
        }
        

