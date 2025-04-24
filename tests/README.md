# Tests for Startup Finder

This directory contains all the test files for the Startup Finder project.

## Test Files

### Crawler Tests
- `test_enhanced_crawler.py`: Tests for the enhanced crawler with Jina-inspired techniques
- `test_improved_crawler.py`: Tests for the improved crawler with parallel processing
- `test_parallel_crawler.py`: Tests specifically for parallel processing capabilities
- `test_uk_startups.py`: Tests for finding decarbonisation startups in the UK
- `test_enrichment.py`: Tests for the enrichment phase of the crawler
- `test_two_phase_crawler.py`: Tests for the two-phase crawler approach
- `test_autoscraper.py`: Tests for the AutoScraper functionality

### API and LLM Tests
- `test_api_keys.py`: Tests for API key handling
- `test_llm_filtering.py`: Tests for LLM-based filtering of startup names
- `test_query_expander.py`: Tests for query expansion functionality

### Utility Scripts
- `fix_all_crawler.py`: Script to fix all issues in the crawler
- `fix_all_issues.py`: Script to fix all indentation issues
- `fix_crawler.py`: Script to fix the _enrich_single_startup method
- `fix_indentation.py`: Script to fix indentation issues
- `fix_syntax.py`: Script to fix syntax errors
- `temp_fix.py`: Temporary script to fix indentation

## Running Tests

To run a specific test, use:

```bash
python -m tests.test_name
```

For example:

```bash
python -m tests.test_enhanced_crawler
```

## Test Organization

The tests are organized to match the structure of the main code:
- Crawler tests test the functionality in `src/processor/crawler.py`
- API and LLM tests test the functionality in various API and LLM modules
