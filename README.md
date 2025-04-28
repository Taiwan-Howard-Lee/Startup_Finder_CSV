# Startup Intelligence Finder

A comprehensive tool that discovers, enriches, and validates information about startups based on search queries. It leverages Google Search API and Google's Gemini AI models for intelligent data processing, filtering, and validation.

## Overview

The Startup Intelligence Finder uses a sophisticated three-phase pipeline to gather high-quality, structured data about startups matching your search criteria. It combines traditional web crawling techniques with advanced AI capabilities to deliver comprehensive startup profiles in a clean CSV format.

## Features

### Core Pipeline

- **Three-Phase Processing Architecture**:
  - **Phase 1 (Discovery)**: Identifies relevant startup names from search results exclusively using LLM-based filtering with Gemini AI
  - **Phase 2 (Enrichment)**: Gathers detailed information about each startup from multiple sources using parallel processing
  - **Phase 3 (Validation)**: Uses Gemini 2.5 Pro to validate, correct, and standardize data before final output

### Advanced Capabilities

- **Intelligent Query Expansion**: Generates up to 100 semantically similar search queries to maximize discovery
- **Multi-Source Data Collection**: Prioritizes official websites and LinkedIn profiles, with fallbacks to general search results
- **Parallel Processing**: Utilizes multi-threading for significantly faster data collection and processing
- **Adaptive Crawling**: Implements Jina-inspired techniques for more effective data extraction
- **URL Normalization**: Avoids duplicate content through intelligent URL handling
- **Error Recovery**: Includes robust fallback mechanisms throughout the pipeline

### AI Integration

- **LLM-Based Filtering**: Uses Gemini AI to extract, validate, and filter startup names
- **Structured Data Extraction**: Employs AI to extract consistent information from unstructured content
- **Data Validation**: Automatically detects and corrects anomalies in the collected data
- **Format Standardization**: Ensures consistent data formats across all entries

### User Experience

- **Flexible Input Options**: Accept direct startup names, file input, or search queries
- **Interactive Mode**: User-friendly guided experience with clear prompts
- **Command-Line Interface**: Powerful options for automation and customization
- **Comprehensive Output**: Detailed CSV with key startup information

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

The Startup Intelligence Finder offers multiple ways to use the tool, from a simple interactive mode to powerful command-line options for advanced users.

### Interactive Mode

For a guided experience, simply run:

```bash
python startup_finder.py
```

This launches the interactive mode which will:
1. Present you with three options:
   - Search for startups using a query
   - Directly input startup names
   - Load startup names from a file
2. Guide you through setting parameters like:
   - Number of search results to process
   - Number of query expansions (1-100)
   - Number of parallel workers
   - Output file location

### Command Line Interface

For automation or more control, use command-line arguments:

```bash
# Basic search query
python startup_finder.py --query "fintech startups in singapore"

# Advanced configuration
python startup_finder.py --query "AI startups in healthcare" --max-results 15 --num-expansions 50 --max-workers 30 --output-file data/healthcare_ai_startups.csv
```

#### Available Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--query` | `-q` | Search query to find startups | (Required unless using `--startups`) |
| `--max-results` | `-m` | Maximum search results per query | 10 |
| `--num-expansions` | `-n` | Number of query expansions to generate | 10 |
| `--output-file` | `-o` | Path to the output CSV file | data/startups_[timestamp].csv |
| `--no-expansion` | | Disable query expansion | (Expansion enabled) |
| `--startups` | `-s` | List of startup names to research | (None) |
| `--startups-file` | `-f` | File containing startup names | (None) |
| `--max-workers` | `-w` | Parallel workers for web crawling | 40 |
| `--upload-to-drive` | `-u` | Upload CSV to Google Drive | (Disabled) |
| `--credentials-path` | `-c` | Path to Google Drive credentials | credentials.json |

### Input Methods

#### 1. Search Query

The most common approach - provide a search query and let the tool discover startups:

```bash
python startup_finder.py --query "cybersecurity startups in london"
```

#### 2. Direct Startup Input

When you already know which startups you want to research:

```bash
python startup_finder.py --startups "Monzo" "Revolut" "Starling Bank"
```

#### 3. Startup List from File

For researching a large list of startups:

```bash
python startup_finder.py --startups-file my_startups.txt
```

Where `my_startups.txt` contains one startup name per line.

### Processing Pipeline

For any input method, the tool follows the same three-phase pipeline:

1. **Discovery Phase**:
   - For search queries: Discovers startup names from search results
   - For direct input: Uses the provided startup names

2. **Enrichment Phase**:
   - Gathers detailed information about each startup
   - Collects data from official websites, LinkedIn, and other sources
   - Uses parallel processing for efficiency

3. **Validation Phase**:
   - Uses Gemini 2.5 Pro to validate and correct the collected data
   - Standardizes formats and fills in missing information where possible
   - Ensures data quality and consistency

4. **Output Generation**:
   - Creates a comprehensive CSV file with detailed startup information
   - Includes company details, contact information, and business data
   - Optionally uploads results directly to Google Drive for cloud storage

## Data Collection Architecture

The Startup Intelligence Finder employs a sophisticated multi-source data collection strategy designed to maximize data quality while respecting website terms of service.

### Ethical Data Collection

Instead of directly scraping websites (which can violate terms of service), the tool uses a combination of:

- **Google Search API**: For discovering content and using search snippets
- **Site-Specific Queries**: For targeted data collection (e.g., `site:linkedin.com/company/ "company name"`)
- **Cached Content**: For accessing information without heavy site traffic
- **Robots.txt Compliance**: Automatically respects website crawling policies
- **Rate Limiting**: Implements delays to avoid overwhelming any single data source

### Data Source Prioritization

The system collects data with the following priority hierarchy:

1. **Official Company Website**
   - Company descriptions and mission statements
   - Product and service information
   - Team details and company history
   - Contact information and locations

2. **LinkedIn Company Pages**
   - Company size and employee count
   - Founding information and timeline
   - Industry categorization
   - Funding rounds and investors

3. **General Search Results**
   - News articles and press releases
   - Industry reports and analyses
   - Conference and event mentions
   - Additional context and verification

### AI-Powered Data Extraction

The tool leverages Google's Gemini AI models at multiple stages:

1. **Gemini 2.5 Flash** (for routine tasks)
   - Query expansion for broader discovery
   - Initial data extraction from structured content
   - Initial processing of search results

2. **Gemini 2.5 Pro** (for complex tasks)
   - Startup name validation and filtering
   - Comprehensive data extraction from unstructured content
   - Final data validation and correction
   - Format standardization and anomaly detection

### Data Processing Pipeline

The data flows through a sophisticated processing pipeline:

1. **Discovery**: Identifies potential startup names from search results using Gemini AI
2. **Validation**: Filters out non-startup entities and ensures relevance using LLM-based analysis
3. **Enrichment**: Gathers detailed information from multiple sources
4. **Normalization**: Standardizes data formats and structures
5. **Verification**: Cross-references information across sources
6. **Correction**: Identifies and fixes anomalies or inconsistencies
7. **Consolidation**: Combines all information into a unified profile

## Output Format

The tool generates a comprehensive CSV file with detailed startup information, structured for easy analysis and integration with other tools.

### CSV Structure

| Column | Description | Example |
|--------|-------------|---------|
| Company Name | Official name of the startup | Monzo |
| Website | Company's official website | https://monzo.com |
| LinkedIn | LinkedIn company page | https://linkedin.com/company/monzo |
| Location | Company headquarters | London, UK |
| Founded Year | Year the company was founded | 2015 |
| Industry | Primary industry or sector | Fintech |
| Company Size | Number of employees | 1,001-5,000 employees |
| Funding | Latest funding information | $500M Series G |
| Product Description | Brief description of main product | Digital banking platform |
| Products/Services | List of key offerings | Mobile banking, Business accounts, Savings |
| Team | Key team members | Tom Blomfield (Co-founder), TS Anil (CEO) |
| Contact | Contact information | contact@monzo.com |
| Source URL | Original discovery source | https://techcrunch.com/... |

### Data Quality

The final output undergoes rigorous validation and standardization:

- **Consistent Formatting**: Standardized date formats, location names, and industry terms
- **Validated URLs**: Properly formatted and verified website and LinkedIn URLs
- **Normalized Company Names**: Consistent capitalization and legal entity handling
- **Structured Information**: Well-organized data fields with appropriate content

## Testing Framework

The project includes a comprehensive test suite in the `tests/` directory, organized into logical components:

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run a specific test
python run_tests.py test_enhanced_crawler

# Run tests for a specific component
python run_tests.py crawler
```

### Test Organization

The test suite is structured to match the application architecture:

#### Crawler Tests (`tests/crawler/`)
- **Enhanced Crawler**: Tests for Jina-inspired techniques
- **Parallel Processing**: Validates multi-threaded data collection
- **URL Normalization**: Ensures proper URL handling and deduplication
- **Startup Discovery**: Tests the LLM-based name identification and validation process
- **Data Enrichment**: Validates the information gathering process

#### Collector Tests (`tests/collector/`)
- **Query Expansion**: Tests the semantic query expansion functionality
- **Input Handling**: Validates different input methods and formats

#### Utility Tests (`tests/utils/`)
- **API Clients**: Tests for Google Search and Gemini API integration
- **Data Cleaning**: Validates normalization and standardization functions
- **Environment Setup**: Tests API key handling and configuration

## Technical Requirements

### Dependencies

The project relies on the following Python packages:

- **API Integration**
  - `google-api-python-client`: For Google Search API integration
  - `google-generativeai`: For Gemini AI model access
  - `python-dotenv`: For environment variable management

- **Web Processing**
  - `requests`: For HTTP requests and web page fetching
  - `beautifulsoup4`: For HTML parsing and data extraction
  - `lxml`: For advanced HTML/XML processing

- **Data Processing**
  - `pandas` (optional): For advanced data manipulation
  - `csv`: For CSV file handling (standard library)
  - `json`: For JSON processing (standard library)

### API Requirements

To use this tool, you'll need to obtain the following API keys:

1. **Google Gemini API Key**
   - Sign up at [Google AI Studio](https://ai.google.dev/)
   - Create a new API key
   - Provides access to Gemini 2.5 Flash and Pro models

2. **Google Custom Search API Key**
   - Sign up at [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the Custom Search API
   - Create API credentials

3. **Custom Search Engine ID**
   - Create a Custom Search Engine at [Programmable Search Engine](https://programmablesearchengine.google.com/)
   - Configure it to search the entire web
   - Copy the Search Engine ID (cx value)

4. **Google Drive API** (Optional, for cloud storage)
   - Sign up at [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the Google Drive API
   - Create OAuth 2.0 Client ID credentials
   - Download the credentials as JSON and save as `credentials.json`

The first three keys should be stored in your `.env` file as described in the Installation section.

### Google Drive Integration

The Startup Finder can automatically upload your CSV results to Google Drive, making it ideal for cloud deployments:

#### Setting Up Google Drive Integration

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Drive API

2. **Create OAuth Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app" as the application type
   - Download the JSON file and save it as `credentials.json` in your project directory

3. **Using Google Drive Upload**:
   - Command line: `python startup_finder.py --query "your query" --upload-to-drive`
   - Interactive mode: Select "y" when asked about uploading to Google Drive
   - First-time use: You'll be prompted to authorize the application in your browser

4. **Authentication Flow**:
   - On first run, a browser window will open asking you to log in to your Google account
   - Grant the requested permissions to the application
   - The authentication token will be saved for future use

5. **Cloud Deployment**:
   - When deploying to cloud services like Render.com, include your `credentials.json` file
   - For headless servers, you may need to pre-authenticate and include the token.json file

## License

MIT License
