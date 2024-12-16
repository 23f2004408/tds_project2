import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
import requests
import json

def main():
    # Check if the AIPROXY_TOKEN environment variable is set
    if "AIPROXY_TOKEN" not in os.environ:
        print("Error: AIPROXY_TOKEN environment variable not found.")
        sys.exit(1)

    aiproxy_token = os.environ["AIPROXY_TOKEN"]

    # Parse command-line arguments
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py <dataset.csv>")
        sys.exit(1)

    csv_filename = sys.argv[1]

    # Attempt to read the CSV file with different encoding
    try:
        data = pd.read_csv(csv_filename, encoding='ISO-8859-1')  # Try ISO-8859-1 encoding first
    except UnicodeDecodeError:
        try:
            # If ISO-8859-1 fails, try utf-8 with error replacement
            print(f"ISO-8859-1 encoding failed. Trying UTF-8 with error replacement.")
            data = pd.read_csv(csv_filename, encoding='utf-8', errors='replace')
        except Exception as e:
            print(f"Error reading {csv_filename}: {e}")
            sys.exit(1)

    # Perform analysis and generate outputs
    analyze_and_generate(data, csv_filename, aiproxy_token)

def analyze_and_generate(data, csv_filename, aiproxy_token):
    # Summarize the dataset
    summary = {
        "shape": data.shape,
        "columns": data.columns.tolist(),
        "missing_values": data.isnull().sum().to_dict(),
        "sample_data": data.head(5).to_dict(orient='records')
    }

    # Generate correlation matrix
    correlation_matrix = data.corr(numeric_only=True).to_dict()

    # Create exactly 4 visualizations
    images = create_visualizations(data, csv_filename)

    # Generate LLM-based analysis via AI Proxy
    generate_readme(summary, correlation_matrix, images, aiproxy_token)

def create_visualizations(data, filename):
    """Generate exactly 4 visualizations for the dataset."""
    images = []
    base_name = os.path.splitext(filename)[0]

    # Heatmap for correlations
    try:
        numeric_data = data.select_dtypes(include=[np.number])
        if not numeric_data.empty:
            plt.figure(figsize=(10, 8))
            sns.heatmap(numeric_data.corr(), annot=True, cmap="coolwarm")
            heatmap_file = f"{base_name}_heatmap.png"
            plt.title("Correlation Matrix Heatmap")
            plt.savefig(heatmap_file, dpi=100)
            plt.close()
            images.append({"filename": heatmap_file, "description": "A heatmap showing the correlation matrix of numeric columns."})
    except Exception as e:
        print(f"Failed to create heatmap: {e}")

    # Distribution plots for numeric columns
    try:
        numeric_columns = numeric_data.columns
        for column in numeric_columns[:3]:  # Up to 3 columns
            plt.figure(figsize=(8, 5))
            sns.histplot(data[column].dropna(), kde=True, color="blue")
            plt.title(f"Distribution of {column}")
            plt.xlabel(column)
            plt.ylabel("Frequency")
            dist_file = f"{base_name}_{column}_distribution.png"
            plt.savefig(dist_file, dpi=100)
            plt.close()
            images.append({"filename": dist_file, "description": f"A distribution plot showing the spread of the `{column}` column."})
            if len(images) == 4:  # Limit to 4 images
                break
    except Exception as e:
        print(f"Failed to create distribution plots: {e}")

    # Handle case where fewer than 4 images were created
    while len(images) < 4:
        placeholder_file = f"{base_name}_placeholder_{len(images)+1}.png"
        plt.figure(figsize=(6, 4))
        plt.text(0.5, 0.5, "Placeholder", fontsize=20, ha='center', va='center')
        plt.axis('off')
        plt.savefig(placeholder_file, dpi=100)
        plt.close()
        images.append({"filename": placeholder_file, "description": "A placeholder visualization."})

    return images

def generate_readme(summary, correlation_matrix, images, aiproxy_token):
    """Generate Markdown README by interacting with the AI Proxy."""
    visualization_details = "\n".join([f"- {img['description']} (see `{img['filename']}`)" for img in images])

    prompt = f"""
    Analyze the following dataset:
    - Shape: {summary['shape']}
    - Columns: {summary['columns']}
    - Missing Values: {summary['missing_values']}
    - Sample Data: {summary['sample_data']}
    - Correlation Matrix: {correlation_matrix}
    The dataset includes the following visualizations:
    {visualization_details}
    Based on this data and visualizations, provide a story-like analysis that includes insights, trends, and potential use cases.
    """

    # Prepare the request payload
    request_data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a data analyst generating Markdown reports."},
            {"role": "user", "content": prompt}
        ]
    }

    # Send the request to the AI Proxy
    try:
        response = requests.post(
            "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {aiproxy_token}"
            },
            data=json.dumps(request_data)
        )
        
        # Check for successful response
        response.raise_for_status()

        # Extract the response content
        analysis = response.json()['choices'][0]['message']['content']

        # Debugging: Print the analysis to ensure it is generated
        print("Analysis content from LLM:\n", analysis)

        # Create README.md
        with open("README.md", "w") as f:
            f.write("# Dataset Analysis\n\n")
            f.write(analysis)
            f.write("\n\n## Visualizations\n")
            for img in images:
                f.write(f"![{img['description']}]({img['filename']})\n")
        print("README.md and visualizations generated successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error during the request to AI Proxy: {e}")
    except Exception as e:
        print(f"Failed to generate README.md: {e}")

if __name__ == "__main__":
    main()
