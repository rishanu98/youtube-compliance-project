import os 
import time
import logging 
import requests
import yt_dlp
from azure.identity import DefaultAzureCredential

logger = logging.getLogger('Video-Indexer')

class VideoIndexerService:
    def __init__(self):
        self.subscription_key = os.getenv("AZURE_SUBSCRIPTION_ID")
        self.location = os.getenv("AZURE_SEARCH_VI_LOCATION", "trial")
        self.account_id = os.getenv("AZURE_VI_ACCOUNT_ID")
        self.resource_group = os.getenv("AZURE_RESOURCE_GROUP")
        self.vi_name = os.getenv("AZURE_VI_NAME", "comp-yt-VI")
        self.access_token = DefaultAzureCredential()

    def get_access_token(self):
        try:
            token = self.access_token.get_token("https://management.azure.com/.default")
            return token.token
        except Exception as e:
            logger.error(f"Error obtaining Azure access token: {str(e)}")
            raise
    def get_account_token(self, arm_access_token):
        
        # It exchanges the token for the Video Indexer 
        
        url = (
            f"https://management.azure.com/subscriptions/{self.subscription_key}"
            f"/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.VideoIndexer/accounts/{self.vi_name}"
            f"/generateAccessToken?api-version=2024-01-01"
        )
        
        headers = {"Authorization": f"Bearer {arm_access_token}"}
        payload = {
            "permissionType": "Contributor",
            "scope": "Account"
            }
        response = requests.post(url, headers = headers, json = payload)
        
        if response.status_code != 200:
            raise Exception (f"Failed to get VI Account Token: {response.text}")
        
        return response.json().get("accessToken")
    def download_video_youtube(self, video_url, output_path): 
        '''
        Downloads a video from YouTube using yt-dlp 
        and saves it to the specified output path.
        
        '''
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_path, # output template
            'quiet': False,
            'no_warnings': False,
            'extactor_args': {'youtube':{'player_client':['android','web']}},
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        logger.info(f"Video downloaded successfully to {output_path}")
        return output_path
    def upload_video(self, video_path, video_name):
        ''' 
        Uploads the video to Azure Video Indexer and returns the video ID.
        '''
        arm_token = self.get_access_token()
        vi_token = self.get_account_token(arm_token)
        url = f"https://api.videoindexer.ai/{self.location}/Accounts/{self.account_id}/Videos"
        params = {
            "accessToken": vi_token,
            "name": video_name,
            "privacy": "Private",
            "videoUrl": None
        }
        logger.info(f"Uploading video {video_name} to Azure Video Indexer.")

        files = {'file': open(video_path, 'rb')}

        response = requests.post(url, params=params, files=files)
        if response.status_code != 200:
            raise Exception(f"Failed to upload video: {response.text}")
        video_id = response.json().get("id")
        return video_id
    
    def wait_for_processing(self, video_id, timeout=1800, interval=30):
        '''
        Polls the Azure Video Indexer API for the processing status of the video until it's completed or failed.
        '''
        processing = True
        start_time = time.time()
        while processing:
            arm_token = self.get_access_token()
            vi_token = self.get_account_token(arm_token)
            url = (
                f"https://api.videoindexer.ai/{self.location}/Accounts/{self.account_id}"
                f"/Videos/{video_id}/Index"
            )
            params = {"accessToken": vi_token}

            response = requests.get(url, params=params)
            if response.status_code != 200:
                raise Exception(f"Failed to get video processing status: {response.text}")
            video_state = response.json().get("state")
            logger.info(f"Current processing state: {video_state}")
            if video_state == 'Processed':
                processing = False
                logger.info(f'The video index has completed. Extracting insights now.')
                return response.json()
            elif video_state == 'Failed':
                processing = False
                logger.error(f"The video index failed for video ID {video_id}.")
            
            if timeout is not None and time.time() - start_time > timeout:
                print(f'Timeout of {timeout} seconds reached. Exiting...')
                break
            time.sleep(interval)
        
    def extract_insights(self, vi_json):
        '''
        Extracts relevant insights from the Azure Video Indexer JSON response.
        '''
        transcript_lines = []
        for v in vi_json.get("videos", []):
            for insights in v.get("insights", {}).get("transcript", []):
                transcript_lines.append(insights.get("text", ""))
        ocr_texts = []
        for v in vi_json.get("videos", []):
            for insights in v.get("insights", {}).get("ocr", []):
                ocr_texts.append(insights.get("text", ""))
        return {"transcripts": transcript_lines,
                "ocr_text": ocr_texts,
                "video_meta_data": {
                    "duration": vi_json.get("summarizedInsights", {}).get("duration", 0),
                    "platform":"youtube"          
                }
            }
        