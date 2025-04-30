# Startup Intelligence Finder

A tool that discovers and collects information about startups based on search queries, using Google Search and Gemini AI for intelligent filtering and data enrichment.

## Features

- **Two-Phase Crawling**: Discovers startup names from search results, then enriches data for each startup
- **LLM-Based Filtering**: Uses Gemini AI to extract, validate, and filter startup names
- **Search Grounding**: Leverages Gemini Pro's ability to search the web for real-time information
- **CSV Generation**: Outputs clean, structured data in CSV format for easy analysis
- **Customizable Queries**: Search for startups in any industry or location

## Project Structure

```
startup-finder/
├── src/                      # Source code
│   ├── collector/            # Input handling and query expansion
│   ├── processor/            # Core crawler and data processing
│   └── utils/                # API clients and utility functions
├── tests/                    # Test files
│   ├── test_enhanced_crawler.py  # Tests for enhanced crawler
│   ├── test_uk_startups.py       # Tests for UK startup discovery
│   └── ...                       # Other test files
├── generate_startup_csv.py   # Main script to generate CSV output
├── run_tests.py              # Script to run all tests
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

## Search Grounding

The Startup Intelligence Finder uses Gemini Pro's search grounding capability to access real-time information from the web. This powerful feature allows the AI to:

1. **Verify Information**: Cross-check startup details against the latest online sources
2. **Fill Knowledge Gaps**: Find missing information that isn't available in the initial data
3. **Validate Relevance**: Ensure startups are truly relevant to the search query
4. **Access Latest News**: Incorporate recent developments and announcements
5. **Enhance Accuracy**: Correct outdated or inaccurate information

To see an example of search grounding in action, run:

```
python examples/search_grounding_example.py
```

## Usage

Run the CSV generator script:

```
python startup_finder.py
```

Follow the prompts to:
1. Enter a search query (e.g., "fintech startups in singapore")
2. Specify the number of search results to process
3. Provide a name for the output CSV file

The script will:
- Discover startup names from search results
- Filter out non-startup names using Gemini AI with search grounding
- Enrich data for each startup using multiple sources
- Validate and correct information using search grounding
- Generate a CSV file with the results

## Example Output

The CSV file contains the following columns:
- Company Name
- Website
- Location
- Founded Year
- Product Description
- Source URL

## Testing

The project includes a comprehensive test suite in the `tests/` directory. To run the tests:

```bash
# Run all tests
python run_tests.py

# Run a specific test
python run_tests.py test_enhanced_crawler
```

The test suite includes:
- Tests for the crawler with Jina-inspired techniques
- Tests for parallel processing
- Tests for URL normalization and adaptive crawling
- Tests for startup discovery and data enrichment
- Tests for search grounding functionality

## Dependencies

- Google API Client
- Google Generative AI (Gemini API)
- BeautifulSoup4
- Requests
- Python-dotenv
- Google Search API

## License

MIT License
