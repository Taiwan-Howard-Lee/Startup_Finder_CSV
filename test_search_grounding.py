import os
import csv
import json
import pandas as pd
from dotenv import load_dotenv
from src.utils.api_client import GeminiAPIClient

def main():
    # Load environment variables
    load_dotenv()

    # Initialize Gemini API client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables")
        return

    gemini_client = GeminiAPIClient(api_key)
    pro_model = gemini_client.pro_model

    # Load the CSV file
    csv_file = "data/testing EV.csv"
    try:
        df = pd.read_csv(csv_file)
        print(f"Loaded CSV file with {len(df)} rows")
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return

    # Take a small sample for testing
    sample_df = df.head(2)
    sample_data = sample_df.to_dict('records')

    # Convert to JSON for the prompt
    sample_json = json.dumps(sample_data, indent=2)

    # Create a prompt for Gemini Pro with search grounding
    prompt = f"""
    You are a data validation expert for EV charging and energy technology companies. I have a dataset of companies related to the EV charging and energy technology sector.

    Please analyze the following company data for anomalies, inconsistencies, or missing information, and provide a corrected version.

    IMPORTANT: Use the search tool to verify company information when possible, especially for:
    - Company existence and correct name spelling
    - Founded year
    - Location
    - Industry classification
    - Funding information
    - Key people/founders

    For each company, search for its name plus relevant keywords to verify the information.

    Here is the data to validate and correct:

    {sample_json}

    Please provide the corrected data in JSON format, maintaining the same structure but with any corrections or additions you've made. Also include a "Validation Sources" field for each company listing the sources you used to verify the information.

    After searching for information, please provide a detailed explanation of what you found and what corrections you made.
    """

    print("Sending request to Gemini Pro with search grounding...")

    # Get response from Gemini Pro with search grounding
    response = pro_model.generate_content(prompt, stream=True)

    # Print the response
    print("\nGemini Pro Response:")

    # Process the streaming response
    search_queries = []
    full_response = ""

    for chunk in response:
        if hasattr(chunk, 'candidates') and chunk.candidates:
            candidate = chunk.candidates[0]
            if hasattr(candidate, 'content') and candidate.content:
                content = candidate.content
                if hasattr(content, 'parts') and content.parts:
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            print(part.text, end="", flush=True)
                            full_response += part.text
                        elif hasattr(part, 'function_call'):
                            if part.function_call.name == "search":
                                query = part.function_call.args.get("query", "No query provided")
                                search_queries.append(query)
                                print(f"\n\nSearch query: {query}\n", end="", flush=True)

    print("\n\nSearch queries used:")
    for i, query in enumerate(search_queries):
        print(f"  {i+1}. {query}")

    # With streaming, we can't get the grounding metadata directly
    # Instead, we've captured the search queries during streaming
    print("\nNote: When using streaming with Gemini, we can't directly access the grounding metadata.")
    print("However, we've captured the search queries that were used during the process.")

if __name__ == "__main__":
    main()
