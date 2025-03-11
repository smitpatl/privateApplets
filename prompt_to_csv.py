#!/usr/bin/env python3
"""
Prompt to CSV Converter
------------------------
Converts a text prompt file into a structured CSV file for applet generation.
Uses OpenAI to assist in extracting and generating appropriate content.
"""

import os
import sys
import csv
import re
import json
import argparse
from pathlib import Path

# Try to import OpenAI
try:
    from openai import OpenAI
except ImportError:
    print("OpenAI package not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])
    from openai import OpenAI

# Constants
PROMPT_PATH = "applet_prompt.txt"
CSV_PATH = "applet_data.csv"

def read_prompt_file(file_path):
    """Read the prompt file and return its content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading prompt file: {e}")
        sys.exit(1)

def parse_prompt_sections(content):
    """Parse the content into sections."""
    sections = {
        'grade_level': '',
        'concept': '',
        'objectives': [],
        'question': '',
        'hints': [],
        'connect_questions': [],
        'notes': ''
    }
    
    # Extract grade level
    grade_match = re.search(r'GRADE LEVEL:\s*(.*?)(?:\n|$)', content)
    if grade_match:
        sections['grade_level'] = grade_match.group(1).strip()
    
    # Extract concept
    concept_match = re.search(r'CONCEPT:\s*(.*?)(?:\n|$)', content)
    if concept_match:
        sections['concept'] = concept_match.group(1).strip()
    
    # Extract learning objectives
    objectives_match = re.search(r'LEARNING OBJECTIVES:\s*(.*?)(?:\n\n|\Z)', content, re.DOTALL)
    if objectives_match:
        objectives_text = objectives_match.group(1)
        sections['objectives'] = [obj.strip()[2:].strip() for obj in objectives_text.split('\n-') if obj.strip()]
        # Fix first item if it doesn't have a dash
        if sections['objectives'] and not objectives_text.strip().startswith('-'):
            sections['objectives'][0] = objectives_text.split('\n')[0].strip()
    
    # Extract question/prompt
    question_match = re.search(r'QUESTION/PROMPT:\s*(.*?)(?:\n\n|\Z)', content, re.DOTALL)
    if question_match:
        sections['question'] = question_match.group(1).strip()
    
    # Extract hints
    hints_match = re.search(r'HINTS FOR SOLUTION:\s*(.*?)(?:\n\n|\Z)', content, re.DOTALL)
    if hints_match:
        hints_text = hints_match.group(1)
        sections['hints'] = [hint.strip()[2:].strip() for hint in hints_text.split('\n-') if hint.strip()]
        # Fix first item if it doesn't have a dash
        if sections['hints'] and not hints_text.strip().startswith('-'):
            sections['hints'][0] = hints_text.split('\n')[0].strip()
    
    # Extract connect questions
    connect_section_match = re.search(r'CONNECT QUESTIONS:\s*(.*?)(?:\n\n|\Z)', content, re.DOTALL)
    if connect_section_match:
        connect_text = connect_section_match.group(1).strip()
        question_blocks = re.split(r'\n\s*\d+\.\s+', connect_text)
        # Skip the first empty block if it exists
        if question_blocks and not question_blocks[0].strip():
            question_blocks = question_blocks[1:]
        else:
            # Extract the question number from the first block
            first_block = question_blocks[0]
            match = re.match(r'\s*(\d+\.\s+)(.*)', first_block)
            if match:
                question_blocks[0] = match.group(2)
        
        for block in question_blocks:
            if not block.strip():
                continue
                
            lines = block.split('\n')
            if not lines:
                continue
                
            question_text = lines[0].strip()
            options = []
            
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('CORRECT:'):
                    options.append({'text': line[8:].strip(), 'correct': True})
                elif line.startswith('WRONG:'):
                    options.append({'text': line[6:].strip(), 'correct': False})
            
            if question_text and options:
                sections['connect_questions'].append({
                    'question': question_text,
                    'options': options
                })
    
    # Extract additional notes
    notes_match = re.search(r'ADDITIONAL NOTES:\s*(.*?)(?:\n\n|\Z)', content, re.DOTALL)
    if notes_match:
        sections['notes'] = notes_match.group(1).strip()
    
    return sections

def generate_connect_questions_with_openai(question, compute_steps, api_key=None):
    """Generate connect questions using OpenAI if none are provided."""
    # When running in GitHub Actions, the API key is set as an environment variable
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        
    if not api_key:
        print("Warning: No OPENAI_API_KEY found in environment variables. Using default connect questions.")
        return [
            {
                'question': "Which formula should you use to solve this problem?",
                'options': [
                    {'text': "The correct formula based on the problem context", 'correct': True},
                    {'text': "An incorrect formula that seems plausible", 'correct': False},
                    {'text': "A formula from a different mathematical concept", 'correct': False},
                    {'text': "No formula is needed for this problem", 'correct': False}
                ]
            },
            {
                'question': "What is the first step in solving this problem?",
                'options': [
                    {'text': "The correct first step for this problem", 'correct': True},
                    {'text': "A step that should come later in the solution", 'correct': False},
                    {'text': "An unnecessary step that doesn't help solve the problem", 'correct': False},
                    {'text': "A step that would lead to an incorrect solution", 'correct': False}
                ]
            }
        ]
    
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
Create 2 multiple-choice connect questions for this 5th grade math problem:

PROBLEM:
{question}

SOLUTION:
{' '.join(compute_steps)}

Each connect question should test the student's conceptual understanding, not just calculation ability.
For each question, provide 1 correct answer and 3 wrong answers that are plausible but incorrect.

Format your response as valid JSON with this structure:
[
  {{
    "question": "Question text here?",
    "options": [
      {{"text": "Correct answer here", "correct": true}},
      {{"text": "Wrong answer 1", "correct": false}},
      {{"text": "Wrong answer 2", "correct": false}},
      {{"text": "Wrong answer 3", "correct": false}}
    ]
  }},
  // Second question with same structure
]

The questions should be specific to the mathematical concepts in this problem.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are a 5th grade math teacher creating conceptual multiple-choice questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Extract and parse JSON response
        json_text = response.choices[0].message.content.strip()
        
        # Handle case where response might include markdown code block
        if "```json" in json_text:
            json_text = re.search(r'```json(.*?)```', json_text, re.DOTALL).group(1).strip()
        elif "```" in json_text:
            json_text = re.search(r'```(.*?)```', json_text, re.DOTALL).group(1).strip()
        
        connect_questions = json.loads(json_text)
        
        # Ensure we have at least 2 connect questions
        if len(connect_questions) < 2:
            default_question = {
                'question': "What concept does this problem test?",
                'options': [
                    {'text': "The correct mathematical concept", 'correct': True},
                    {'text': "A related but incorrect concept", 'correct': False},
                    {'text': "An unrelated mathematical concept", 'correct': False},
                    {'text': "This problem doesn't test any specific concept", 'correct': False}
                ]
            }
            while len(connect_questions) < 2:
                connect_questions.append(default_question)
        
        return connect_questions[:2]  # Limit to 2 questions
        
    except Exception as e:
        print(f"Error generating connect questions with OpenAI: {e}")
        # Fallback to basic connect questions
        return [
            {
                'question': "Which formula should you use to solve this problem?",
                'options': [
                    {'text': "The correct formula based on the problem context", 'correct': True},
                    {'text': "An incorrect formula that seems plausible", 'correct': False},
                    {'text': "A formula from a different mathematical concept", 'correct': False},
                    {'text': "No formula is needed for this problem", 'correct': False}
                ]
            },
            {
                'question': "What is the first step in solving this problem?",
                'options': [
                    {'text': "The correct first step for this problem", 'correct': True},
                    {'text': "A step that should come later in the solution", 'correct': False},
                    {'text': "An unnecessary step that doesn't help solve the problem", 'correct': False},
                    {'text': "A step that would lead to an incorrect solution", 'correct': False}
                ]
            }
        ]

def generate_compute_steps_with_openai(question, hints, api_key=None):
    """Generate compute steps using OpenAI."""
    # When running in GitHub Actions, the API key is set as an environment variable
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        
    if not api_key:
        print("Warning: No OPENAI_API_KEY found in environment variables. Using default compute steps.")
        # Return some default steps based on hints
        steps = []
        steps.append("Step 1: Calculate the volume of the original shape")
        for i, hint in enumerate(hints):
            steps.append(f"Step {i+2}: {hint}")
        return steps
    
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
Generate detailed step-by-step solution steps for this 5th grade math problem:

PROBLEM:
{question}

SOLUTION HINTS:
{', '.join(hints) if hints else "Identify what's given, set up the appropriate equation, and solve step-by-step."}

Format your response as a numbered list of computation steps, starting from identifying what's given,
and proceeding through each calculation to the final answer. Include at least 6-8 detailed steps.
Each step should be clear enough for a 5th grader to understand.

Make sure to break down the solution into many small steps rather than combining multiple calculations into one step.
Return ONLY the numbered steps, no explanations or other text.

Example format:
Step 1: Identify what is given...
Step 2: Calculate...
etc.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are a 5th grade math teacher creating clear step-by-step solutions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Extract and process the steps
        steps_text = response.choices[0].message.content.strip()
        steps = []
        
        # Extract steps using regex
        step_pattern = re.compile(r'Step\s+\d+:.*?(?=Step\s+\d+:|$)', re.DOTALL)
        matches = step_pattern.findall(steps_text)
        
        if matches:
            # Clean up the steps
            steps = [re.sub(r'\n\s*', ' ', step.strip()) for step in matches]
        else:
            # Fallback: split by newlines and look for steps
            lines = steps_text.split('\n')
            for line in lines:
                line = line.strip()
                if re.match(r'Step\s+\d+:', line):
                    steps.append(line)
        
        return steps
        
    except Exception as e:
        print(f"Error generating compute steps with OpenAI: {e}")
        # Fallback to basic steps
        return [
            "Step 1: Calculate the volume of the original shape",
            "Step 2: Determine the equation for the new shape",
            "Step 3: Solve for the unknown dimension",
            "Step 4: Verify the solution"
        ]

def generate_check_steps_with_openai(question, compute_steps, api_key=None):
    """Generate check steps using OpenAI."""
    # When running in GitHub Actions, the API key is set as an environment variable
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        
    if not api_key:
        print("Warning: No OPENAI_API_KEY found in environment variables. Using default check steps.")
        return [
            "Check if the volume of the original shape equals the volume of the new shape",
            "Verify your calculations by substituting the values",
            "Consider if your answer makes sense in the context of the problem",
            "Calculate the surface area of both shapes to observe how it changes",
            "Try with different numbers to see if the pattern holds"
        ]
    
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
Generate 5 check/verification steps for this 5th grade math problem and solution:

PROBLEM:
{question}

SOLUTION:
{' '.join(compute_steps)}

I need 5 check steps that a student could use to verify their work or explore variations of this problem.
Each check step should be a complete sentence. These will be used for a slider in an interactive applet.

Example format:
1. Check if...
2. Try calculating...
3. Compare...
etc.

Return ONLY the 5 numbered check steps, no other text.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are a 5th grade math teacher creating verification steps for students."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=750
        )
        
        # Extract and process the steps
        check_text = response.choices[0].message.content.strip()
        check_steps = []
        
        # Extract numbered items
        number_pattern = re.compile(r'^\s*\d+\.\s+(.*?)$', re.MULTILINE)
        matches = number_pattern.findall(check_text)
        
        if matches:
            check_steps = [match.strip() for match in matches]
        else:
            # Fallback: split by newlines
            lines = check_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.isdigit():
                    check_steps.append(line)
        
        # Ensure we have exactly 5 check steps
        while len(check_steps) < 5:
            check_steps.append(f"Check your work for step {len(check_steps) + 1}")
        
        return check_steps[:5]  # Limit to 5 steps
        
    except Exception as e:
        print(f"Error generating check steps with OpenAI: {e}")
        # Fallback to basic check steps
        return [
            "Check if the volume of the original shape equals the volume of the new shape",
            "Verify your calculations by substituting the values",
            "Consider if your answer makes sense in the context of the problem",
            "Calculate the surface area of both shapes to observe how it changes",
            "Try with different numbers to see if the pattern holds"
        ]

def generate_title_with_openai(concept, question, api_key=None):
    """Generate a title for the applet using OpenAI."""
    # When running in GitHub Actions, the API key is set as an environment variable
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
        
    if not api_key:
        print("Warning: No OPENAI_API_KEY found in environment variables. Using default title.")
        # Extract key words from concept and question
        words = re.findall(r'\b\w+\b', concept + " " + question)
        important_words = [word for word in words if len(word) > 3 and word.lower() not in ('with', 'what', 'that', 'this', 'from', 'have', 'been')]
        if important_words:
            title_words = important_words[:3]
            return ' '.join(title_words).title() + " Challenge"
        return "Math Visualization Challenge"
    
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
Create a brief, engaging title for a 5th grade math applet about:

CONCEPT: {concept}

QUESTION: {question}

The title should be concise (3-5 words), catchy, and relevant to the mathematical concept.
Return ONLY the title, nothing else.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You create concise, engaging titles for educational content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=50
        )
        
        title = response.choices[0].message.content.strip()
        
        # Remove quotes if present
        title = title.strip('"\'')
        
        # Add "Challenge" if not present
        if "challenge" not in title.lower():
            title += " Challenge"
            
        return title
        
    except Exception as e:
        print(f"Error generating title with OpenAI: {e}")
        return "Volume Transformation Challenge"

def create_csv_content(sections, api_key=None):
    """Create the CSV content from the parsed sections."""
    print("Generating title...")
    # Generate a title
    title = generate_title_with_openai(sections['concept'], sections['question'], api_key)
    
    print("Generating compute steps...")
    # Generate compute steps
    compute_steps = generate_compute_steps_with_openai(sections['question'], sections['hints'], api_key)
    
    print("Generating check steps...")
    # Generate check steps
    check_steps = generate_check_steps_with_openai(sections['question'], compute_steps, api_key)
    
    # If no connect questions were provided, generate them
    if not sections['connect_questions'] or len(sections['connect_questions']) < 2:
        print("No connect questions provided. Generating them with OpenAI...")
        ai_connect_questions = generate_connect_questions_with_openai(sections['question'], compute_steps, api_key)
        # If we have some provided questions, add the AI-generated ones to fill the gaps
        if sections['connect_questions']:
            # Append AI questions until we have at least 2
            for q in ai_connect_questions:
                if len(sections['connect_questions']) < 2:
                    sections['connect_questions'].append(q)
                else:
                    break
        else:
            # Use all AI-generated questions
            sections['connect_questions'] = ai_connect_questions
    
    # Create CSV rows
    rows = [
        ["ZDOG APPLET CSV GENERATOR", ""],
        ["Complete the fields below to generate an applet.", ""],
        ["title", title],
        ["question_text", sections['question']]
    ]
    
    # Add any given items (will be auto-extracted by OpenAI if left blank)
    for i in range(1, 4):
        if i-1 < len(sections['hints']):
            rows.append([f"given_{i}", sections['hints'][i-1]])
        else:
            rows.append([f"given_{i}", ""])
    
    # Add tofind items (will be auto-extracted by OpenAI if left blank)
    for i in range(1, 4):
        if i-1 < len(sections['objectives']):
            rows.append([f"tofind_{i}", sections['objectives'][i-1]])
        else:
            rows.append([f"tofind_{i}", ""])
    
    # Add compute steps - ensure we have at least 6 steps
    for i in range(1, 10):
        if i-1 < len(compute_steps):
            rows.append([f"compute_step_{i}", compute_steps[i-1]])
        else:
            # For steps 1-6, add placeholders if needed
            if i <= 6:
                rows.append([f"compute_step_{i}", f"Step {i}: Perform the required calculation for this step"])
            else:
                rows.append([f"compute_step_{i}", ""])
    
    # Add check steps - ensure we have all 5 steps filled
    for i in range(1, 7):
        if i-1 < len(check_steps):
            rows.append([f"check_step_{i}", check_steps[i-1]])
        else:
            # Add placeholder for the 5 main steps
            if i <= 5:
                rows.append([f"check_step_{i}", f"Check step {i}: Verify your work by examining this aspect"])
            else:
                rows.append([f"check_step_{i}", ""])
    
    # Add connect questions - we should have at least 2 by this point
    for i in range(1, 3):  # Always add exactly 2 questions
        if i-1 < len(sections['connect_questions']):
            q = sections['connect_questions'][i-1]
            rows.append([f"connect_question_{i}", q['question']])
            
            # Add options
            correct_added = False
            wrong_count = 0
            
            for option in q['options']:
                if option['correct'] and not correct_added:
                    rows.append([f"connect_option_correct_{i}_1", option['text']])
                    correct_added = True
                elif not option['correct'] and wrong_count < 3:
                    wrong_count += 1
                    rows.append([f"connect_option_wrong_{i}_{wrong_count}", option['text']])
            
            # Add default correct option if none specified
            if not correct_added:
                rows.append([f"connect_option_correct_{i}_1", "The correct answer"])
            
            # Fill in remaining wrong options
            while wrong_count < 3:
                wrong_count += 1
                rows.append([f"connect_option_wrong_{i}_{wrong_count}", f"Incorrect option {wrong_count}"])
        else:
            # This should not happen since we now generate questions, but just in case
            rows.append([f"connect_question_{i}", f"Question {i}: What concept is being tested in this problem?"])
            rows.append([f"connect_option_correct_{i}_1", "The correct concept for this problem"])
            rows.append([f"connect_option_wrong_{i}_1", "An incorrect but related concept"])
            rows.append([f"connect_option_wrong_{i}_2", "A different mathematical concept"])
            rows.append([f"connect_option_wrong_{i}_3", "None of the above"])
    
    # Add visualization parameters (let OpenAI generate these)
    rows.append(["visualization_type", ""])
    rows.append(["visualization_params", ""])
    
    return rows

def write_csv_file(rows, file_path):
    """Write the rows to a CSV file."""
    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        print(f"Successfully wrote CSV file: {file_path}")
        return True
    except Exception as e:
        print(f"Error writing CSV file: {e}")
        return False

def main():
    """Main function to process the prompt file and generate the CSV."""
    print("Starting prompt to CSV conversion...")
    
    # Get the API key from environment variable - for GitHub Actions this will be automatically set
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY environment variable not set. This is required for GitHub Actions.")
    
    # Read the prompt file
    prompt_content = read_prompt_file(PROMPT_PATH)
    
    # Parse the content into sections
    print("Parsing prompt content...")
    sections = parse_prompt_sections(prompt_content)
    
    # Generate the CSV content
    print("Generating CSV content...")
    csv_rows = create_csv_content(sections, api_key)
    
    # Write the CSV file
    success = write_csv_file(csv_rows, CSV_PATH)
    
    if success:
        print("Conversion completed successfully.")
        print(f"The CSV file has been updated: {CSV_PATH}")
        print("You can now commit this file to trigger the applet generation, or make further edits if needed.")
        return 0
    else:
        print("Conversion failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
