import os, logging, glob
from typing import Any, Dict
from dotenv import load_dotenv
from langchain import text_splitter
from langchain import text_splitter
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch

logging.basicConfig(level=logging.INFO,format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("compliance_qa_pipeline")

load_dotenv()  # Load environment variables from .env file

def index_document() -> dict:
    """
    Node to index a document (PDF) and return its content.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))  # Example file path, adjust as needed
    folder_path = os.path.join(current_dir,'../data/documents')
    logger.info("="*60)
    logger.info(f'AZURE_OPENAI_API_KEY:{os.getenv("AZURE_OPENAI_API_KEY")}')
    logger.info(f'AZURE_OPENAI_ENDPOINT:{os.getenv("AZURE_OPENAI_ENDPOINT")}')
    logger.info(f'Embedding deployment model:{os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")}')
    logger.info(f'AZURE_SEARCH_INDEX_NAME:{os.getenv("AZURE_SEARCH_INDEX_NAME")}')
    logger.info(f'AZURE_OPENAI_API_VERSION:{os.getenv("AZURE_OPENAI_API_VERSION")}')

    # validate the required environment variables
    required_env_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME",
        "AZURE_SEARCH_INDEX_NAME",
        "AZURE_OPENAI_API_VERSION"
    ]

    missing_var = [var for var in required_env_vars if not os.getenv(var)]

    if missing_var:
        logger.error(f"Missing required environment variables: {', '.join(missing_var)}")
        return {"error": f"Missing required environment variables: {', '.join(missing_var)}"}
    
    # intialize Azure OpenAI Embeddings and Azure Search client
    try:
        embedding: AzureOpenAIEmbeddings  = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        )

        logger.info("Azure OpenAI Embeddings initialized successfully.")

        index_name: str = os.getenv("AZURE_SEARCH_INDEX_NAME")

        logger.info(f"Intilaizing Azure Search client with index: {index_name}")

        vector_store: AzureSearch = AzureSearch(
                                   azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
                                   index_name=index_name,
                                   azure_search_api_key=os.getenv("AZURE_SEARCH_ADMIN_KEY"),
                                   embedding_function=embedding.embed_query
                                   )
        pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))

        if not pdf_files:
             logger.warning(f'No pdf files found in directory: {folder_path}')

        logger.info(f"Found {len(pdf_files)} PDF files to index.")

        all_docs = []

        for pdf_path in pdf_files:
            loader = PyPDFLoader(str(pdf_path))
            pages = loader.load()

            for page in pages:
                page.metadata["source_file"] = pdf_path.name
                page.metadata["source_path"] = str(pdf_path)

            all_docs.extend(pages)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""]
        )

        chunks = text_splitter.split_documents(all_docs)
        logger.info(f"Split documents into {len(chunks)} chunks for embedding.")

        if chunks:
            try:
                vector_store.add_documents(chunks)
                logger.info("-" * 60)
                logger.info(f"Successfully indexed {len(chunks)} chunks into Azure Search index: {index_name}")
                logger.info("-" * 60)
            except Exception as e:
                logger.error(f"Error adding documents to Azure Search: {str(e)}")
                return {"error": f"Error adding documents to Azure Search: {str(e)}"}
        else:
            logger.warning("No chunks were created from the documents. Check the text splitter configuration.")

    except Exception as e:
        return {"error": str(e), "folder_path": folder_path}
    
if __name__ == "__main__":
    result = index_document()
    if "error" in result:
        logger.error(f"Document indexing failed: {result['error']}")
    else:
        logger.info("Document indexing completed successfully.")