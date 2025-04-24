# Startup Intelligence Finder - Project Plan

## Project Overview
Building a developer-friendly tool that uses AI (Google's Gemini API and Google Search API) to find and analyze startup companies using natural language queries.

### Data Collection Strategy
The project implements a two-phase data collection approach:
1. **Phase 1 (Discovery)**: Initial crawling and search to identify relevant startup names based on user queries
2. **Phase 2 (Enrichment)**: Using the discovered startup names as specific queries to gather detailed information about each company

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
- [ ] Create ranker.py
  - [ ] Implement scoring algorithm
  - [ ] Add result sorting

### Phase 4: Configuration Files
- [ ] Create default_fields.json
  - [ ] Define default search fields
- [ ] Create api_config.py
  - [ ] Set up API configuration options

### Phase 5: Main Class Implementation
- [ ] Create startup_finder.py
  - [ ] Implement StartupFinder class
  - [ ] Add search method
  - [ ] Add export functionality

### Phase 6: Testing
- [ ] Create test_collector.py
  - [ ] Test input handling
  - [ ] Test query expansion
- [ ] Create test_processor.py
  - [ ] Test data collection
  - [ ] Test result ranking
- [ ] Add integration tests

### Phase 7: Documentation
- [ ] Create usage examples
- [ ] Add docstrings to all functions
- [ ] Create API documentation

### Phase 8: Output Formatting
- [ ] Implement CSV export
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
1. Implement the two-phase crawling strategy
   - First phase: Gather startup names from search results
   - Second phase: Use startup names to query for detailed information
2. Complete the ranker implementation
3. Develop the main StartupFinder class
4. Create comprehensive tests
