import os
import logging
from azure.monitor.opentelemetry import configure_azure_monitor

# Configure Azure Monitor with OpenTelemetry
logger = logging.getLogger("compliance_qa_pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def setup_telemetry():
    '''
    Sets up Azure Monitor telemetry using OpenTelemetry.
    '''
    connection_string = os.getenv("APPLICATION_INSIGHTS_CONNECTION_STRING")
    if not connection_string:
        logger.warning("telemetry not set. It will not be sent to Azure Monitor.")
        return None
    
    try:
        configure_azure_monitor(connection_string=connection_string, logger_name="compliance_qa_pipeline")
        logger.info("Azure Monitor telemetry configured successfully.")
        
    except Exception as e:
        logger.error(f"Error configuring Azure Monitor telemetry: {str(e)}")
        raise e
