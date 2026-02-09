import os
from github import Github
from dotenv import load_dotenv

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import os

# Scopes must match Reader to share token or be consistent
SCOPES = ["https://www.googleapis.com/auth/drive"]

class ExporterAgent:
    def __init__(self):
        load_dotenv()
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo_name = os.getenv("GITHUB_REPO_NAME")
        self.github_client = None
        self.repo = None
        self.drive_service = None

    def _authenticate_drive(self):
        """Authenticates with Google Drive for verify/upload."""
        from google.oauth2 import service_account
        creds = None
        
        # 1. Try Service Account
        if os.path.exists('service_account.json'):
             try:
                 creds = service_account.Credentials.from_service_account_file(
                    'service_account.json', scopes=SCOPES)
             except Exception as e:
                 print(f"Exporter Alert: Service Account error: {e}")

        # 2. Try User Token
        if not creds and os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
        # Refresh logic handling both types if needed, though Service Account handles itself mostly?
        # Creating service
        try:
            self.drive_service = build("drive", "v3", credentials=creds)
            return self.drive_service
        except Exception as e:
            print(f"Exporter Drive Auth Error: {e}")
            return None

    def connect_github(self):
        if not self.github_token:
            print("Exporter Agent: GITHUB_TOKEN not found in .env")
            return

        try:
            self.github_client = Github(self.github_token)
            self.repo = self.github_client.get_user().get_repo(self.repo_name.split("/")[-1])
            print(f"Exporter Agent: Connected to GitHub repo {self.repo_name}")
        except Exception as e:
            print(f"Exporter Agent: Failed to connect to GitHub. Error: {e}")

    def export_to_csv(self, dataframe, filename="output.csv"):
        """Exports DataFrame to a CSV file locally."""
        if dataframe.empty:
            print("Exporter Agent: DataFrame is empty, skipping export.")
            return None
            
        dataframe.to_csv(filename, index=False)
        print(f"Exporter Agent: Saved locally to {filename}")
        return filename

    def upload_to_drive(self, file_path, folder_id=None):
        """Uploads a file to Google Drive."""
        service = self._authenticate_drive()
        if not service:
            print("Exporter Agent: Could not authenticate with Drive.")
            return

        file_metadata = {'name': os.path.basename(file_path)}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaFileUpload(file_path, mimetype='text/csv')
        
        try:
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"Exporter Agent: File ID: {file.get('id')} uploaded to Drive.")
        except Exception as e:
            print(f"Exporter Agent: Failed to upload to Drive: {e}")

    def upload_to_github(self, file_path, commit_message="Update data"):
        """Uploads a file to the GitHub repository."""
        if not self.repo:
            print("Exporter Agent: Not connected to GitHub.")
            return

        with open(file_path, "r") as file:
            content = file.read()

        file_name = os.path.basename(file_path)
        
        try:
            # Check if file exists to update or create
            contents = self.repo.get_contents(file_name)
            self.repo.update_file(contents.path, commit_message, content, contents.sha)
            print(f"Exporter Agent: Updated {file_name} on GitHub.")
        except:
            self.repo.create_file(file_name, commit_message, content)
            print(f"Exporter Agent: Created {file_name} on GitHub.")
