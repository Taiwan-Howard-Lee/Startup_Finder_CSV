# Startup Intelligence Finder

A tool that discovers and collects information about startups based on search queries, using Google Search and Gemini AI for intelligent filtering and data enrichment.

## Features

- **Two-Phase Crawling**: Discovers startup names from search results, then enriches data for each startup
- **LLM-Based Filtering**: Uses Gemini AI to extract, validate, and filter startup names
- **CSV Generation**: Outputs clean, structured data in CSV format for easy analysis
- **Customizable Queries**: Search for startups in any industry or location

## Project Structure

```
startup-finder/
├── src/                      # Source code
│   ├── collector/            # Input handling and query expansion
│   ├── processor/            # Core crawler and data processing
│   └── utils/                # API clients and utility functions
├── generate_startup_csv.py   # Main script to generate CSV output
├── run_complete_test.py      # Test script for the complete pipeline
├── setup_env.py              # Environment setup and API key validation
└── requirements.txt          # Project dependencies
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/startup-finder.git
   cd startup-finder
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   GOOGLE_SEARCH_API_KEY=your_google_search_api_key
   GOOGLE_CSE_ID=your_google_custom_search_engine_id
   ```

## Usage

Run the CSV generator script:

```
python generate_startup_csv.py
```

Follow the prompts to:
1. Enter a search query (e.g., "fintech startups in singapore")
2. Specify the number of search results to process
3. Provide a name for the output CSV file

The script will:
- Discover startup names from search results
- Filter out non-startup names using Gemini AI
- Enrich data for each startup
- Generate a CSV file with the results

## Example Output

The CSV file contains the following columns:
- Company Name
- Website
- Location
- Founded Year
- Product Description
- Source URL

## Dependencies

- Google API Client
- Gemini API
- BeautifulSoup4
- Requests
- Python-dotenv

## License

MIT License
