# Interactive Math Applet Generator

This repository allows non-technical users to create interactive 3D math visualizations using the Zdog library and OpenAI integration.

## How It Works

1. Edit the `applet_data.csv` file with your math problem details
2. Commit your changes to trigger the automatic generation process
3. The system generates the applet and publishes it to the public repository

## Editing the Applet CSV File

To create a new applet:

1. Navigate to the `applet_data.csv` file in this repository
2. Click the pencil icon (Edit this file) on GitHub
3. Modify the fields in the CSV:
   - `title`: The name of your applet (e.g., "Box Dimensions Challenge")
   - `question_text`: The full math problem text
   - `compute_step_*`: Step-by-step solution shown in the "compute" tab
   - `connect_question_*`: Multiple-choice questions for the "connect" tab
   - (You can leave the given/tofind blank to use automatic extraction)
4. Click "Commit changes" when done

## How the Automatic Process Works

When you commit your changes to `applet_data.csv`:

1. A GitHub Action automatically runs
2. The system generates the applet using OpenAI and Zdog 3D
3. The applet is pushed to the public repository
4. The public index page is automatically updated
5. The applet becomes available on the GitHub Pages site

## Required Repository Secrets

For this workflow to function, the following secrets must be configured in the repository:

1. **OPENAI_API_KEY**: Your OpenAI API key for generating visualizations
2. **GH_PAT**: A GitHub Personal Access Token for pushing to the public repository

### Setting Up the PAT (Personal Access Token)

1. Log in to GitHub and go to your account settings
2. Navigate to Developer Settings > Personal access tokens > Generate new token
3. Give it a descriptive name like "Applet Generator"
4. Select the "repo" scope to allow pushing to repositories
5. Click "Generate token" and copy the token value
6. Add it as a repository secret named `GH_PAT` in this repository's settings

## Troubleshooting

- If the applet generation fails, check the GitHub Actions logs for details
- Common issues:
  - Missing or invalid OpenAI API key
  - Invalid CSV format (make sure columns and rows are properly formatted)
  - Network or permission issues when pushing to the public repository
  
## Example CSV

Here's an example of a properly formatted applet definition:

```
title,Box Dimensions Challenge
question_text,"A cuboidal box with dimensions 8 cm × 6 cm × 12 cm is melted into another cuboid whose width is 16 cm. Find the length and height of the new cuboid formed if l = h."
compute_step_1,Step 1: Calculate the volume of the original box
compute_step_2,Volume = length × width × height = 8 cm × 6 cm × 12 cm = 576 cm³
connect_question_1,"To find the length and height of a box using its volume and width, which formula should we use?"
connect_option_correct_1_1,Length = √(Volume ÷ Width) when Length = Height
connect_option_wrong_1_1,Length = Volume × Width × Height
```

**Note**: The system will automatically extract given and to-find information from the question text using AI, but you can override this by explicitly providing `given_1`, `given_2`, etc. and `tofind_1`, `tofind_2`, etc. fields.
