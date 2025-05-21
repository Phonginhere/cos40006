#!/usr/bin/env python3
"""
Wrapper script to run the pipeline with proper module imports.
This ensures the pipeline module can be imported correctly.
"""

import os
import sys
import argparse
import importlib

# Make sure we're running from the src directory for all relative paths
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Force reload the utils module to ensure we get the latest version
import pipeline.utils as utils
print("Loading utils module...")
importlib.reload(utils)
print("Reloading utils module...")

# Debug import check
print(f"utils module functions: {dir(utils)}")

# Import pipeline modules - do this AFTER module reload
from pipeline.main import main

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the pipeline with specified model')
    parser.add_argument('--model', type=str, default="gpt-4.1-mini",
                        help='Model name to use for the pipeline')
    args = parser.parse_args()
    
    try:
        # Load API key first
        utils.load_api_key()
        # Then set the model
        print(f"Setting model to: {args.model}")
        # Set the current LLM
        utils.CURRENT_LLM = args.model
        # Update dependent paths
        persona_abbr = utils.get_persona_abbreviation()
        utils.ROOT_RESULTS_DIR = os.path.join("results", persona_abbr, utils.CURRENT_LLM)
        utils.USE_CASE_DIR = os.path.join(utils.ROOT_RESULTS_DIR, "use_cases")
        utils.USE_CASE_TASK_EXTRACTION_DIR = os.path.join(utils.ROOT_RESULTS_DIR, "use_case_task_extraction")
        utils.USER_STORY_DIR = os.path.join(utils.ROOT_RESULTS_DIR, "user_stories")
        
        # Set up conflict directories
        utils.USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(utils.ROOT_RESULTS_DIR, "conflicts_within_one_group")
        utils.USER_STORY_CONFLICT_ACROSS_TWO_GROUPS_DIR = os.path.join(utils.ROOT_RESULTS_DIR, "conflicts_across_two_groups")
        
        # Update functional and non-functional directories
        utils.FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(
            utils.USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, "functional_user_stories"
        )
        utils.NON_FUNCTIONAL_USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR = os.path.join(
            utils.USER_STORY_CONFLICT_WITHIN_ONE_GROUP_DIR, "non_functional_user_stories"
        )
        
        # Run the main pipeline
        main()
    except Exception as e:
        print(f"Error running pipeline: {e}")
