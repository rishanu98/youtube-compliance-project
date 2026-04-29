# Compliance QA Pipeline

An AI-powered pipeline that audits videos for brand/compliance violations.

The project:
- Downloads and indexes a video (currently focused on YouTube URLs)
- Extracts transcript + OCR insights using Azure Video Indexer
- Retrieves relevant compliance rules from Azure AI Search (RAG)
- Uses Azure OpenAI + LangGraph to generate a structured compliance report
- Exposes the workflow through a FastAPI endpoint and a local CLI simulation

## Project Structure

```text
ComplianceQAPipeline/
|- main.py                            # CLI simulation entrypoint
|- requirements.txt
|- backend/
|  |- scripts/
|  |  |- index_document.py            # Index policy PDFs into Azure AI Search
|  |- data/
|  |  |- documents/                   # Place compliance PDFs here
|  |- src/
|     |- api/
|     |  |- server.py                 # FastAPI app
|     |  |- telemetry.py              # Azure Monitor setup
|     |- graph/
|     |  |- state.py                  # LangGraph state schema
|     |  |- nodes.py                  # index_video + compliance_check nodes
|     |  |- workflow.py               # Graph wiring
|     |- services/
|        |- video_indexer.py          # Azure Video Indexer integration
```

## Prerequisites

- Python `3.12+`
- Azure resources:
  - Azure OpenAI (chat + embedding deployments)
  - Azure AI Search
  - Azure Video Indexer account
  - (Optional) Application Insights for telemetry
- Access to download public YouTube videos (via `yt-dlp`)

## Setup

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create a `.env` file in the project root and configure environment variables.

### Required Environment Variables

#### Azure OpenAI
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_CHAT_DEPLOYMENT`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`

#### Azure AI Search (runtime RAG)
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_API_KEY`
- `AZURE_SEARCH_INDEX_NAME`

#### Azure Video Indexer
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`
- `AZURE_VI_ACCOUNT_ID`
- `AZURE_VI_NAME`
- `AZURE_SEARCH_VI_LOCATION` (defaults to `trial` if not set)

#### Optional telemetry
- `APPLICATION_INSIGHTS_CONNECTION_STRING`

### Additional Variables Used by `backend/scripts/index_document.py`

The document indexing script uses slightly different names for some settings:
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_INDEX_NAME`
- `AZURE_SEARCH_ADMIN_KEY`

## Index Compliance Documents (One-time / as needed)

Add your policy/compliance PDFs to:
- `backend/data/documents/`

Then run:

```powershell
python backend/scripts/index_document.py
```

This chunks PDF content, creates embeddings, and uploads them into your Azure AI Search index.

## Run the Project

### Option 1: CLI simulation

```powershell
python main.py
```

This runs the LangGraph pipeline with a sample YouTube URL from `main.py`.

### Option 2: FastAPI server

```powershell
uvicorn backend.src.api.server:app --reload
```

Health check:
- `GET /health`

Audit endpoint:
- `POST /audit_video`
- Request body:

```json
{
  "video_url": "https://www.youtube.com/watch?v=Cyzz4tgLJXE"
}
```

Example curl:

```bash
curl -X POST "http://127.0.0.1:8000/audit_video" \
  -H "Content-Type: application/json" \
  -d "{\"video_url\":\"https://www.youtube.com/watch?v=Cyzz4tgLJXE\"}"
```

## Workflow Overview

1. `index_video` node:
   - Downloads video
   - Uploads to Azure Video Indexer
   - Waits for processing
   - Extracts transcript/OCR insights
2. `compliance_check` node:
   - Retrieves relevant policy chunks from Azure AI Search
   - Prompts Azure OpenAI for strict JSON compliance output
   - Produces `compliance_result`, `final_status`, and `final_report`

## Notes

- Temporary downloaded media files (`*.mp4`, `*.mkv`) are git-ignored.
- The repo currently contains both `pyproject.toml` and `requirements.txt`; dependency installation is currently driven by `requirements.txt`.
- Keep `.env` private and never commit secrets.