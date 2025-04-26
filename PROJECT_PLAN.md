# Startup Intelligence Finder - Project Plan

## Project Overview
Building a developer-friendly tool that uses AI (Google's Gemini API and Google Search API) to find and analyze startup companies using natural language queries.

### Data Collection Strategy
The project implements a three-phase data processing approach:
1. **Phase 1 (Discovery)**: Initial crawling and search to identify relevant startup names based on user queries
2. **Phase 2 (Enrichment)**: Using the discovered startup names as specific queries to gather detailed information about each company
3. **Phase 3 (Validation)**: Using Gemini 2.5 Pro to validate and correct the collected data before final output

## Development Phases

### Phase 1: Project Setup
- [x] Create PROJECT_PLAN.md
- [x] Set up project directory structure
  - [x] src/
    - [x] collector/
    - [x] processor/
    - [x] utils/
  - [x] tests/
  - [x] config/
  - [x] examples/
- [x] Create virtual environment
- [x] Create requirements.txt with dependencies
- [x] Set up initial __init__.py files

### Phase 2: Environment Configuration
- [x] Create setup_env.py
  - [x] Add API key configuration for Gemini
  - [x] Add API key configuration for Google Search
  - [x] Add Custom Search Engine ID configuration
  - [x] Add dependency checking

### Phase 3: Core Components Development

#### Utils Module
- [x] Create api_client.py
  - [x] Implement Gemini API wrapper
  - [x] Add error handling
- [x] Create google_search_client.py
  - [x] Implement Google Search API wrapper
  - [x] Add web scraping functionality
- [x] Create data_cleaner.py
  - [x] Implement data normalization
  - [x] Add data validation

#### Collector Module
- [x] Create input_handler.py
  - [x] Implement query parsing
  - [x] Add field validation
- [x] Create query_expander.py
  - [x] Implement Gemini API integration
  - [x] Add query expansion logic

#### Processor Module
- [x] Create crawler.py
  - [x] Implement data source connectors
  - [x] Add data extraction logic
- [x] Implement two-phase crawling strategy
  - [x] Phase 1: Gather startup names from initial search
  - [x] Phase 2: Enrich data using startup names as queries
- [x] Create enhanced_crawler.py
  - [x] Implement Jina-inspired adaptive crawling techniques
  - [x] Add parallel processing for faster data collection
  - [x] Implement URL normalization to avoid duplicates
- [x] Create website_extractor.py
  - [x] Extract data from company websites
  - [x] Implement LLM-based data extraction
- [x] Create linkedin_extractor.py
  - [x] Extract data from LinkedIn company pages via Google Search
  - [x] Implement LLM-based data extraction

### Phase 4: Configuration Files
- [ ] Create default_fields.json
  - [ ] Define default search fields
- [ ] Create api_config.py
  - [ ] Set up API configuration options

### Phase 5: Main Class Implementation
- [x] Create startup_finder.py
  - [x] Implement main functionality
  - [x] Add search method with two-phase approach
  - [x] Add export functionality with CSV generation
  - [x] Implement command-line interface with multiple options
  - [x] Add interactive mode for user-friendly operation

### Phase 6: Testing
- [x] Create test directory structure
  - [x] tests/crawler/ for crawler component tests
  - [x] tests/collector/ for collector component tests
  - [x] tests/utils/ for utility component tests
- [x] Create run_tests.py for test execution
- [x] Implement test discovery and execution
- [~] Create test_collector.py (partially complete)
  - [~] Test input handling
  - [~] Test query expansion
- [~] Create test_processor.py (partially complete)
  - [~] Test data collection
  - [ ] Test result ranking
- [ ] Add integration tests

### Phase 7: Documentation
- [ ] Create usage examples
- [ ] Add docstrings to all functions
- [ ] Create API documentation

### Phase 8: Output Formatting
- [x] Implement CSV export
  - [x] Add customizable output file naming
  - [x] Include comprehensive startup data fields
  - [x] Add data validation with Gemini 2.5 Pro
- [ ] Implement JSON export
- [ ] Add confidence scores and metadata

## Dependencies
- Python 3.8+
- Google Cloud account with Gemini API access
- Google Search API key
- Custom Search Engine ID
- Required Python packages (to be listed in requirements.txt)

## Testing Strategy
- Unit tests for each module
- Integration tests for complete workflow
- Coverage target: 80%+

## Coding Standards
- Follow PEP 8
- Use type hints
- Add docstrings
- Keep functions focused

## Next Steps

### Immediate Priorities

1. **Enhance test coverage**
   - Complete tests for all components
   - Add integration tests for the full workflow
   - Implement test fixtures for consistent testing
   - Reach the target of 80%+ test coverage

2. **Improve documentation**
   - Add comprehensive docstrings to all functions
   - Create API documentation for developers
   - Add more usage examples
   - Document the data extraction process

### Future Enhancements
1. **Add JSON export functionality**
   - Implement JSON export with full metadata
   - Add confidence scores for extracted data
   - Include source attribution for each data point

2. **Improve data extraction**
   - Add more specialized extractors for different data sources
   - Enhance pattern recognition for specific data types
   - Implement more sophisticated validation of extracted data

3. **Performance optimization**
   - Further optimize parallel processing
   - Implement caching for frequently accessed data
   - Add resume capability for interrupted processes

4. **User interface improvements**
   - Add progress reporting during long-running operations
   - Implement a simple web interface
   - Add visualization of startup data
