import os
import streamlit as st

def save_api_key_to_file(api_key):
    """Save the API key to file for the pipeline functions to use"""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Save to main project directory as api_key.txt
        api_key_path = os.path.join(project_root, "api_key.txt")
        with open(api_key_path, "w") as file:
            file.write(api_key)
            
        print(f"API key saved to {api_key_path}")
        
        # Reload the API key in the utils module if possible
        try:
            from pipeline import utils
            # Force reload the API key in the utils module
            utils.api_key = utils.load_api_key()
            utils.client.api_key = utils.api_key
        except Exception as e:
            print(f"Note: Could not reload OpenAI client with new key: {e}")
            
        return True
    except Exception as e:
        print(f"Error saving API key: {str(e)}")
        return False
