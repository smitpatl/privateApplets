#!/usr/bin/env python3
"""
Update Index Script
------------------
Update the index.html file in the public repository to include the new applet.
"""

import os
import sys
import re
import glob
import json
from pathlib import Path
from datetime import datetime

def generate_card_html(applet_name, applet_path, title=None):
    """Generate HTML for an applet card in the index."""
    # Use folder name as title if not provided
    if not title:
        # Replace camelCase with spaces
        title = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', applet_name)
        # Replace underscores with spaces
        title = title.replace('_', ' ')
    
    # Try to get a thumbnail or description, but don't fail if impossible
    description = "Interactive mathematics visualization applet"
    try:
        # Look for an index.html and extract meta description if available
        html_path = os.path.join(applet_path, "index.html")
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                # Try to extract description from meta tag
                desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html_content)
                if desc_match:
                    description = desc_match.group(1)
                # If no description meta tag, look for question text
                elif 'question' in html_content.lower():
                    quest_match = re.search(r'<p id="questionText">(.*?)</p>', html_content)
                    if quest_match:
                        description = quest_match.group(1)
                        # Remove HTML tags
                        description = re.sub(r'<[^>]+>', '', description)
                        # Truncate if too long
                        if len(description) > 150:
                            description = description[:147] + "..."
    except Exception as e:
        print(f"Warning: Could not extract description for {applet_name}: {e}")
    
    # Generate card HTML
    card_html = f"""
    <div class="card">
        <div class="card-content">
            <h2 class="card-title">{title}</h2>
            <p class="card-description">{description}</p>
        </div>
        <a href="./{applet_name}/" class="card-button">Open Applet</a>
    </div>
    """
    return card_html

def update_index_html(public_repo_path):
    """Update the index.html file with all applets."""
    index_path = os.path.join(public_repo_path, "index.html")
    
    # Check if index.html exists, if not create it
    if not os.path.exists(index_path):
        create_new_index_html(index_path)
        return
    
    try:
        # Read existing index.html
        with open(index_path, 'r', encoding='utf-8') as f:
            index_content = f.read()
        
        # Find the cards container
        cards_match = re.search(r'<div\s+class="cards-container">(.*?)</div>\s*<!--\s*end\s+cards\s*-->', 
                              index_content, re.DOTALL)
        
        if not cards_match:
            print("Warning: Could not find cards container in index.html")
            create_new_index_html(index_path)
            return
        
        # Get all applet directories
        applet_dirs = []
        for item in os.listdir(public_repo_path):
            item_path = os.path.join(public_repo_path, item)
            if os.path.isdir(item_path) and item != "js" and not item.startswith('.'):
                # Check if it has an index.html file
                if os.path.exists(os.path.join(item_path, "index.html")):
                    applet_dirs.append(item)
        
        # Generate cards HTML
        cards_html = "\n        <!-- Cards for applets -->\n"
        for applet_dir in sorted(applet_dirs):
            applet_path = os.path.join(public_repo_path, applet_dir)
            cards_html += generate_card_html(applet_dir, applet_path)
        
        # Replace cards container content
        new_index_content = re.sub(
            r'<div\s+class="cards-container">.*?</div>\s*<!--\s*end\s+cards\s*-->',
            f'<div class="cards-container">{cards_html}</div><!-- end cards -->',
            index_content, 
            flags=re.DOTALL
        )
        
        # Update last modified date
        today = datetime.now().strftime("%Y-%m-%d")
        new_index_content = re.sub(
            r'<p\s+class="last-updated">.*?</p>',
            f'<p class="last-updated">Last updated: {today}</p>',
            new_index_content
        )
        
        # Write updated index.html
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(new_index_content)
            
        print(f"Successfully updated index.html with {len(applet_dirs)} applets")
        
    except Exception as e:
        print(f"Error updating index.html: {e}")
        sys.exit(1)

def create_new_index_html(index_path):
    """Create a new index.html file from scratch."""
    public_repo_path = os.path.dirname(index_path)
    
    # Get all applet directories
    applet_dirs = []
    for item in os.listdir(public_repo_path):
        item_path = os.path.join(public_repo_path, item)
        if os.path.isdir(item_path) and item != "js" and not item.startswith('.'):
            # Check if it has an index.html file
            if os.path.exists(os.path.join(item_path, "index.html")):
                applet_dirs.append(item)
    
    # Generate cards HTML
    cards_html = "\n        <!-- Cards for applets -->\n"
    for applet_dir in sorted(applet_dirs):
        applet_path = os.path.join(public_repo_path, applet_dir)
        cards_html += generate_card_html(applet_dir, applet_path)
    
    # Current date for last updated
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Create basic index.html
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interactive Math Applets</title>
    <style>
        body, html {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        header {{
            background-color: #4a86e8;
            color: white;
            padding: 20px 0;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            margin: 0;
            font-size: 2rem;
        }}
        .cards-container {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            display: flex;
            flex-direction: column;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        }}
        .card-content {{
            padding: 20px;
            flex: 1;
        }}
        .card-title {{
            margin-top: 0;
            color: #4a86e8;
            font-size: 1.5rem;
        }}
        .card-description {{
            color: #666;
            line-height: 1.5;
        }}
        .card-button {{
            display: block;
            background-color: #4a86e8;
            color: white;
            text-align: center;
            padding: 12px;
            text-decoration: none;
            font-weight: bold;
            transition: background-color 0.3s;
        }}
        .card-button:hover {{
            background-color: #3a76d8;
        }}
        footer {{
            margin-top: 40px;
            text-align: center;
            padding: 20px;
            color: #777;
            font-size: 0.9rem;
        }}
        @media (max-width: 768px) {{
            .cards-container {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>Interactive Math Applets</h1>
    </header>
    
    <div class="container">
        <p>Welcome to our collection of interactive mathematics applets. These visualizations are designed to help students understand mathematical concepts through interactive learning.</p>
        
        <div class="cards-container">{cards_html}</div><!-- end cards -->
        
        <footer>
            <p class="last-updated">Last updated: {today}</p>
            <p>© 2025 Interactive Math Applets</p>
        </footer>
    </div>
</body>
</html>
"""
    
    # Write the new index.html
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Created new index.html with {len(applet_dirs)} applets")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_index.py <public_repo_path>")
        sys.exit(1)
    
    public_repo_path = sys.argv[1]
    update_index_html(public_repo_path)
