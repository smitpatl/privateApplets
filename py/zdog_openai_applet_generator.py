#!/usr/bin/env python3
"""
Zdog Applet Generator with OpenAI Integration
--------------------------------------------
Generate interactive 3D applets using Zdog and OpenAI from CSV content files.
"""

import csv
import os
import sys
import json
import re
import argparse
from pathlib import Path

# Import Zdog generators from current package
from .zdog_openai_generator import generate_zdog_scenes_for_html, extract_visualization_text
from .zdog_applet_generator import read_csv_file, extract_items, process_connect_questions

# Directory constants - relative to parent directory
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
JS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "js")
OUTPUT_DIR = "output"

def generate_zdog_openai_applet(csv_file, output_file=None, api_key=None):
    """Generate HTML applet with Zdog visualizations from CSV file using OpenAI."""
    # Read and process CSV content
    content = read_csv_file(csv_file)
    
    # Extract data
    compute_steps = extract_items(content, "compute_step")
    check_steps = extract_items(content, "check_step")
    connect_questions = process_connect_questions(content)
    
    # Extract visualization text with OpenAI to get spans from question text if needed
    visualization_text = extract_visualization_text(content, api_key)
    
    # Use extracted spans if available, otherwise fallback to CSV
    given_items = visualization_text['comprehend']['given'] if visualization_text['comprehend']['given'] else extract_items(content, "given")
    tofind_items = visualization_text['comprehend']['tofind'] if visualization_text['comprehend']['tofind'] else extract_items(content, "tofind")
    
    # Determine output paths
    if not output_file:
        # Create output directory based on CSV filename
        csv_name = os.path.basename(csv_file)
        base_name = os.path.splitext(csv_name)[0]
        output_dir = os.path.join(OUTPUT_DIR, base_name)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "index.html")
    else:
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
    
    # Generate Zdog scenes using OpenAI with fallback mechanism
    try:
        print("Generating Zdog scenes with OpenAI...")
        zdog_scenes_json = generate_zdog_scenes_for_html(csv_file, api_key)
        print("Successfully generated Zdog scenes configuration")
    except Exception as e:
        print(f"Error generating Zdog scenes: {e}")
        sys.exit(1)
    
    # Load HTML template without title bar
    template_path = os.path.join(TEMPLATE_DIR, "zdog_template_notitle.html")
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    except Exception as e:
        print(f"Error reading template file: {e}")
        sys.exit(1)
    
    # Ensure JS directory is copied to output
    os.makedirs(os.path.join(output_dir, "js"), exist_ok=True)
    
    # Copy Zdog JS library to output directory
    source_js = os.path.join(JS_DIR, "zdog.dist.min.js")
    target_js = os.path.join(output_dir, "js", "zdog.dist.min.js")
    
    try:
        with open(source_js, 'rb') as src, open(target_js, 'wb') as dst:
            dst.write(src.read())
        print(f"Copied Zdog JS library to {target_js}")
    except Exception as e:
        print(f"Error copying Zdog JS library: {e}")
        sys.exit(1)
    
    # Replace template variables
    html = template.replace('{{title}}', content.get('title', 'Interactive 3D Applet'))
    html = html.replace('{{question_text}}', content.get('question_text', ''))
    
    # Update JS paths to point to parent directory
    html = html.replace('js/zdog.dist.min.js', '../js/zdog.dist.min.js')
    
    # Add Zdog scenes JSON
    html = html.replace('{{zdog_scenes_json}}', zdog_scenes_json)
    
    # Process JSON strings - double escaping control characters to ensure they don't cause issues
    def process_json(items):
        # First, convert to JSON string
        json_str = json.dumps(items)
        # Then escape backslashes again for proper JS string embedding - using string concatenation to avoid f-string issues
        return json_str.replace('\\', '\\' + '\\')
    
    # Replace JSON data
    html = html.replace('{{given_items}}', process_json(given_items))
    html = html.replace('{{tofind_items}}', process_json(tofind_items))
    html = html.replace('{{compute_steps}}', process_json(compute_steps))
    html = html.replace('{{check_steps}}', process_json(check_steps))
    html = html.replace('{{connect_questions}}', process_json(connect_questions))
    
    # Write HTML file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"3D applet generated successfully: {output_file}")
        return output_file
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Create argument parser
    parser = argparse.ArgumentParser(description='Generate 3D HTML applet from CSV content using Zdog and OpenAI')
    parser.add_argument('csv_file', help='Path to the CSV file')
    parser.add_argument('--output', help='Output HTML file path')
    parser.add_argument('--api-key', help='OpenAI API key (or set OPENAI_API_KEY env variable)')
    parser.add_argument('--open', action='store_true', help='Open the generated applet in browser')
    
    args = parser.parse_args()
    
    # Use the API key from arguments if provided, otherwise use the default one in zdog_openai_generator.py
    api_key = args.api_key
    
    # Create necessary directories
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    os.makedirs(JS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate applet
    output_file = args.output if args.output else None
    
    result = generate_zdog_openai_applet(args.csv_file, output_file, api_key)
    
    # Open the generated file if requested
    if args.open and result:
        try:
            import webbrowser
            print(f"Opening {result} in browser...")
            webbrowser.open(f"file://{os.path.abspath(result)}")
        except Exception as e:
            print(f"Error opening file: {e}")
    
    if result:
        print(f"Applet generated: {result}")
        print(f"Open this file in a web browser to view the interactive 3D visualization.")
