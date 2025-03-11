#!/usr/bin/env python3
"""
Zdog Applet Generator
----------------------
Generate interactive 3D applets using Zdog from CSV content files.
"""

import csv
import os
import sys
import json
import re
from pathlib import Path

# Import Zdog generator
from .zdog_generator import generate_zdog_scenes_for_html

# Directory constants
TEMPLATE_DIR = "templates"
JS_DIR = "js"
OUTPUT_DIR = "output"

def read_csv_file(file_path):
    """Read CSV file and return content as dictionary."""
    content = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    field, value = row[0], row[1]
                    content[field] = value
        return content
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)

def extract_items(content, prefix):
    """Extract items with a common prefix from content dictionary."""
    items = []
    i = 1
    while True:
        key = f"{prefix}_{i}"
        if key in content:
            items.append(content[key])
            i += 1
        else:
            break
    return items

def process_connect_questions(content):
    """Process connect questions into a structured format."""
    questions = []
    i = 1
    
    while True:
        # Check if we have a question for this index
        question_key = f"connect_question_{i}"
        if question_key not in content:
            break
            
        # Create question object
        question = {
            "question": content[question_key],
            "options": []
        }
        
        # Add correct option
        correct_key = f"connect_option_correct_{i}_1"
        if correct_key in content:
            question["options"].append({
                "text": content[correct_key],
                "correct": "true"
            })
            
        # Add wrong options
        j = 1
        while True:
            wrong_key = f"connect_option_wrong_{i}_{j}"
            if wrong_key in content:
                question["options"].append({
                    "text": content[wrong_key],
                    "correct": "false"
                })
                j += 1
            else:
                break
                
        # Only add the question if it has options
        if question["options"]:
            questions.append(question)
            
        i += 1
        
    return questions

def generate_zdog_applet(csv_file, output_file=None):
    """Generate HTML applet with Zdog visualizations from CSV file."""
    # Read and process CSV content
    content = read_csv_file(csv_file)
    
    # Extract data
    given_items = extract_items(content, "given")
    tofind_items = extract_items(content, "tofind")
    compute_steps = extract_items(content, "compute_step")
    connect_questions = process_connect_questions(content)
    
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
    
    # Generate Zdog scenes JSON
    try:
        print("Generating Zdog scenes from content...")
        # Use the Zdog generator to create scene configurations
        zdog_scenes_json = generate_zdog_scenes_for_html(csv_file)
        print("Generated Zdog scenes configuration")
    except Exception as e:
        print(f"Error generating Zdog scenes: {e}")
        sys.exit(1)
    
    # Load HTML template
    template_path = os.path.join(TEMPLATE_DIR, "zdog_template.html")
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
    
    # Add Zdog scenes JSON
    html = html.replace('{{zdog_scenes_json}}', zdog_scenes_json)
    
    # Replace JSON data
    html = html.replace('{{given_items}}', json.dumps(given_items))
    html = html.replace('{{tofind_items}}', json.dumps(tofind_items))
    html = html.replace('{{compute_steps}}', json.dumps(compute_steps))
    html = html.replace('{{connect_questions}}', json.dumps(connect_questions))
    
    # Write HTML file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"3D applet generated successfully: {output_file}")
        return output_file
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)

def create_zdog_sample(output_file="sample/metal-cubes-zdog.csv"):
    """Create a metal cubes challenge CSV file with Zdog configuration."""
    content = [
        ["field", "value"],
        ["title", "Metal Cubes Challenge"],
        ["question_text", "<span class=\"highlight-given\">Five metal cubes with sides of 5 cm</span> were melted and casted into a bigger cube. Find the <span class=\"highlight-tofind\">volume</span> of the new cube."],
        ["given_1", "5 metal cubes with sides of 5 cm"],
        ["tofind_1", "Volume of new cube"],
        ["compute_step_1", "Formula: Volume = s³"],
        ["compute_step_2", "Solution: Volume of small cube = 5³"],
        ["compute_step_3", "= 5 × 5 × 5"],
        ["compute_step_4", "= 125 cm³"],
        ["compute_step_5", "Volume of large cube = 125 × 5"],
        ["compute_step_6", "= 625 cm³"],
        ["connect_question_1", "What is the formula for the volume of a cube?"],
        ["connect_option_correct_1_1", "V = s³"],
        ["connect_option_wrong_1_1", "V = s²"],
        ["connect_option_wrong_1_2", "V = 6s²"],
        ["connect_option_wrong_1_3", "V = 4πs³/3"],
        ["visualization_type", "cubes_to_larger_cube"],
        ["visualization_params", "{\"small_cube_count\": 5, \"small_cube_size\": 5, \"small_cube_color\": \"#f47983\"}"]
    ]
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(content)
        
    print(f"Zdog metal cubes example CSV created: {output_file}")

if __name__ == "__main__":
    import argparse
    
    # Create argument parser
    parser = argparse.ArgumentParser(description='Generate 3D HTML applet from CSV content using Zdog')
    parser.add_argument('csv_file', help='Path to the CSV file')
    parser.add_argument('--output', help='Output HTML file path')
    parser.add_argument('--create-sample', action='store_true', help='Create sample Zdog CSV file')
    
    args = parser.parse_args()
    
    # Create necessary directories
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    os.makedirs(JS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if args.create_sample:
        create_zdog_sample()
        print("Sample file created. Use it with: python zdog_applet_generator.py sample/metal-cubes-zdog.csv")
        sys.exit(0)
    
    # Generate applet
    output_file = args.output if args.output else None
    
    result = generate_zdog_applet(args.csv_file, output_file)
    
    if result:
        print(f"Applet generated: {result}")
        print(f"Open this file in a web browser to view the interactive 3D visualization.")
