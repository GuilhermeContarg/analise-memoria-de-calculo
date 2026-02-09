from flask import Flask, render_template, request, Response, jsonify, send_file
import threading
import queue
import time
import os
from main import run_system

app = Flask(__name__)

# Queue to store logs for the current session/request
log_queue = queue.Queue()

def web_logger(message):
    """Callback function to push logs to the queue."""
    log_queue.put(message)

@app.route('/')
def home():
    return render_template('index.html')

# Global variable to store the path of the last generated report
last_report_path = None

@app.route('/api/run', methods=['POST'])
def run_agents():
    global last_report_path
    data = request.json
    source_type = data.get('source_type', 'LOCAL')
    path_or_id = data.get('path_or_id')
    export_drive = data.get('export_drive', False)
    export_github = data.get('export_github', False)
    
    # Validation
    if not path_or_id:
        return jsonify({"error": "Path or ID is required"}), 400

    # Clear queue
    with log_queue.mutex:
        log_queue.queue.clear()

    # Run in separate thread
    def target():
        global last_report_path
        try:
            # Capture the return value from run_system (which should be the path)
            result = run_system(
                source_type=source_type,
                path_or_id=path_or_id,
                export_local=True,
                export_drive=export_drive,
                export_github=export_github,
                logger_func=web_logger
            )
            web_logger(f"DEBUG: run_system returned: {result}")
            
            # Check if result looks like a path or success message
            if result and os.path.exists(str(result)):
                 last_report_path = str(result)
                 web_logger(f"DEBUG: Report path set to: {last_report_path}")
            else:
                 web_logger("DEBUG: Returned path does not exist or is empty.")
            
            web_logger("DONE") # Signal completion
        except Exception as e:
            web_logger(f"CRITICAL ERROR: {e}")
            web_logger("DONE")

    thread = threading.Thread(target=target)
    thread.start()

    return jsonify({"status": "started"})

@app.route('/stream_logs')
def stream_logs():
    def generate():
        while True:
            message = log_queue.get()
            if message == "DONE":
                yield f"data: {message}\n\n"
                break
            yield f"data: {message}\n\n"
    return Response(generate(), mimetype='text/event-stream')

@app.route('/download_report')
def download_report():
    global last_report_path
    if last_report_path and os.path.exists(last_report_path):
        return send_file(last_report_path, as_attachment=True)
    
    # Fallback to local default if global path not set
    file_path = "relatorio_final.csv"
    if os.path.exists(file_path):
         return send_file(file_path, as_attachment=True)
         
    return "File not found", 404

if __name__ == '__main__':
    # Local dev run
    app.run(debug=True, port=8080)
