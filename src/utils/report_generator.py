"""
Report generator for Startup Finder metrics.
"""

import os
import time
import csv
import json
from typing import Dict, List, Any, Optional

from src.utils.metrics_collector import MetricsCollector

def export_detailed_reports(metrics_collector: MetricsCollector, base_filename: str = "startup_finder_report"):
    """
    Export detailed reports including metrics and startup names at each stage.

    This function is kept for backward compatibility but now calls export_consolidated_reports
    which generates just two CSV files instead of multiple separate files.

    Args:
        metrics_collector: The metrics collector instance.
        base_filename: Base filename for the reports.

    Returns:
        Dictionary of filenames for each report.
    """
    # Call the new consolidated export function
    return export_consolidated_reports(metrics_collector, base_filename)


def export_consolidated_reports(metrics_collector: MetricsCollector, base_filename: str = "startup_finder_report"):
    """
    Export consolidated reports: one for startup data and one for all metrics.

    This function generates just two CSV files:
    1. A final startup list CSV with all the enriched data
    2. A comprehensive metrics report CSV with all metrics and debugging information

    Args:
        metrics_collector: The metrics collector instance.
        base_filename: Base filename for the reports.

    Returns:
        Dictionary of filenames for the two reports.
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    os.makedirs("reports", exist_ok=True)

    report_files = {}

    # 1. Export the final startup list with all enriched data
    startup_data_file = f"reports/{base_filename}_startups_{timestamp}.csv"

    # Get all possible fields
    all_fields = set()
    for field_dict in metrics_collector.field_values.values():
        all_fields.update(field_dict.keys())

    with open(startup_data_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header row with all fields
        header = ['Startup Name'] + sorted(all_fields)
        writer.writerow(header)

        # Write data for each startup
        for name in sorted(metrics_collector.final_startup_names):
            row = [name]
            field_data = metrics_collector.field_values.get(name, {})

            for field in sorted(all_fields):
                row.append(field_data.get(field, ''))

            writer.writerow(row)

    report_files['startups'] = startup_data_file

    # 2. Export a comprehensive metrics report with all debugging information
    metrics_file = f"reports/{base_filename}_metrics_{timestamp}.csv"

    with open(metrics_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # SECTION 1: Summary metrics
        writer.writerow(['=== SUMMARY METRICS ==='])
        writer.writerow(['Category', 'Metric', 'Value'])

        report = metrics_collector.report()
        for category, metrics in report.items():
            if isinstance(metrics, dict):
                for metric, value in metrics.items():
                    writer.writerow([category, metric, value])
            else:
                writer.writerow([category, category, metrics])

        writer.writerow([])  # Empty row as separator

        # SECTION 2: Startup names at each stage
        writer.writerow(['=== STARTUP NAMES AT EACH STAGE ==='])

        stages = [
            ('Potential', metrics_collector.potential_startup_names),
            ('Pattern Extracted', metrics_collector.pattern_extracted_names),
            ('LLM Extracted', metrics_collector.llm_extracted_names),
            ('Validated', metrics_collector.validated_names),
            ('Eliminated', metrics_collector.eliminated_names),
            ('Final', metrics_collector.final_startup_names)
        ]

        # Create a table with all stages as columns
        all_names = set()
        for _, names in stages:
            all_names.update(names)

        # Write header row with stage names
        header_row = ['Startup Name'] + [stage[0] for stage in stages]
        writer.writerow(header_row)

        # Write data rows
        for name in sorted(all_names):
            row = [name]
            for _, names in stages:
                row.append('Yes' if name in names else 'No')
            writer.writerow(row)

        writer.writerow([])  # Empty row as separator

        # SECTION 3: URL processing details
        writer.writerow(['=== URL PROCESSING DETAILS ==='])
        writer.writerow(['URL', 'Status', 'Processing Time (s)'])

        # Processed URLs
        for url in metrics_collector.processed_urls:
            time_taken = metrics_collector.url_processing_time_map.get(url, "N/A")
            writer.writerow([url, 'Processed', time_taken])

        # Blocked URLs
        for url in metrics_collector.blocked_urls:
            writer.writerow([url, 'Blocked by robots.txt', 'N/A'])

        # Failed URLs
        for url in metrics_collector.failed_urls:
            writer.writerow([url, 'Failed', 'N/A'])

        writer.writerow([])  # Empty row as separator

        # SECTION 4: Query to startup mapping
        writer.writerow(['=== QUERY TO STARTUP MAPPING ==='])
        writer.writerow(['Query', 'Startups Found'])

        for query, startups in metrics_collector.query_startup_map.items():
            writer.writerow([query, ', '.join(sorted(startups))])

    report_files['metrics'] = metrics_file

    print(f"\nGenerated consolidated reports:")
    print(f"1. Startup data: {startup_data_file}")
    print(f"2. Metrics report: {metrics_file}")

    return report_files

def display_metrics_dashboard(metrics_collector: MetricsCollector):
    """Display a real-time metrics dashboard."""
    report = metrics_collector.report()

    # Clear the console
    os.system('cls' if os.name == 'nt' else 'clear')

    # Print header
    print("=" * 80)
    print("STARTUP FINDER METRICS DASHBOARD")
    print("=" * 80)

    # Print URL metrics
    print("\nURL METRICS:")
    print(f"Discovered: {report['url_metrics']['discovered']}")
    print(f"Processed: {report['url_metrics']['processed']} ({report['url_metrics']['success_rate']:.1f}%)")
    print(f"Blocked by robots.txt: {report['url_metrics']['blocked_by_robots']}")
    print(f"Skipped duplicates: {report['url_metrics']['skipped_duplicates']}")
    print(f"Failed: {report['url_metrics']['failed']}")
    print(f"Cache hits: {report['url_metrics']['cache_hits']} ({report['url_metrics']['cache_hit_rate']:.1f}%)")

    # Print startup metrics
    print("\nSTARTUP METRICS:")
    print(f"Potential startups found: {report['startup_metrics']['potential_found']}")
    print(f"After pattern extraction: {report['startup_metrics']['after_pattern_extraction']}")
    print(f"After LLM extraction: {report['startup_metrics']['after_llm_extraction']}")
    print(f"After validation: {report['startup_metrics']['after_validation']}")
    print(f"Eliminated: {report['startup_metrics']['eliminated']}")
    print(f"Final unique startups: {report['startup_metrics']['final_unique']}")
    print(f"Conversion rate: {report['startup_metrics']['conversion_rate']:.1f}%")

    # Print extraction metrics
    print("\nEXTRACTION METRICS:")
    print(f"Website success rate: {report['extraction_metrics']['website_success_rate']:.1f}%")
    print(f"LinkedIn success rate: {report['extraction_metrics']['linkedin_success_rate']:.1f}%")
    print(f"Crunchbase success rate: {report['extraction_metrics']['crunchbase_success_rate']:.1f}%")
    print(f"Fallback usages: {report['extraction_metrics']['fallback_usages']}")

    # Print field completion
    print("\nFIELD COMPLETION RATES:")
    for field, rate in report['field_completion'].items():
        print(f"{field}: {rate:.1f}%")

    # Print time metrics
    print("\nTIME METRICS:")
    print(f"Average URL processing time: {report['time_metrics']['avg_url_processing_time']:.2f}s")
    print(f"Average startup enrichment time: {report['time_metrics']['avg_startup_enrichment_time']:.2f}s")
    print(f"Total elapsed time: {report['elapsed_time']:.2f}s")

    # Print API metrics
    print("\nAPI METRICS:")
    print(f"Google API calls: {report['api_metrics']['google_api_calls']}")
    print(f"Gemini API calls: {report['api_metrics']['gemini_api_calls']}")

    print("\n" + "=" * 80)
