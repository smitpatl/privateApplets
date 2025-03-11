#!/usr/bin/env python3
"""
Zdog Generator for Applets
-------------------------
Generates Zdog 3D visualization configurations from text content.

This script:
1. Takes CSV content as input
2. Generates JSON configuration for Zdog scenes based on the content
3. Returns the configurations for embedding in the HTML applet
"""

import os
import csv
import json
from pathlib import Path

def extract_visualization_text(csv_content):
    """Extract text content needed for visualizations from CSV content."""
    # Map step types to their relevant content
    visualization_text = {
        'comprehend': {
            'question': csv_content.get('question_text', ''),
            'given': [csv_content.get(f'given_{i}', '') for i in range(1, 10) if f'given_{i}' in csv_content],
            'tofind': [csv_content.get(f'tofind_{i}', '') for i in range(1, 10) if f'tofind_{i}' in csv_content]
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
    
    # Extract visualization type and parameters
    visualization_text['visualization_type'] = csv_content.get('visualization_type', 'default')
    
    # Try to parse visualization parameters if available
    try:
        if 'visualization_params' in csv_content:
            params = csv_content['visualization_params']
            visualization_text['visualization_params'] = json.loads(params)
        else:
            visualization_text['visualization_params'] = {}
    except:
        visualization_text['visualization_params'] = {}
    
    return visualization_text

def get_cubes_to_larger_cube_config(visualization_text):
    """Generate configuration for 'cubes to larger cube' visualization type."""
    params = visualization_text.get('visualization_params', {})
    
    # Default parameters if not specified
    small_cube_count = params.get('small_cube_count', 5)
    small_cube_size = params.get('small_cube_size', 5)
    small_cube_color = params.get('small_cube_color', '#f47983')
    
    # Calculate derived values
    large_cube_volume = small_cube_size**3 * small_cube_count
    large_cube_size = round(large_cube_volume**(1/3), 2)  # Cube root
    
    # Colors for different phases
    phase_colors = {
        'comprehend': '#f47983',  # Pink
        'connect': '#5b9bd5',     # Blue
        'compute': '#6aa84f',     # Green
        'check': '#ffd700'        # Gold
    }
    
    # Create scenes for each phase
    scenes = {}
    
    # COMPREHEND PHASE
    
    # Comprehend 1: Show the initial problem with small cubes
    scenes['comprehend_1'] = {
        "shapes": []
    }
    
    # Position small cubes in an organized pattern
    positions = []
    if small_cube_count == 1:
        positions = [(0, 0, 0)]
    elif small_cube_count <= 4:
        # 2x2 grid
        grid_size = 2
        for i in range(grid_size):
            for j in range(grid_size):
                if len(positions) < small_cube_count:
                    positions.append((
                        (i - (grid_size-1)/2) * small_cube_size * 1.2,
                        0,
                        (j - (grid_size-1)/2) * small_cube_size * 1.2
                    ))
    else:
        # Position in a pyramid-like structure
        layer_size = 3
        layers = 2
        cube_index = 0
        for layer in range(layers):
            for i in range(layer_size - layer):
                for j in range(layer_size - layer):
                    if cube_index < small_cube_count:
                        positions.append((
                            (i - (layer_size-1-layer)/2) * small_cube_size * 1.2,
                            -layer * small_cube_size * 1.2,
                            (j - (layer_size-1-layer)/2) * small_cube_size * 1.2
                        ))
                        cube_index += 1
    
    # Add remaining cubes if needed
    while len(positions) < small_cube_count:
        positions.append((
            (len(positions) % 3 - 1) * small_cube_size * 1.2,
            -((len(positions) // 3) + 1) * small_cube_size * 1.2,
            0
        ))
    
    # Add small cubes to the scene with distinct edges/wireframes
    for i, (x, y, z) in enumerate(positions):
        # Create a group for each cube to contain both the solid cube and its wireframe
        cube_group = {
            "type": "Group",
            "id": f"small_cube_group_{i+1}",
            "options": {
                "translate": {"x": x * 10, "y": y * 10, "z": z * 10}
            },
            "children": [
                # Solid filled cube
                {
                    "type": "Box",
                    "id": f"small_cube_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,  # Scale up for better visibility
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 0,  # No stroke for the filled part
                        "fill": True,
                        "color": small_cube_color
                    }
                },
                # Wireframe overlay for clear edges
                {
                    "type": "Box",
                    "id": f"small_cube_wireframe_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 1.5,  # Thicker stroke for visible edges
                        "fill": False,  # No fill, just edges
                        "color": "#000000"  # Black edges for contrast
                    }
                }
            ]
        }
        
        scenes['comprehend_1']['shapes'].append(cube_group)
    
    # Add text label for small cube size
    scenes['comprehend_1']['shapes'].append({
        "type": "Shape",
        "id": "size_label",
        "options": {
            "stroke": 0,
            "translate": {"x": -positions[0][0] * 10, "y": -positions[0][1] * 10 - small_cube_size * 10, "z": positions[0][2] * 10},
            "color": "transparent"
        },
        "children": [
            {
                "type": "Text",
                "id": "size_text",
                "options": {
                    "text": f"{small_cube_size} cm",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": -10, "z": 0},
                    "textAlign": "center"
                }
            }
        ]
    })
    
    # Comprehend 2: Highlight given information
    scenes['comprehend_2'] = {
        "shapes": []
    }
    
    # Copy the small cubes with highlighting and distinct edges
    for i, (x, y, z) in enumerate(positions):
        # Create a group for each cube to contain both the solid cube and its wireframe
        cube_group = {
            "type": "Group",
            "id": f"small_cube_group_{i+1}",
            "options": {
                "translate": {"x": x * 10, "y": y * 10, "z": z * 10}
            },
            "children": [
                # Solid filled cube
                {
                    "type": "Box",
                    "id": f"small_cube_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 0,
                        "fill": True,
                        "color": small_cube_color
                    }
                },
                # Wireframe overlay for clear edges (thicker for emphasis)
                {
                    "type": "Box",
                    "id": f"small_cube_wireframe_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 2.5,  # Even thicker stroke for emphasis
                        "fill": False,
                        "color": "#000000"
                    }
                }
            ]
        }
        
        scenes['comprehend_2']['shapes'].append(cube_group)
    
    # Add text labels with given information
    scenes['comprehend_2']['shapes'].append({
        "type": "Shape",
        "id": "given_label",
        "options": {
            "stroke": 0,
            "translate": {"x": 0, "y": -positions[0][1] * 10 - small_cube_size * 15, "z": 0},
            "color": "transparent"
        },
        "children": [
            {
                "type": "Text",
                "id": "given_text",
                "options": {
                    "text": f"{small_cube_count} cubes",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": -10, "z": 0},
                    "textAlign": "center"
                }
            },
            {
                "type": "Text",
                "id": "given_size",
                "options": {
                    "text": f"{small_cube_size} cm sides",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": 10, "z": 0},
                    "textAlign": "center"
                }
            }
        ]
    })
    
    # Comprehend 3: Show what to find (the larger cube)
    scenes['comprehend_3'] = {
        "shapes": []
    }
    
    # Add small cubes (faded) with distinct edges
    for i, (x, y, z) in enumerate(positions):
        cube_group = {
            "type": "Group",
            "id": f"small_cube_group_{i+1}",
            "options": {
                "translate": {"x": x * 10, "y": y * 10, "z": z * 10}
            },
            "children": [
                # Faded solid filled cube
                {
                    "type": "Box",
                    "id": f"small_cube_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 0,
                        "fill": True,
                        "color": small_cube_color,
                        "opacity": 0.4  # Faded to show transition
                    }
                },
                # Faded wireframe overlay
                {
                    "type": "Box",
                    "id": f"small_cube_wireframe_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 1.5,
                        "fill": False,
                        "color": "#000000",
                        "opacity": 0.6  # More visible than the fill
                    }
                }
            ]
        }
        
        scenes['comprehend_3']['shapes'].append(cube_group)
    
    # Add larger cube (semi-transparent) with distinct edges
    scenes['comprehend_3']['shapes'].append({
        "type": "Group",
        "id": "large_cube_group",
        "options": {
            "translate": {"x": 120, "y": 0, "z": 0}
        },
        "children": [
            # Semi-transparent solid filled cube
            {
                "type": "Box",
                "id": "large_cube",
                "options": {
                    "width": large_cube_size * 10,
                    "height": large_cube_size * 10,
                    "depth": large_cube_size * 10,
                    "stroke": 0,
                    "fill": True,
                    "color": small_cube_color,
                    "opacity": 0.6
                }
            },
            # Wireframe overlay for clear edges
            {
                "type": "Box",
                "id": "large_cube_wireframe",
                "options": {
                    "width": large_cube_size * 10,
                    "height": large_cube_size * 10,
                    "depth": large_cube_size * 10,
                    "stroke": 2.5,
                    "fill": False,
                    "color": "#000000",
                    "opacity": 0.8  # More visible than the fill
                }
            }
        ]
    })
    
    # Add question mark for the volume
    scenes['comprehend_3']['shapes'].append({
        "type": "Shape",
        "id": "volume_question",
        "options": {
            "stroke": 0,
            "translate": {"x": 120, "y": -large_cube_size * 7, "z": large_cube_size * 6},
            "color": "transparent"
        },
        "children": [
            {
                "type": "Text",
                "id": "volume_text",
                "options": {
                    "text": "Volume = ?",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": 0, "z": 0},
                    "textAlign": "center"
                }
            }
        ]
    })
    
    # CONNECT PHASE
    
    # Connect 1: Show volume formula relationship
    scenes['connect_1'] = {
        "shapes": []
    }
    
    # Add one small cube with formula and distinct edges
    scenes['connect_1']['shapes'].append({
        "type": "Group",
        "id": "formula_cube_group",
        "options": {
            "translate": {"x": -50, "y": 0, "z": 0}
        },
        "children": [
            # Solid filled cube
            {
                "type": "Box",
                "id": "formula_cube",
                "options": {
                    "width": small_cube_size * 10,
                    "height": small_cube_size * 10,
                    "depth": small_cube_size * 10,
                    "stroke": 0,
                    "fill": True,
                    "color": phase_colors['connect']
                }
            },
            # Wireframe overlay for clear edges
            {
                "type": "Box",
                "id": "formula_cube_wireframe",
                "options": {
                    "width": small_cube_size * 10,
                    "height": small_cube_size * 10,
                    "depth": small_cube_size * 10,
                    "stroke": 1.5,
                    "fill": False,
                    "color": "#000000"
                }
            }
        ]
    })
    
    # Add formula text
    scenes['connect_1']['shapes'].append({
        "type": "Shape",
        "id": "formula_label",
        "options": {
            "stroke": 0,
            "translate": {"x": 50, "y": 0, "z": 0},
            "color": "transparent"
        },
        "children": [
            {
                "type": "Text",
                "id": "formula_text",
                "options": {
                    "text": "Volume = s³",
                    "fontSize": 18,
                    "color": "#000000",
                    "translate": {"x": 0, "y": -15, "z": 0},
                    "textAlign": "center"
                }
            },
            {
                "type": "Text",
                "id": "formula_example",
                "options": {
                    "text": f"V = {small_cube_size}³ = {small_cube_size**3} cm³",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": 15, "z": 0},
                    "textAlign": "center"
                }
            }
        ]
    })
    
    # COMPUTE PHASE
    
    # Compute 1: Calculate volume of small cube
    scenes['compute_1'] = {
        "shapes": []
    }
    
    # Add one small cube with distinct edges
    scenes['compute_1']['shapes'].append({
        "type": "Group",
        "id": "compute_small_cube_group",
        "options": {
            "translate": {"x": -70, "y": 0, "z": 0}
        },
        "children": [
            # Solid filled cube
            {
                "type": "Box",
                "id": "compute_small_cube",
                "options": {
                    "width": small_cube_size * 10,
                    "height": small_cube_size * 10,
                    "depth": small_cube_size * 10,
                    "stroke": 0,
                    "fill": True,
                    "color": phase_colors['compute']
                }
            },
            # Wireframe for edges
            {
                "type": "Box",
                "id": "compute_small_cube_wireframe",
                "options": {
                    "width": small_cube_size * 10,
                    "height": small_cube_size * 10,
                    "depth": small_cube_size * 10,
                    "stroke": 1.5,
                    "fill": False,
                    "color": "#000000"
                }
            }
        ]
    })
    
    # Add formula and calculation
    scenes['compute_1']['shapes'].append({
        "type": "Shape",
        "id": "compute_formula",
        "options": {
            "stroke": 0,
            "translate": {"x": 50, "y": 0, "z": 0},
            "color": "transparent"
        },
        "children": [
            {
                "type": "Text",
                "id": "compute_formula_text",
                "options": {
                    "text": "Volume = s³",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": -30, "z": 0},
                    "textAlign": "center"
                }
            },
            {
                "type": "Text",
                "id": "compute_step1",
                "options": {
                    "text": f"Volume = {small_cube_size}³",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": 0, "z": 0},
                    "textAlign": "center"
                }
            },
            {
                "type": "Text",
                "id": "compute_step2",
                "options": {
                    "text": f"Volume = {small_cube_size**3} cm³",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": 30, "z": 0},
                    "textAlign": "center"
                }
            }
        ]
    })
    
    # Compute 2: Calculate total volume
    scenes['compute_2'] = {
        "shapes": []
    }
    
    # Position small cubes in an array
    small_cubes_positions = []
    grid_size = min(3, round(small_cube_count**0.5))
    
    for i in range(grid_size):
        for j in range(grid_size):
            for k in range((small_cube_count // (grid_size**2)) + 1):
                index = i * grid_size * grid_size + j * grid_size + k
                if index < small_cube_count:
                    small_cubes_positions.append((
                        (i - (grid_size-1)/2) * small_cube_size * 1.2 * 10,
                        (k - ((small_cube_count // (grid_size**2))/2)) * small_cube_size * 1.2 * 10,
                        (j - (grid_size-1)/2) * small_cube_size * 1.2 * 10
                    ))
    
    # Add small cubes with distinct edges
    for i, (x, y, z) in enumerate(small_cubes_positions):
        scenes['compute_2']['shapes'].append({
            "type": "Group",
            "id": f"compute2_small_cube_group_{i+1}",
            "options": {
                "translate": {"x": -80 + x, "y": y, "z": z}
            },
            "children": [
                # Solid filled cube
                {
                    "type": "Box",
                    "id": f"compute2_small_cube_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 0,
                        "fill": True,
                        "color": phase_colors['compute']
                    }
                },
                # Wireframe for edges
                {
                    "type": "Box",
                    "id": f"compute2_small_cube_wireframe_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 1.5,
                        "fill": False,
                        "color": "#000000"
                    }
                }
            ]
        })
    
    # Add calculation text
    scenes['compute_2']['shapes'].append({
        "type": "Shape",
        "id": "compute2_formula",
        "options": {
            "stroke": 0,
            "translate": {"x": 80, "y": 0, "z": 0},
            "color": "transparent"
        },
        "children": [
            {
                "type": "Text",
                "id": "compute2_step1",
                "options": {
                    "text": f"Total Volume = {small_cube_count} × {small_cube_size**3} cm³",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": -15, "z": 0},
                    "textAlign": "center"
                }
            },
            {
                "type": "Text",
                "id": "compute2_step2",
                "options": {
                    "text": f"Total Volume = {small_cube_count * small_cube_size**3} cm³",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": 15, "z": 0},
                    "textAlign": "center"
                }
            }
        ]
    })
    
    # Compute 3: Show formation of larger cube
    scenes['compute_3'] = {
        "shapes": []
    }
    
    # Add small cubes (less opaque) with distinct edges
    for i, (x, y, z) in enumerate(small_cubes_positions):
        scenes['compute_3']['shapes'].append({
            "type": "Group",
            "id": f"compute3_small_cube_group_{i+1}",
            "options": {
                "translate": {"x": -80 + x, "y": y, "z": z}
            },
            "children": [
                # Solid filled cube (faded)
                {
                    "type": "Box",
                    "id": f"compute3_small_cube_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 0,
                        "fill": True,
                        "color": phase_colors['compute'],
                        "opacity": 0.3
                    }
                },
                # Wireframe for edges (more visible than fill)
                {
                    "type": "Box",
                    "id": f"compute3_small_cube_wireframe_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 1.5,
                        "fill": False,
                        "color": "#000000",
                        "opacity": 0.5
                    }
                }
            ]
        })
    
    # Add larger cube (starting to form) with distinct edges
    scenes['compute_3']['shapes'].append({
        "type": "Group",
        "id": "compute3_large_cube_group",
        "options": {
            "translate": {"x": 80, "y": 0, "z": 0}
        },
        "children": [
            # Solid filled cube (semi-transparent)
            {
                "type": "Box",
                "id": "compute3_large_cube",
                "options": {
                    "width": large_cube_size * 10,
                    "height": large_cube_size * 10,
                    "depth": large_cube_size * 10,
                    "stroke": 0,
                    "fill": True,
                    "color": phase_colors['compute'],
                    "opacity": 0.7
                }
            },
            # Wireframe for clear edges
            {
                "type": "Box",
                "id": "compute3_large_cube_wireframe",
                "options": {
                    "width": large_cube_size * 10,
                    "height": large_cube_size * 10,
                    "depth": large_cube_size * 10,
                    "stroke": 2.5,
                    "fill": False,
                    "color": "#000000",
                    "opacity": 0.9
                }
            }
        ]
    })
    
    # Add transformation arrow
    scenes['compute_3']['shapes'].append({
        "type": "Shape",
        "id": "transform_arrow",
        "options": {
            "stroke": 3,
            "color": "#000000",
            "path": [
                {"x": -30, "y": 0, "z": 0},
                {"x": 30, "y": 0, "z": 0}
            ]
        }
    })
    
    # Add arrowhead
    scenes['compute_3']['shapes'].append({
        "type": "Shape",
        "id": "arrow_head",
        "options": {
            "stroke": 3,
            "color": "#000000",
            "path": [
                {"x": 25, "y": -5, "z": 0},
                {"x": 30, "y": 0, "z": 0},
                {"x": 25, "y": 5, "z": 0}
            ]
        }
    })
    
    # Compute 4: Show final large cube with volume
    scenes['compute_4'] = {
        "shapes": []
    }
    
    # Add larger cube (fully formed) with distinct edges
    scenes['compute_4']['shapes'].append({
        "type": "Group",
        "id": "compute4_large_cube_group",
        "options": {
            "translate": {"x": 0, "y": 0, "z": 0}
        },
        "children": [
            # Solid filled cube
            {
                "type": "Box",
                "id": "compute4_large_cube",
                "options": {
                    "width": large_cube_size * 10,
                    "height": large_cube_size * 10,
                    "depth": large_cube_size * 10,
                    "stroke": 0,
                    "fill": True,
                    "color": phase_colors['compute']
                }
            },
            # Wireframe for clear edges
            {
                "type": "Box",
                "id": "compute4_large_cube_wireframe",
                "options": {
                    "width": large_cube_size * 10,
                    "height": large_cube_size * 10,
                    "depth": large_cube_size * 10,
                    "stroke": 2.5,
                    "fill": False,
                    "color": "#000000"
                }
            }
        ]
    })
    
    # Add volume label
    scenes['compute_4']['shapes'].append({
        "type": "Shape",
        "id": "volume_label",
        "options": {
            "stroke": 0,
            "translate": {"x": 0, "y": -large_cube_size * 7, "z": large_cube_size * 6},
            "color": "transparent"
        },
        "children": [
            {
                "type": "Text",
                "id": "volume_text",
                "options": {
                    "text": f"Volume = {small_cube_count * small_cube_size**3} cm³",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": 0, "z": 0},
                    "textAlign": "center"
                }
            }
        ]
    })
    
    # Add dimension labels
    scenes['compute_4']['shapes'].append({
        "type": "Shape",
        "id": "dimension_label",
        "options": {
            "stroke": 0,
            "translate": {"x": large_cube_size * 7, "y": 0, "z": 0},
            "color": "transparent"
        },
        "children": [
            {
                "type": "Text",
                "id": "dimension_text",
                "options": {
                    "text": f"{large_cube_size} cm",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": 0, "z": 0},
                    "textAlign": "left"
                }
            }
        ]
    })
    
    # CHECK PHASE
    
    # Check 1: Initial verification (0%)
    scenes['check_1'] = {
        "shapes": []
    }
    
    # Add the small cubes with distinct edges
    for i, (x, y, z) in enumerate(positions):
        scenes['check_1']['shapes'].append({
            "type": "Group",
            "id": f"check1_small_cube_group_{i+1}",
            "options": {
                "translate": {"x": x * 10, "y": y * 10, "z": z * 10}
            },
            "children": [
                # Solid filled cube
                {
                    "type": "Box",
                    "id": f"check1_small_cube_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 0,
                        "fill": True,
                        "color": phase_colors['check']
                    }
                },
                # Wireframe for edges
                {
                    "type": "Box",
                    "id": f"check1_small_cube_wireframe_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 1.5,
                        "fill": False,
                        "color": "#000000"
                    }
                }
            ]
        })
    
    # Add progress text
    scenes['check_1']['shapes'].append({
        "type": "Shape",
        "id": "check1_progress",
        "options": {
            "stroke": 0,
            "translate": {"x": 0, "y": -100, "z": 0},
            "color": "transparent"
        },
        "children": [
            {
                "type": "Text",
                "id": "progress_text",
                "options": {
                    "text": "Verification: 0%",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": 0, "z": 0},
                    "textAlign": "center"
                }
            }
        ]
    })
    
    # Check 3: Midpoint verification (50%)
    scenes['check_3'] = {
        "shapes": []
    }
    
    # Add small cubes (half visible) with distinct edges
    for i, (x, y, z) in enumerate(positions[:small_cube_count//2]):
        scenes['check_3']['shapes'].append({
            "type": "Group",
            "id": f"check3_small_cube_group_{i+1}",
            "options": {
                "translate": {"x": -80 + x * 10, "y": y * 10, "z": z * 10}
            },
            "children": [
                # Solid filled cube
                {
                    "type": "Box",
                    "id": f"check3_small_cube_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 0,
                        "fill": True,
                        "color": phase_colors['check']
                    }
                },
                # Wireframe for edges
                {
                    "type": "Box",
                    "id": f"check3_small_cube_wireframe_{i+1}",
                    "options": {
                        "width": small_cube_size * 10,
                        "height": small_cube_size * 10,
                        "depth": small_cube_size * 10,
                        "stroke": 1.5,
                        "fill": False,
                        "color": "#000000"
                    }
                }
            ]
        })
    
    # Add large cube (partially formed) with distinct edges
    scenes['check_3']['shapes'].append({
        "type": "Group",
        "id": "check3_large_cube_group",
        "options": {
            "translate": {"x": 80, "y": 0, "z": 0}
        },
        "children": [
            # Solid filled cube (semi-transparent)
            {
                "type": "Box",
                "id": "check3_large_cube",
                "options": {
                    "width": large_cube_size * 10,
                    "height": large_cube_size * 10,
                    "depth": large_cube_size * 10,
                    "stroke": 0,
                    "fill": True,
                    "color": phase_colors['check'],
                    "opacity": 0.4
                }
            },
            # Wireframe for clear edges
            {
                "type": "Box",
                "id": "check3_large_cube_wireframe",
                "options": {
                    "width": large_cube_size * 10,
                    "height": large_cube_size * 10,
                    "depth": large_cube_size * 10,
                    "stroke": 2,
                    "fill": False,
                    "color": "#000000",
                    "opacity": 0.7
                }
            }
        ]
    })
    
    # Add progress text
    scenes['check_3']['shapes'].append({
        "type": "Shape",
        "id": "check3_progress",
        "options": {
            "stroke": 0,
            "translate": {"x": 0, "y": -100, "z": 0},
            "color": "transparent"
        },
        "children": [
            {
                "type": "Text",
                "id": "progress_text",
                "options": {
                    "text": "Verification: 50%",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": 0, "z": 0},
                    "textAlign": "center"
                }
            }
        ]
    })
    
    # Check 5: Complete verification (100%)
    scenes['check_5'] = {
        "shapes": []
    }
    
    # Add the large cube (fully formed) with distinct edges
    scenes['check_5']['shapes'].append({
        "type": "Group",
        "id": "check5_large_cube_group",
        "options": {
            "translate": {"x": 0, "y": 0, "z": 0}
        },
        "children": [
            # Solid filled cube
            {
                "type": "Box",
                "id": "check5_large_cube",
                "options": {
                    "width": large_cube_size * 10,
                    "height": large_cube_size * 10,
                    "depth": large_cube_size * 10,
                    "stroke": 0,
                    "fill": True,
                    "color": phase_colors['check']
                }
            },
            # Wireframe for clear edges
            {
                "type": "Box",
                "id": "check5_large_cube_wireframe",
                "options": {
                    "width": large_cube_size * 10,
                    "height": large_cube_size * 10,
                    "depth": large_cube_size * 10,
                    "stroke": 2.5,
                    "fill": False,
                    "color": "#000000"
                }
            }
        ]
    })
    
    # Add verification information
    scenes['check_5']['shapes'].append({
        "type": "Shape",
        "id": "verification_info",
        "options": {
            "stroke": 0,
            "translate": {"x": 0, "y": -100, "z": 0},
            "color": "transparent"
        },
        "children": [
            {
                "type": "Text",
                "id": "verify_title",
                "options": {
                    "text": "Verification: 100% Complete",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": -15, "z": 0},
                    "textAlign": "center"
                }
            },
            {
                "type": "Text",
                "id": "verify_formula",
                "options": {
                    "text": f"Volume of large cube = {small_cube_count * small_cube_size**3} cm³",
                    "fontSize": 16,
                    "color": "#000000",
                    "translate": {"x": 0, "y": 15, "z": 0},
                    "textAlign": "center"
                }
            }
        ]
    })
    
    return scenes

def generate_zdog_config(visualization_text):
    """Generate Zdog configuration based on visualization type and parameters."""
    visualization_type = visualization_text.get('visualization_type', 'default')
    
    # Select appropriate generator based on visualization type
    if visualization_type == 'cubes_to_larger_cube':
        scenes = get_cubes_to_larger_cube_config(visualization_text)
    else:
        # Default to cubes for now
        scenes = get_cubes_to_larger_cube_config(visualization_text)
    
    # Fill in any missing scenes with defaults
    all_scenes = {}
    
    # Ensure we have scenes for each phase and step
    for phase in ['comprehend', 'compute', 'check']:
        for step in range(1, 6):  # Up to 5 steps per phase
            scene_key = f"{phase}_{step}"
            if scene_key in scenes:
                all_scenes[scene_key] = scenes[scene_key]
    
    # Add connect scene
    if 'connect_1' in scenes:
        all_scenes['connect_1'] = scenes['connect_1']
    
    # Configure global settings
    config = {
        "global": {
            "dragRotate": True,
            "zoom": 1.0,
            "backgroundColor": "#ffffff",
            "isometric": True  # Enable isometric view by default
        },
        "scenes": all_scenes
    }
    
    return config

def generate_zdog_config_from_csv(csv_file):
    """
    Generate Zdog configuration from CSV content.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        JSON string with Zdog configuration
    """
    # Read CSV content
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        csv_content = {}
        for row in reader:
            if len(row) >= 2:
                csv_content[row[0]] = row[1]
    
    # Extract text for visualizations
    visualization_text = extract_visualization_text(csv_content)
    
    # Generate Zdog configuration
    config = generate_zdog_config(visualization_text)
    
    # Convert to JSON string
    return json.dumps(config, indent=2)

def generate_zdog_scenes_for_html(csv_file, output_dir=None):
    """
    Generate Zdog scene config from CSV content and save to file or return as string.
    
    Args:
        csv_file: Path to CSV file
        output_dir: Directory to save output file (if None, returns as string)
        
    Returns:
        If output_dir is None, returns the JSON string with Zdog configuration
        Otherwise, returns the path to the saved file
    """
    # Generate Zdog configuration
    config_json = generate_zdog_config_from_csv(csv_file)
    
    # Save to file if output_dir is provided
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'zdog_scenes.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(config_json)
        print(f"Generated and saved Zdog configuration to {output_file}")
        return output_file
    
    return config_json

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Zdog configuration from CSV content')
    parser.add_argument('csv_file', help='Path to the CSV file')
    parser.add_argument('--output-dir', help='Directory to save output file')
    
    args = parser.parse_args()
    
    result = generate_zdog_scenes_for_html(args.csv_file, args.output_dir)
    
    if not args.output_dir:
        # Print generated JSON
        print(result)
