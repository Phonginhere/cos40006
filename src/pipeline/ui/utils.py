import os
import json
import subprocess
import sys
import time
import io
import zipfile
from datetime import datetime

def limit_words(text: str, limit: int = 25) -> str:
    """Limit text to a specified number of words, adding ellipsis if truncated."""
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]) + "..."

def get_cached_system_summary(utils_instance) -> str:
    """Load the full system summary via Utils instance (no truncation)."""
    try:
        return utils_instance.load_system_summary()
    except Exception as e:
        return f"Error loading system summary: {str(e)}"

def save_uploaded_persona_files(uploaded_files, utils_instance):
    """Save uploaded persona JSON files to the uploaded_persona_dir."""
    os.makedirs(utils_instance.UPLOADED_PERSONA_DIR, exist_ok=True)
    saved_files = []
    for uploaded_file in uploaded_files:
        dest_path = os.path.join(utils_instance.UPLOADED_PERSONA_DIR, uploaded_file.name)
        with open(dest_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        saved_files.append(uploaded_file.name)
    return saved_files

def run_pipeline(main_py_path: str, working_dir: str):
    """
    Run main.py pipeline as subprocess.
    Returns subprocess.Popen object.
    """
    command = [sys.executable, main_py_path]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        cwd=working_dir
    )
    return process

def stop_pipeline(process):
    """
    Stop the running pipeline subprocess gracefully.
    Returns True if stopped, False if error.
    """
    try:
        if process.poll() is None:
            process.terminate()
            time.sleep(1)
            if process.poll() is None:
                process.kill()
        return True
    except Exception:
        return False

def process_with_api(utils_instance, api_key: str, model_name: str, system_name: str, main_py_path: str, working_dir: str):
    """
    Save API key and run pipeline main.py as subprocess, updating Utils instance.
    Returns (message:str, success:bool, process:subprocess.Popen).
    """
    # Save API key in Utils instance and file
    saved = utils_instance.save_api_key(api_key)
    if not saved:
        return "Failed to save API key.", False, None

    # Update current model and system in Utils
    utils_instance.CURRENT_LLM = model_name
    utils_instance.SYSTEM_NAME = system_name

    # Reinitialize paths inside Utils if needed (optional, depends on your design)
    # utils_instance._init_results_paths()

    try:
        process = run_pipeline(main_py_path, working_dir)
        return "Pipeline started successfully.", True, process
    except Exception as e:
        return f"Failed to start pipeline: {str(e)}", False, None

def create_zip_for_folder(folder_path: str):
    """
    Create an in-memory ZIP file for all files under the given folder path.
    Returns BytesIO or None if folder doesn't exist or is empty.
    """
    if not folder_path or not os.path.exists(folder_path):
        return None

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, folder_path)
                zipf.write(full_path, rel_path)
    zip_buffer.seek(0)
    return zip_buffer
