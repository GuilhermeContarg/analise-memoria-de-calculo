import os
import glob
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]

class ReaderAgent:
    def __init__(self):
        load_dotenv()
        self.source_type = os.getenv("SOURCE_TYPE", "DRIVE").upper()
        self.local_folder_path = os.getenv("LOCAL_FOLDER_PATH", "./input_data")
        self.creds = None
        self.service = None

    def authenticate(self):
        """Authenticates with Google Drive API."""
        self.creds = None
        
        # 1. Try Service Account (Cloud Production)
        if os.path.exists('service_account.json'):
            try:
                from google.oauth2 import service_account
                self.creds = service_account.Credentials.from_service_account_file(
                    'service_account.json', scopes=SCOPES)
                print("Reader Agent: Authenticated with Service Account.")
            except Exception as e:
                print(f"Reader Agent: Service Account Auth failed: {e}")

        # 2. Key User Token (Local / Fallback)
        if not self.creds: 
             if os.path.exists("token.json"):
                self.creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except:
                    self.creds = None
            
            # Interactive flow (Only works locally)
            if not self.creds and not os.path.exists('service_account.json'):
                try:
                     flow = InstalledAppFlow.from_client_secrets_file(
                        "credentials.json", SCOPES)
                     self.creds = flow.run_local_server(port=0)
                     with open("token.json", "w") as token:
                        token.write(self.creds.to_json())
                except:
                     print("Reader Agent: Interactive auth failed (headless environment?)")

        try:
            self.service = build("drive", "v3", credentials=self.creds)
            print("Reader Agent: Authenticated successfully with Google Drive.")
        except Exception as e:
            print(f"An error occurred: {e}")
            self.service = None

    def list_files(self, folder_id=None, source_type=None, override_path=None):
        """Lists files based on the configured or overridden source type."""
        # Determine source and path (override takes precedence)
        current_source = source_type if source_type else self.source_type
        current_path = override_path if override_path else self.local_folder_path
        
        if current_source == "LOCAL":
            return self._list_local_files(current_path)
        else:
            return self._list_drive_files(folder_id)

    def _list_local_files(self, folder_path):
        """Lists files from the local directory."""
        if not os.path.exists(folder_path):
            print(f"Reader Agent: Local folder '{folder_path}' does not exist.")
            return []
        
        files = []
        for filepath in glob.glob(os.path.join(folder_path, "*")):
            if os.path.isfile(filepath):
                files.append({
                    "id": filepath,
                    "name": os.path.basename(filepath),
                    "mimeType": "application/octet-stream" # Generic local type
                })
        
        print(f"Reader Agent: Found {len(files)} files in local folder: {folder_path}")
        return files

    def _list_drive_files(self, folder_id):
        """Lists files from a specific Google Drive folder."""
        if not self.service: # Helper to auto-auth if needed? Or assume auth'd.
             # self.authenticate() # Be careful about side effects
             print("Reader Agent: Drive Service not initialized. Run authenticate() first.")
             return []

        results = self.service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType)",
            pageSize=1000  # Adjust as needed (max 1000)
        ).execute()
        files = results.get('files', [])
        
        print(f"Reader Agent: Found {len(files)} files in Drive.")
        return files

    def download_file(self, file_id, file_name, destination_folder="temp_downloads"):
        """Downloads a file from Drive to a local folder."""
        if not self.service:
            print("Reader Agent: Drive Service not initialized.")
            return None
            
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
            
        local_path = os.path.join(destination_folder, file_name)
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            with open(local_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    # print(f"Download {int(status.progress() * 100)}%.")
            return local_path
        except Exception as e:
            print(f"Reader Agent: Failed to download {file_name}. Error: {e}")
            return None
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []
