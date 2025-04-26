# Startup Intelligence Finder

A tool that discovers and collects information about startups based on search queries, using Google Search and Gemini AI for intelligent filtering and data enrichment.

## Features

- **Three-Phase Processing Pipeline**:
  - **Phase 1 (Discovery)**: Discovers startup names from search results
  - **Phase 2 (Enrichment)**: Enriches data for each startup from multiple sources
  - **Phase 3 (Validation)**: Uses Gemini 2.5 Pro to validate and correct data before output
- **LLM-Based Filtering**: Uses Gemini AI to extract, validate, and filter startup names
- **Parallel Processing**: Utilizes multi-threading for faster data collection and processing
- **Adaptive Crawling**: Implements Jina-inspired techniques for more effective data extraction
- **URL Normalization**: Avoids duplicate content through intelligent URL handling
- **LLM-Based Data Extraction**: Extracts structured data from multiple sources using AI
- **Data Validation**: Automatically detects and corrects anomalies in the collected data
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
│   ├── crawler/              # Tests for crawler components
│   ├── collector/            # Tests for collector components
│   └── utils/                # Tests for utility components
├── data/                     # Data files and output
│   ├── *.csv                 # CSV output files
│   └── *.json                # JSON data files
├── docs/                     # Documentation
│   ├── PROJECT_PLAN.md       # Project planning document
│   └── README.md             # Copy of this README
├── maintenance/              # Maintenance scripts
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

## Usage

### Basic Usage

Run the main script:

```
python startup_finder.py
```

This will start the interactive mode where you can:
1. Search for startups using a query
2. Directly input startup names
3. Load startup names from a file

### Command Line Options

You can also run the script with command-line arguments:

```
python startup_finder.py --query "fintech startups in singapore" --max-results 10 --output-file data/fintech_startups.csv
```

Key options:
- `--query` or `-q`: Search query to find startups
- `--max-results` or `-m`: Maximum number of search results to process per query (default: 10)
- `--num-expansions` or `-n`: Number of query expansions to generate (1-100, default: 10)
- `--output-file` or `-o`: Path to the output CSV file
- `--no-expansion`: Disable query expansion
- `--startups` or `-s`: List of startup names to directly search for, bypassing discovery phase
- `--startups-file` or `-f`: Path to a file containing startup names, one per line
- `--max-workers` or `-w`: Maximum number of parallel workers for web crawling (default: 20)

### Direct Startup Input

If you already know which startups you want to research:

```
python startup_finder.py --startups "Company1" "Company2" "Company3"
```

### Loading Startups from a File

You can also load startup names from a text file:

```
python startup_finder.py --startups-file my_startups.txt
```

The script will:
- Discover startup names from search results (or use provided names)
- Filter out non-startup names using Gemini AI
- Enrich data for each startup using parallel processing
- Validate and correct data using Gemini 2.5 Pro
- Generate a clean, validated CSV file with the results

## Data Sources

The tool uses a sophisticated approach to gather data from multiple sources:

### Google Search as a Proxy

Instead of directly scraping websites like LinkedIn (which can be against terms of service), the tool uses Google Search as a proxy:
- Uses site-specific searches (e.g., `site:linkedin.com/company/ "company name"`)
- Extracts data from search snippets and cached pages
- Respects rate limits and robots.txt rules

### Priority of Data Sources

Data is collected with the following priority:
1. **Official Company Website**: Primary source for company information
2. **LinkedIn Company Page**: For company size, founding information, and team details
3. **General Search Results**: For additional context and missing information

### LLM-Based Extraction

The tool uses Gemini AI to extract structured data from unstructured content:
- Identifies company descriptions, locations, founding years, etc.
- Validates and filters startup names to ensure relevance
- Combines information from multiple sources into a coherent profile

## Example Output

The CSV file contains the following columns:
- Company Name
- Website
- LinkedIn
- Location
- Founded Year
- Industry
- Company Size
- Funding
- Product Description
- Products/Services
- Team
- Contact
- Source URL

## Testing

The project includes a comprehensive test suite in the `tests/` directory. To run the tests:

```bash
# Run all tests
python run_tests.py

# Run a specific test
python run_tests.py test_enhanced_crawler
```

The test suite is organized into subdirectories:

- **tests/crawler/**: Tests for crawler components
  - Enhanced crawler with Jina-inspired techniques
  - Parallel processing
  - URL normalization and adaptive crawling
  - Startup discovery and data enrichment
  - LinkedIn and company website data collection

- **tests/collector/**: Tests for collector components
  - Query expansion
  - AutoScraper functionality

- **tests/utils/**: Tests for utility components
  - API key handling
  - LLM-based filtering

## Dependencies

- Google API Client
- Gemini API
- BeautifulSoup4
- Requests
- Python-dotenv

## License

MIT License
