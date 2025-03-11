#!/usr/bin/env python3
"""
Applet Generator and Deployment Script
--------------------------------------------
Generate interactive 3D applets using Zdog and OpenAI from CSV content file
and prepare them for deployment to the public repository.
"""

import os
import sys
import csv
import re
import shutil
from pathlib import Path

# Import generator from current directory
from zdog_openai_applet_generator import generate_zdog_openai_applet, extract_visualization_text

# Constants
CSV_PATH = "applet_data.csv"
OUTPUT_DIR = "generated-applet"
TEMP_DIR = "temp_applet"
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
JS_DIR = os.path.join(os.path.dirname(__file__), "js")

def read_csv_content(csv_path):
    """Read CSV content into a dictionary."""
    content = {}
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    content[row[0]] = row[1]
        return content
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)

def sanitize_applet_name(title):
    """Convert applet title to a valid directory name."""
    # Remove spaces and special characters
    sanitized = re.sub(r'[^\w]', '', title)
    # Ensure it starts with a letter
    if not sanitized or not sanitized[0].isalpha():
        sanitized = "Applet" + sanitized
    return sanitized

def main():
    """Main function to generate and prepare applet for deployment."""
    print("Starting applet generation process...")
    
    # Read CSV content
    csv_content = read_csv_content(CSV_PATH)
    
    # Get applet title and sanitize for directory name
    applet_title = csv_content.get('title', 'Unnamed Applet')
    applet_name = sanitize_applet_name(applet_title)
    
    print(f"Generating applet: {applet_title} (directory: {applet_name})")
    
    # Ensure output directory exists and is empty
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for item in os.listdir(OUTPUT_DIR):
        item_path = os.path.join(OUTPUT_DIR, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)
    
    # Generate applet using the zdog_openai_applet_generator
    try:
        # Get OpenAI API key from environment
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("Warning: OPENAI_API_KEY environment variable not set")
            api_key = None
        
        # Generate the applet
        output_file = os.path.join(OUTPUT_DIR, "index.html")
        generate_zdog_openai_applet(CSV_PATH, output_file, api_key)
        
        # Ensure js directory exists with Zdog library in output
        os.makedirs(os.path.join(OUTPUT_DIR, "js"), exist_ok=True)
        shutil.copy(
            os.path.join(JS_DIR, "zdog.dist.min.js"),
            os.path.join(OUTPUT_DIR, "js", "zdog.dist.min.js")
        )
        
        # Write applet name to file for GitHub Action
        with open("applet_name.txt", "w") as f:
            f.write(applet_name)
        
        print(f"Applet generation complete: {output_file}")
        print(f"Applet name for deployment: {applet_name}")
        
        return 0
    except Exception as e:
        print(f"Error generating applet: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
