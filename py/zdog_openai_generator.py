#!/usr/bin/env python3
"""
Zdog OpenAI Generator for Applets
---------------------------------
Generates Zdog 3D visualization configurations using OpenAI API with
robust error handling and fallback mechanisms.

This script:
1. Takes CSV content as input
2. Uses OpenAI to analyze the problem and extract parameters
3. Generates Zdog scene configurations based on the analysis
4. Applies validation and error correction
5. Returns the configurations for embedding in the HTML applet
"""

import os
import csv
import json
import re
import sys
from openai import OpenAI
import jsonschema
from pathlib import Path

# Initialize OpenAI client
client = OpenAI(api_key="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")

# Enable more verbose debugging
DEBUG = True

# Import base Zdog generator for fallback functionality
from .zdog_generator import generate_zdog_config, get_cubes_to_larger_cube_config

# Schema for validating Zdog configurations
ZDOG_SCENE_SCHEMA = {
    "type": "object",
    "required": ["shapes"],
    "properties": {
        "shapes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["type"],
                "properties": {
                    "type": {"type": "string"},
                    "id": {"type": "string"},
                    "options": {"type": "object"},
                    "children": {"type": "array"}
                }
            }
        }
    }
}

def extract_spans_with_openai(question_text, api_key=None):
    """Extract given and to-find spans from the question text using OpenAI."""
    # Update client if api_key is provided
    openai_client = OpenAI(api_key=api_key) if api_key else client
    
    try:
        if DEBUG:
            print(f"Calling OpenAI API to extract spans from question text...")
            
        system_prompt = """You are a mathematical problem analyzer specialized in identifying the 'given' information and 'to find' goals in word problems.
Your task is to extract these elements from the question text. The given information includes all numeric values, measurements, and stated facts.
The 'to find' information includes the specific question being asked or what needs to be calculated.

Output ONLY valid JSON with the following schema:
{
  "given": [
    "string containing a specific given fact or value",
    "another given item"
  ],
  "tofind": [
    "specific item or quantity that needs to be found",
    "another item to find (if applicable)"
  ]
}

Important:
- Extract COMPLETE phrases, not just numbers or fragments
- Include units with measurements
- Separate distinct given facts into separate list items
- If multiple quantities need to be found, list them separately
"""
        
        user_prompt = f"""Analyze this mathematical problem and extract the given information and what needs to be found:
{question_text}

Return ONLY a JSON object with 'given' and 'tofind' arrays."""
        
        # Call OpenAI API with updated client
        response = openai_client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_completion_tokens=500
        )
        
        # Extract and parse JSON response
        json_response = response.choices[0].message.content.strip()
        
        if DEBUG:
            print("OpenAI API response for spans extraction: " + str(json_response[:300]) + "...")
            
        # Handle case where response might include markdown code block
        if "```json" in json_response:
            json_response = re.search(r'```json(.*?)```', json_response, re.DOTALL).group(1).strip()
        elif "```" in json_response:
            json_response = re.search(r'```(.*?)```', json_response, re.DOTALL).group(1).strip()
        
        # Parse JSON
        spans = json.loads(json_response)
        print(f"Successfully extracted spans: {spans}")
        
        # Ensure we have the expected structure
        if "given" not in spans or "tofind" not in spans:
            print("Warning: OpenAI response missing required fields. Using fallback.")
            return {"given": [], "tofind": []}
        
        return spans
    
    except Exception as e:
        print(f"Error extracting spans with OpenAI: {e}")
        return {"given": [], "tofind": []}

def extract_visualization_text(csv_content, api_key=None):
    """Extract text content needed for visualizations from CSV content."""
    # Map step types to their relevant content
    visualization_text = {
        'comprehend': {
            'question': csv_content.get('question_text', ''),
            'given': [],
            'tofind': []
        },
        'compute': {
            'steps': [csv_content.get(f'compute_step_{i}', '') for i in range(1, 10) if f'compute_step_{i}' in csv_content]
        },
        'connect': {
            'questions': []
        },
        'check': {
            'final_answer': ''  # Extract from compute steps if available
        }
    }
    
    # Check if given and tofind are explicitly provided in CSV
    csv_given = [csv_content.get(f'given_{i}', '') for i in range(1, 10) if f'given_{i}' in csv_content and csv_content.get(f'given_{i}', '')]
    csv_tofind = [csv_content.get(f'tofind_{i}', '') for i in range(1, 10) if f'tofind_{i}' in csv_content and csv_content.get(f'tofind_{i}', '')]
    
    # If explicitly provided in CSV, use those values
    if csv_given:
        visualization_text['comprehend']['given'] = csv_given
    if csv_tofind:
        visualization_text['comprehend']['tofind'] = csv_tofind
    
    # If not provided in CSV, extract from question text using OpenAI
    question_text = csv_content.get('question_text', '')
    if question_text and (not csv_given or not csv_tofind):
        try:
            spans = extract_spans_with_openai(question_text, api_key)
            
            # Only use extracted spans if CSV didn't provide them
            if not csv_given:
                visualization_text['comprehend']['given'] = spans.get('given', [])
            if not csv_tofind:
                visualization_text['comprehend']['tofind'] = spans.get('tofind', [])
        except Exception as e:
            print(f"Error extracting spans from question text: {e}")
            # Leave as empty lists if extraction fails
    
    # Extract connect questions
    i = 1
    while True:
        question_key = f'connect_question_{i}'
        if question_key not in csv_content:
            break
            
        question = {
            'question': csv_content.get(question_key, ''),
            'correct': csv_content.get(f'connect_option_correct_{i}_1', ''),
            'wrong': [
                csv_content.get(f'connect_option_wrong_{i}_{j}', '') 
                for j in range(1, 5) 
                if f'connect_option_wrong_{i}_{j}' in csv_content
            ]
        }
        visualization_text['connect']['questions'].append(question)
        i += 1
    
    # Try to extract final answer from compute steps
    compute_steps = visualization_text['compute']['steps']
    if compute_steps:
        # Usually the last step contains the answer
        visualization_text['check']['final_answer'] = compute_steps[-1]
    
    # Also extract any existing visualization_type and visualization_params
    if 'visualization_type' in csv_content:
        visualization_text['visualization_type'] = csv_content['visualization_type']
    
    try:
        if 'visualization_params' in csv_content:
            visualization_text['visualization_params'] = json.loads(csv_content['visualization_params'])
    except json.JSONDecodeError:
        print("Warning: visualization_params in CSV is not valid JSON")
    
    return visualization_text

def extract_parameters_with_openai(problem_text, api_key=None):
    """Extract visualization parameters from problem text using OpenAI."""
    # Update client if api_key is provided
    openai_client = OpenAI(api_key=api_key) if api_key else client
    
    try:
        if DEBUG:
            print(f"Calling OpenAI API to extract parameters from: {problem_text[:100]}...")
            
        system_prompt = """You are a mathematical problem analyzer specialized in extracting numerical parameters and visualization types from problem text.
Your task is to extract all numeric values, counts, sizes, and to identify what type of visualization would be most appropriate.
Output ONLY valid JSON with the following schema:
{
  "visualization_type": "string (e.g., cubes_to_larger_cube, cylinder_volume, etc.)",
  "parameters": {
    "count": integer or null,
    "size": number or null,
    "colors": [string] or null,
    "other_relevant_params": any
  }
}
"""
        
        user_prompt = f"""Analyze this mathematical problem and extract parameters for visualization:
{problem_text}

Return ONLY a JSON object with visualization_type and parameters."""
        
        # Call OpenAI API with updated client
        response = openai_client.chat.completions.create(
            model="gpt-4o-2024-08-06",  # Model with larger context window
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # Low temperature for more deterministic output
            max_completion_tokens=500
        )
        
        # Extract and parse JSON response with updated response structure
        json_response = response.choices[0].message.content.strip()
        
        if DEBUG:
            print(f"OpenAI API response: {json_response[:300]}...")
            
        # Handle case where response might include markdown code block
        if "```json" in json_response:
            json_response = re.search(r'```json(.*?)```', json_response, re.DOTALL).group(1).strip()
        elif "```" in json_response:
            json_response = re.search(r'```(.*?)```', json_response, re.DOTALL).group(1).strip()
        
        # Parse JSON
        params = json.loads(json_response)
        print(f"Successfully extracted parameters: {params}")
        
        # Validate structure
        if "visualization_type" not in params or "parameters" not in params:
            print("Warning: OpenAI response missing required fields. Using fallback.")
            return extract_parameters_manually(problem_text)
        
        return params
    
    except Exception as e:
        print(f"Error extracting parameters with OpenAI: {e}")
        print("Using fallback parameter extraction.")
        return extract_parameters_manually(problem_text)

def extract_parameters_manually(problem_text):
    """Extract visualization parameters manually as fallback."""
    # Default parameters
    params = {
        "visualization_type": "default",
        "parameters": {
            "count": None,
            "size": None,
            "colors": ["#f47983"]
        }
    }
    
    # Look for cube patterns
    cube_pattern = re.search(r'(\d+)\s*(?:metal|wooden|)?\s*cubes?\s*(?:with|of)?\s*(?:sides?|edge|length)\s*(?:of|=|:)?\s*(\d+)', problem_text, re.IGNORECASE)
    if cube_pattern:
        params["visualization_type"] = "cubes_to_larger_cube"
        params["parameters"]["count"] = int(cube_pattern.group(1))
        params["parameters"]["size"] = int(cube_pattern.group(2))
    
    # Look for cylinder patterns
    cylinder_pattern = re.search(r'cylinder\s*(?:with|of)?\s*(?:radius|r)\s*(?:of|=|:)?\s*(\d+)', problem_text, re.IGNORECASE)
    if cylinder_pattern:
        params["visualization_type"] = "cylinder_volume"
        params["parameters"]["size"] = int(cylinder_pattern.group(1))
    
    # If no specific pattern found but cubes mentioned, default to cube visualization
    if params["visualization_type"] == "default" and "cube" in problem_text.lower():
        params["visualization_type"] = "cubes_to_larger_cube"
        params["parameters"]["count"] = 5  # Reasonable default
        params["parameters"]["size"] = 5   # Reasonable default
    
    print(f"Manually extracted parameters: {params}")
    return params

def select_visualization_type(parameters, problem_text=None):
    """Select the appropriate visualization type based on parameters and context."""
    # Use provided type if it exists
    viz_type = parameters.get("visualization_type", "default")
    
    # If not explicitly provided, try to infer a better type from the problem text
    if viz_type == "default" and problem_text:
        # Extract problem characteristics to determine appropriate visualization
        if problem_text:
            # Check for different geometric and problem patterns
            if any(keyword in problem_text.lower() for keyword in ["box", "rectangular prism", "cuboid"]):
                if any(keyword in problem_text.lower() for keyword in ["height", "find the height"]):
                    return "box_height"
                elif any(keyword in problem_text.lower() for keyword in ["volume", "capacity"]):
                    return "box_volume"
                else:
                    return "rectangular_prism"
            
            elif any(keyword in problem_text.lower() for keyword in ["cylinder", "tube", "pipe"]):
                return "cylinder_volume"
            
            elif any(keyword in problem_text.lower() for keyword in ["cone", "pyramid"]):
                return "cone_volume"
            
            elif any(keyword in problem_text.lower() for keyword in ["sphere", "ball"]):
                return "sphere_volume"
            
            elif any(keyword in problem_text.lower() for keyword in ["pool", "tank", "container", "aquarium"]):
                return "container_volume"
            
            elif any(keyword in problem_text.lower() for keyword in ["cubes", "blocks", "stack"]):
                if "larger cube" in problem_text.lower():
                    return "cubes_to_larger_cube"
                else:
                    return "stacked_cubes"
    
    # Map to actual implementation types
    type_map = {
        "cubes_to_larger_cube": "cubes_to_larger_cube",
        "cube_transformation": "cubes_to_larger_cube",
        "cylinder_volume": "cylinder_volume",
        "box_height": "box_height",
        "box_volume": "box_volume",
        "rectangular_prism": "rectangular_prism",
        "cone_volume": "cone_volume",
        "sphere_volume": "sphere_volume",
        "container_volume": "container_volume",
        "stacked_cubes": "stacked_cubes",
        "default": "general_3d_scene"  # More neutral default
    }
    
    return type_map.get(viz_type, "general_3d_scene")

def generate_zdog_scenes_with_openai(visualization_text, api_key=None):
    """Generate unique Zdog scenes using OpenAI directly for each problem."""
    try:
        # Try to use existing parameters if available, or extract from text
        if 'visualization_params' in visualization_text and 'visualization_type' in visualization_text:
            visualization_params = {
                "visualization_type": visualization_text["visualization_type"],
                "parameters": visualization_text["visualization_params"]
            }
            if DEBUG:
                print(f"Using existing parameters: {visualization_params}")
        else:
            # Extract parameters from the question text and given information
            question_text = visualization_text.get('comprehend', {}).get('question', '')
            given_text = ", ".join(visualization_text.get('comprehend', {}).get('given', []))
            full_text = f"{question_text} {given_text}"
            
            # Use OpenAI to extract parameters
            if DEBUG:
                print(f"Extracting parameters from text: {full_text[:100]}...")
            visualization_params = extract_parameters_with_openai(full_text, api_key)
        
        # Select visualization type with problem context
        visualization_type = select_visualization_type(visualization_params, full_text)
        if DEBUG:
            print(f"Selected visualization type: {visualization_type}")
        
        # Generate scenes directly with OpenAI without using templates
        print("Generating unique Zdog scenes with OpenAI...")
        try:
            # Pass all visualization text to create a completely unique scene
            zdog_config = generate_zdog_scenes_with_api(visualization_text, visualization_params, api_key)
            if DEBUG:
                print("Successfully generated unique scenes with OpenAI API!")
            return zdog_config
        except Exception as e:
            print(f"Error generating scenes with OpenAI: {e}")
            print("Falling back to template-based generation as last resort.")
            # Only fall back to template in case of complete failure
            update_visualization_text = visualization_text.copy()
            update_visualization_text["visualization_type"] = visualization_type
            update_visualization_text["visualization_params"] = visualization_params.get("parameters", {})
            return generate_zdog_config(update_visualization_text)
    except Exception as e:
        print(f"Error in OpenAI integration: {e}")
        print("Falling back to template-based generation.")
        
        # Fallback to template-based generation
        print("Using template-based Zdog scene generation.")
        update_visualization_text = visualization_text.copy()
        update_visualization_text["visualization_type"] = visualization_type if 'visualization_type' in locals() else "general_3d_scene"
        update_visualization_text["visualization_params"] = visualization_params.get("parameters", {}) if 'visualization_params' in locals() else {}
        
        return generate_zdog_config(update_visualization_text)

def enhance_template_with_openai(visualization_text, viz_params, template_config, api_key=None):
    """Enhance a template-based Zdog configuration using OpenAI."""
    # Update client if api_key is provided
    openai_client = OpenAI(api_key=api_key) if api_key else client
    
    if DEBUG:
        print("Preparing API call for Zdog scene enhancement...")
    
    # Extract relevant information
    question_text = visualization_text.get('comprehend', {}).get('question', '')
    given_text = ", ".join(visualization_text.get('comprehend', {}).get('given', []))
    compute_steps = visualization_text.get('compute', {}).get('steps', [])
    compute_text = "\n".join(compute_steps)
    
    # Create specific type guidance
    viz_type = viz_params.get("visualization_type", "cubes_to_larger_cube")
    count = viz_params.get("parameters", {}).get("count", 5)
    size = viz_params.get("parameters", {}).get("size", 5)
    
    # Convert template config to pretty JSON string
    template_json = json.dumps(template_config, indent=2)
    
    # Create prompt for OpenAI
    system_prompt = """You are a 3D graphics expert specializing in enhancing Zdog scene configurations.
Your task is to take an existing Zdog configuration and enhance it with additional details, 
while preserving its fundamental structure and mathematical correctness.

Output ONLY a valid JSON object for the enhanced Zdog scenes.
"""
    
    user_prompt = f"""Enhance this Zdog scene configuration for a mathematical problem visualization:

PROBLEM:
{question_text}

GIVEN:
{given_text}

SOLUTION STEPS:
{compute_text}

VISUALIZATION TYPE: {viz_type}
CUBES COUNT: {count}
CUBE SIZE: {size}

EXISTING CONFIGURATION:
{template_json}

ENHANCEMENT GUIDELINES:
1. Preserve the existing structure and mathematical correctness
2. Add more detailed text labels to explain each step
3. Improve the positioning of elements for better visibility
4. Add transition arrows or indicators between transformation steps
5. Add reference grid and axes for better orientation
6. Ensure all cubes have both solid fill AND wireframe overlay
7. Keep original cube counts and dimensions
8. Do not add, remove or change the number of scenes

Return ONLY the enhanced valid JSON configuration with no explanation.
"""
    
    try:
        # Call OpenAI API with updated client
        print("Calling OpenAI API to enhance Zdog scenes...")
        response = openai_client.chat.completions.create(
            model="gpt-4o-2024-08-06",  # Model with larger context window
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_completion_tokens=4000
        )
        
        # Extract and parse JSON response with updated response structure
        json_response = response.choices[0].message.content.strip()
        
        if DEBUG:
            print(f"Received response of length: {len(json_response)} characters")
            
        # Handle markdown code block if present
        if "```json" in json_response:
            json_response = re.search(r'```json(.*?)```', json_response, re.DOTALL).group(1).strip()
        elif "```" in json_response:
            json_response = re.search(r'```(.*?)```', json_response, re.DOTALL).group(1).strip()
        
        # Parse JSON
        try:
            enhanced_config = json.loads(json_response)
            
            # Validate structure
            if "global" not in enhanced_config or "scenes" not in enhanced_config:
                print("Warning: Enhanced configuration missing global or scenes. Using template.")
                return template_config
            
            # Check scene count consistency
            if len(enhanced_config["scenes"]) != len(template_config["scenes"]):
                print("Warning: Scene count mismatch. Using template.")
                return template_config
            
            print("Successfully enhanced Zdog configuration")
            return enhanced_config
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing enhanced configuration: {e}")
            return template_config
    
    except Exception as e:
        print(f"Error calling OpenAI API for enhancement: {e}")
        return template_config

def generate_zdog_scenes_with_api(visualization_text, viz_params, api_key=None):
    """Generate unique Zdog scenes using OpenAI API with extensive context from the problem."""
    # Update client if api_key is provided
    openai_client = OpenAI(api_key=api_key) if api_key else client
    
    if DEBUG:
        print("Preparing API call for Zdog scene generation...")
        
    # Create a comprehensive system prompt with explicit structure requirements - using a raw string to avoid f-string issues
    system_prompt = r"""You are a 3D graphics expert specializing in converting mathematical problems into Zdog scene configurations.
Your task is to create UNIQUE Zdog scenes that visualize mathematical concepts for educational purposes.
Each visualization should be customized specifically for the individual problem, NOT a generic template.

Output ONLY valid JSON for Zdog scenes with this schema:
{
  "global": {
    "dragRotate": false,
    "zoom": 1.2,
    "backgroundColor": "#f0f0f0",
    "isometric": true
  },
  "scenes": {
    "comprehend_1": { "shapes": [] },
    "comprehend_2": { "shapes": [] },
    "comprehend_3": { "shapes": [] },
    "connect_1": { "shapes": [] },
    "compute_1": { "shapes": [] },
    ... (other scenes)
  }
}

REQUIRED STRUCTURE FOR EACH CUBE:
- ALWAYS use a parent Group to contain each cube
- ALWAYS include both a solid filled cube AND a wireframe overlay for clear edges
- Example structure for a proper cube:

{
  "type": "Group",
  "id": "small_cube_group_1",
  "options": {
    "translate": {"x": 0, "y": 0, "z": 0}
  },
  "children": [
    {
      "type": "Box",
      "id": "small_cube_1",
      "options": {
        "width": 75,
        "height": 75,
        "depth": 75,
        "stroke": 0,
        "fill": true,
        "color": "#f47983"
      }
    },
    {
      "type": "Box",
      "id": "small_cube_wireframe_1",
      "options": {
        "width": 75,
        "height": 75,
        "depth": 75,
        "stroke": 2.5,
        "fill": false,
        "color": "#000000"
      }
    }
  ]
}

WARNING: Do not use Text type shapes, as Zdog does not support text. Instead, use Shape, Group, Box, Cylinder, Cone, or other supported shape types. 
Valid Zdog shapes types are: Anchor, Box, Cone, Cylinder, Ellipse, Group, Hemisphere, Polygon, Rect, RoundedRect, Shape.

IMPORTANT VISUAL REQUIREMENTS:
- Create a UNIQUE visualization that specifically matches the problem context
- DO NOT use generic templates - each problem deserves its own custom visualization
- Use Groups and nested structures for complex elements
- DO NOT include reference grid or axes - keep the visualization clean
- Add transition elements like arrows between scenes
- Use appropriate text labels in each scene
- Ensure cubes have BOTH solid fill AND wireframe overlay for clear edges
- Be creative with colors and layouts to make the visualization engaging and educational
- Configure the global settings with dragRotate: false, isometric: true
"""
    
    # Extract all available context from visualization_text with proper None handling
    question_text = visualization_text.get('comprehend', {}).get('question', '') or ''
    given_items = visualization_text.get('comprehend', {}).get('given', []) or []
    given_text = ", ".join(given_items) if given_items else ""
    tofind_items = visualization_text.get('comprehend', {}).get('tofind', []) or []
    tofind_text = ", ".join(tofind_items) if tofind_items else ""
    compute_steps = visualization_text.get('compute', {}).get('steps', []) or []
    compute_text = "\n".join(compute_steps) if compute_steps else ""
    connect_questions = visualization_text.get('connect', {}).get('questions', []) or []
    connect_text = ""
    
    # Format connect questions if available
    if connect_questions:
        connect_text = "Connect Questions:\n"
        for i, q in enumerate(connect_questions):
            question = q.get('question', '') or ''
            correct = q.get('correct', '') or ''
            connect_text += str(i+1) + ". " + question + "\n"
            connect_text += "   Correct: " + correct + "\n"
    
    # Extract final answer if available
    final_answer = visualization_text.get('check', {}).get('final_answer', '') or ''
    
    # Create specific type guidance based on visualization type
    viz_type = viz_params.get("visualization_type", "cubes_to_larger_cube")
    viz_specific_guidance = ""
    
    # Define specialized guidance based on the visualization type
    if viz_type == "cubes_to_larger_cube":
        count = viz_params.get("parameters", {}).get("count", 5)
        size = viz_params.get("parameters", {}).get("size", 5)
        cube_volume = count * (size**3)
        # Use string concatenation instead of f-string to avoid backslash issues
        viz_specific_guidance = """
Create scenes showing """ + str(count) + """ small cubes with """ + str(size) + """ cm sides being transformed into one larger cube.
- Make this visualization UNIQUE and specific to this problem - NOT generic
- Use Box elements with wireframe overlays for clear edges
- Position small cubes in a pattern that's easily counted
- Make cubes LARGE and PROMINENT in the view (at least 20-30 units in size)
- Scale all cubes appropriately - small cubes should have dimensions of at least """ + str(size * 15) + """ units
- Create a larger cube with appropriate dimensions scaled similarly
- Include a transition animation logic in compute_3 scene
- Show proper dimensions with text labels
- Compute the correct volume of the larger cube as """ + str(count) + """ x """ + str(size) + """^3 = """ + str(cube_volume) + """ cubic cm
- Use isometric projection (30 degrees angles) for proper 3D
"""
    elif viz_type == "box_height":
        # Use regular string instead of f-string to avoid backslash issues
        viz_specific_guidance = """
Create scenes showing a rectangular box/prism with focus on finding its height.
- Make this visualization UNIQUE and specific to this problem - NOT generic
- Show the box with clear dimensions for length and width
- Use visual indicators to show that height is the unknown dimension
- Create progressive scenes that demonstrate the formula and calculation
- Use Box elements with wireframe overlays for clear edges
- Include appropriate formula visualization: Height = Volume divided by (Length x Width)
- Show the calculation process visually in the compute steps
- Use clear color coding to distinguish different dimensions
- Include a transition showing the height being calculated/revealed
- Use isometric projection for proper 3D visualization
"""
    elif viz_type == "cylinder_volume":
        # Use regular string instead of f-string to avoid backslash issues
        viz_specific_guidance = """
Create scenes showing a cylinder with focus on its volume calculation.
- Make this visualization UNIQUE and specific to this problem - NOT generic
- Show the cylinder with clear radius and height measurements
- Use Cylinder elements with wireframe overlays
- Include appropriate volume formula visualization: V = πr²h
- Create progressive scenes that demonstrate the formula and calculation
- Use clear color coding for different dimensions
- Show cross-section view in one of the scenes if helpful
- Include transition effects between different steps of calculation
- Use appropriate scale to make all elements clearly visible
"""
    elif viz_type == "rectangular_prism" or viz_type == "box_volume":
        # Use regular string instead of f-string to avoid backslash issues
        viz_specific_guidance = """
Create scenes showing a rectangular prism/box with focus on volume calculation.
- Make this visualization UNIQUE and specific to this problem - NOT generic
- Show the box with clear dimensions for length, width, and height
- Use Box elements with wireframe overlays for clear edges
- Include appropriate volume formula visualization: V = length x width x height
- Create progressive scenes that demonstrate the formula and calculation
- Use clear color coding to distinguish different dimensions
- Include layer-by-layer building or decomposition in one of the scenes
- Use isometric projection for proper 3D visualization
"""
    else:
        # Generic guidance for other visualization types - using concatenation instead of f-string
        viz_specific_guidance = """
Create scenes specific to the \"""" + viz_type + """\" visualization type.
- Make this visualization UNIQUE and specific to this problem - NOT generic
- Customize the visualization to perfectly match the problem context
- Create progressive scenes that demonstrate the concept clearly
- Use appropriate 3D elements with both fill and wireframe overlays
- Include clear labeling and dimensional indicators
- Use appropriate formulas and show calculation progression
- Incorporate transition effects between different states or steps
- Use color coding to distinguish different elements or dimensions
- Ensure all elements are appropriately sized and positioned for clarity
"""
    
    # Prepare user prompt with comprehensive context from the problem
    # Create given and to-find items strings safely
    given_items_str = "\n".join([f"- {item}" for item in given_items])
    tofind_items_str = "\n".join([f"- {item}" for item in tofind_items])
    solution_steps_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(compute_steps)])
    params_str = json.dumps(viz_params.get("parameters", {}), indent=2)
    
    # Create user prompt using regular string concatenation to avoid f-string with backslashes
    user_prompt = f"""Create a completely UNIQUE and CUSTOM Zdog 3D scene configuration to visualize this specific mathematical problem:

COMPLETE PROBLEM CONTEXT:
Question: {question_text}

Given Items:
{given_items_str}

To Find Items:
{tofind_items_str}

Solution Steps:
{solution_steps_str}

{connect_text}

Final Answer: {final_answer}

VISUALIZATION TYPE: {viz_type}

PARAMETERS:
{params_str}

{viz_specific_guidance}

UNIQUENESS REQUIREMENTS:
1. Create a completely CUSTOM visualization for this specific problem
2. DO NOT use a generic template approach - this should be tailored to this exact problem
3. The visual elements should directly relate to the specific numerical values and context of THIS problem
4. Be creative with layout, colors, and visual metaphors that reinforce the mathematical concepts

IMPLEMENTATION GUIDANCE:
- Implement all scenes: comprehend (1-3), connect_1, compute (1-4), and check (1, 3, 5)
- Each scene should build upon the previous one to tell a coherent visual story
- Ensure proper object grouping with both fill and wireframe elements
- For 3D primitives like boxes, cylinders, etc., always include the wireframe overlay
- Position elements with appropriate spacing for clarity
- Use colors that have good contrast and help distinguish different elements

Return ONLY a valid JSON object with global settings and scenes.
"""
    
    if DEBUG:
        print(f"User prompt length: {len(user_prompt)} characters")
    
    try:
        # Call OpenAI API with updated client
        print("Calling OpenAI API to generate Zdog scenes...")
        response = openai_client.chat.completions.create(
            model="gpt-4o-2024-08-06",  # Model with larger context window
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_completion_tokens=4000
        )
        
        # Extract and parse JSON response with updated response structure
        json_response = response.choices[0].message.content.strip()
        
        if DEBUG:
            print(f"Received response of length: {len(json_response)} characters")
            print(f"First 100 characters: {json_response[:100]}...")
            
        # Handle markdown code block if present
        if "```json" in json_response:
            json_response = re.search(r'```json(.*?)```', json_response, re.DOTALL).group(1).strip()
        elif "```" in json_response:
            json_response = re.search(r'```(.*?)```', json_response, re.DOTALL).group(1).strip()
        
        try:
            # Parse JSON
            print("Parsing and validating JSON response...")
            config = json.loads(json_response)
            
            # Validate the structure
            if "global" not in config or "scenes" not in config:
                raise ValueError("Missing global or scenes in configuration")
            
            # Validate each scene against schema
            for scene_key, scene in config["scenes"].items():
                jsonschema.validate(instance=scene, schema=ZDOG_SCENE_SCHEMA)
                
                # Additional validation for cube sizes
                for shape in scene.get("shapes", []):
                    # Check if this is a Box shape (cube)
                    if shape.get("type") == "Box" and "options" in shape:
                        options = shape.get("options", {})
                        # Make sure cubes are sufficiently large (at least 50 units)
                        if "width" in options and options["width"] < 50:
                            print(f"Warning: Cube in {scene_key} is too small ({options['width']}), scaling up")
                            options["width"] = max(75, options["width"] * 1.5)
                            options["height"] = max(75, options.get("height", options["width"]))
                            options["depth"] = max(75, options.get("depth", options["width"]))
                    
                    # Check children for Box shapes too
                    for child in shape.get("children", []):
                        if child.get("type") == "Box" and "options" in child:
                            child_options = child.get("options", {})
                            if "width" in child_options and child_options["width"] < 50:
                                print(f"Warning: Child cube in {scene_key} is too small ({child_options['width']}), scaling up")
                                child_options["width"] = max(75, child_options["width"] * 1.5)
                                child_options["height"] = max(75, child_options.get("height", child_options["width"]))
                                child_options["depth"] = max(75, child_options.get("depth", child_options["width"]))
            
            print(f"Successfully generated and validated {len(config['scenes'])} scenes")
            return config
        
        except (json.JSONDecodeError, jsonschema.exceptions.ValidationError) as e:
            print(f"Error validating OpenAI response: {e}")
            if DEBUG:
                error_snippet = json_response[:200] + "..." if len(json_response) > 200 else json_response
                print(f"Response snippet that caused the error: {error_snippet}")
                
            # Fall back to template-based generation
            update_visualization_text = visualization_text.copy()
            update_visualization_text["visualization_type"] = viz_type
            update_visualization_text["visualization_params"] = viz_params.get("parameters", {})
            return generate_zdog_config(update_visualization_text)
    
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        # Fall back to template-based generation
        update_visualization_text = visualization_text.copy()
        update_visualization_text["visualization_type"] = viz_type
        update_visualization_text["visualization_params"] = viz_params.get("parameters", {})
        return generate_zdog_config(update_visualization_text)

def generate_zdog_scenes_for_html(csv_file, api_key=None):
    """
    Generate Zdog scene config from CSV content using OpenAI with fallbacks.
    
    Args:
        csv_file: Path to CSV file
        api_key: OpenAI API key (optional)
        
    Returns:
        JSON string with Zdog configuration
    """
    try:
        # Read CSV content
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            csv_content = {}
            for row in reader:
                if len(row) >= 2:
                    csv_content[row[0]] = row[1]
        
        # Extract text for visualizations
        visualization_text = extract_visualization_text(csv_content)
        
        # Generate Zdog configuration with OpenAI and fallbacks
        config = generate_zdog_scenes_with_openai(visualization_text, api_key)
        
        # Convert to JSON string
        return json.dumps(config, indent=2)
    
    except Exception as e:
        print(f"Error in generate_zdog_scenes_for_html: {e}")
        # Final fallback - use base generator without OpenAI
        return generate_zdog_config_from_csv(csv_file)

def generate_zdog_config_from_csv(csv_file):
    """Fallback function that calls the base generator."""
    # Import here to avoid circular imports
    from zdog_generator import generate_zdog_scenes_for_html as base_generate
    print("Using base Zdog generator as final fallback.")
    return base_generate(csv_file)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Zdog configuration from CSV content using OpenAI')
    parser.add_argument('csv_file', help='Path to the CSV file')
    parser.add_argument('--api-key', help='OpenAI API key (or set OPENAI_API_KEY env variable)')
    parser.add_argument('--output-file', help='Output JSON file path')
    
    args = parser.parse_args()
    
    # Use the provided API key from args, environment, or the hardcoded one
    api_key = args.api_key
    
    # Generate Zdog configuration
    config_json = generate_zdog_scenes_for_html(args.csv_file, api_key)
    
    # Save to file or print to stdout
    if args.output_file:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(config_json)
        print(f"Zdog configuration saved to {args.output_file}")
    else:
        print(config_json)
