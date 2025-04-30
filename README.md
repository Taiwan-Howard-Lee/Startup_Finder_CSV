# Startup Finder

A powerful tool for discovering and analyzing startups in specific domains using advanced AI and search techniques.

## Features

- **Intelligent Query Expansion**: Automatically generates semantically similar variations of your search query to maximize discovery.
- **Advanced Startup Discovery**: Uses Google Search API and Gemini AI to find relevant startups.
- **Comprehensive Data Enrichment**: Gathers detailed information about each startup from multiple sources.
- **Search Grounding**: Leverages Gemini Pro's search grounding capability to access real-time information from the web.
- **Parallel Processing**: Efficiently processes large amounts of data using parallel execution.
- **CSV Output**: Generates a clean, structured CSV file with all the gathered information.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Taiwan-Howard-Lee/Startup_Finder_CSV.git
   cd Startup_Finder_CSV
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up your API keys:
   - Create a `.env` file in the root directory
   - Add your API keys:
     ```
     GEMINI_API_KEY=your_gemini_api_key
     GOOGLE_SEARCH_API_KEY=your_google_search_api_key
     GOOGLE_CX_ID=your_google_custom_search_engine_id
     ```

## Usage

Run the main script with your search query:

```
python startup_finder.py "Nature-Based Solutions startup in Brazil"
```

### Options

- `--max-results`: Maximum number of results per query (default: 100)
- `--expansions`: Number of query expansions to generate (default: 5)
- `--output`: Output CSV file path (default: `startups_{timestamp}.csv`)

## Search Grounding

This project uses Gemini Pro's search grounding capability to access real-time information from the web. This allows the AI to:

1. Verify startup information against the latest data
2. Fill in missing details from multiple sources
3. Validate the relevance of startups to your query
4. Provide more accurate and up-to-date results

To see an example of search grounding in action, run:

```
python examples/search_grounding_example.py
```

## Testing

Run the tests to verify that everything is working correctly:

```
python run_tests.py
```

Or run specific tests:

```
python tests/functions/test_search_grounding.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Google Gemini API for AI-powered analysis
- Google Custom Search API for discovery
- All contributors to this project
