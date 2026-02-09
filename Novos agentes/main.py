from agent_reader import ReaderAgent
from agent_organizer import OrganizerAgent
from agent_exporter import ExporterAgent
import os
from dotenv import load_dotenv

def run_system(source_type=None, path_or_id=None, export_local=True, export_drive=False, export_github=False, logger_func=print):
    """
    Runs the full agent pipeline.
    :param source_type: 'DRIVE' or 'LOCAL'.
    :param path_or_id: Drive Folder ID or Local Folder Path.
    :param export_local: Boolean, save to disk.
    :param export_drive: Boolean, save to Drive (same folder as source if Drive, or root).
    :param logger_func: Function to handle logs.
    """
    # Helper to log messages
    def log(msg):
        logger_func(msg)

    load_dotenv()
    
    # Defaults from .env
    if not source_type:
        source_type = os.getenv("SOURCE_TYPE", "DRIVE").upper()
    if not path_or_id:
        if source_type == "LOCAL":
            path_or_id = os.getenv("LOCAL_FOLDER_PATH", "./input_data")
        else:
            path_or_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    # 1. Reader Agent
    log(f"--- STEP 1: READING ({source_type}) ---")
    reader = ReaderAgent()
    
    # Authenticate (Drive)
    if source_type == "DRIVE" or export_drive:
        # If exporting to Drive, we need auth even if reading from Local
        try:
            reader.authenticate()
        except Exception as e:
            log(f"Authentication failed: {e}")
            if source_type == "DRIVE": return "Auth Failed" # Critial if reading from Drive
            # If just exporting, maybe we can accept failure later, but safest is to fail auth.

    # List files
    if source_type == "DRIVE":
        files = reader.list_files(folder_id=path_or_id, source_type="DRIVE")
        # [NEW] Download files for processing
        log(f"Downloading {len(files)} files from Drive...")
        download_count = 0
        for f in files:
            # Decide where to save. Temp folder?
            temp_dir = os.path.join(os.getcwd(), "temp_downloads")
            local_path = reader.download_file(f['id'], f['name'], temp_dir)
            if local_path:
                f['local_path'] = local_path
                download_count += 1
        log(f"Downloaded {download_count} files.")

    else:
        files = reader.list_files(override_path=path_or_id, source_type="LOCAL")
        # For local, 'id' IS the path, but let's be explicit
        for f in files:
            f['local_path'] = f['id']
    
    if not files: log("No files found.")

    log(f"Found {len(files)} files/records.")

    # 2. Organizer Agent
    log("\n--- STEP 2: ORGANIZING ---")
    organizer = OrganizerAgent()
    processed_df = organizer.process_data(files, logger_func=log)

    # 3. Exporter Agent
    log("\n--- STEP 3: EXPORTING ---")
    exporter = ExporterAgent()
    
    csv_file = None
    
    # Determine Output Path
    # If Local Source and Export Local, save in source folder.
    # Otherwise/Default, save in current working directory.
    filename = "relatorio_final.csv"
    if source_type == "LOCAL" and path_or_id and os.path.isdir(path_or_id):
        output_path = os.path.join(path_or_id, filename)
    else:
        output_path = filename

    # Always create file (needed for upload)
    csv_file = exporter.export_to_csv(processed_df, output_path)
    
    if export_local:
        log(f"Saved locally to: {csv_file}")
    
    # Drive Export
    if export_drive:
        if csv_file:
            log("Uploading to Google Drive...")
            # If source was Drive, upload to same folder? Or explicit ID?
            # For now, let's use path_or_id if source was Drive, else None (Root)
            dest_id = path_or_id if source_type == "DRIVE" else None
            exporter.upload_to_drive(csv_file, folder_id=dest_id)
            log("Uploaded to Drive.")
    
    # GitHub Export (Optional - Env Controlled + GUI Flag)
    github_token = os.getenv("GITHUB_TOKEN")
    if export_github and github_token:
        log("Connecting to GitHub...")
        exporter.connect_github()
        if csv_file:
            exporter.upload_to_github(csv_file)
            log("Uploaded to GitHub.")
    elif export_github and not github_token:
        log("GitHub Export requested but GITHUB_TOKEN not found in .env")
    else:
        # log("Skipping GitHub upload.")
        pass

    log("--- EXECUTION FINISHED ---")
    log("--- EXECUTION FINISHED ---")
    return csv_file

def main():
    # CLI Entry point
    run_system()

if __name__ == "__main__":
    main()
