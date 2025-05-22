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
    Export consolidated reports: one for startup data, one for all metrics, and one for context.

    This function generates three CSV files:
    1. A final startup list CSV with all the enriched data
    2. A comprehensive metrics report CSV with all metrics and debugging information
    3. A context report with raw text and paragraphs where startups were mentioned

    Args:
        metrics_collector: The metrics collector instance.
        base_filename: Base filename for the reports.

    Returns:
        Dictionary of filenames for the reports.
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    os.makedirs("output/reports", exist_ok=True)

    report_files = {}

    # 1. Export the final startup list with all enriched data
    startup_data_file = f"output/reports/{base_filename}_startups_{timestamp}.csv"

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
    metrics_file = f"output/reports/{base_filename}_metrics_{timestamp}.csv"

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

        # We no longer track blocked URLs separately

        # Failed URLs
        for url in metrics_collector.failed_urls:
            writer.writerow([url, 'Failed', 'N/A'])

        writer.writerow([])  # Empty row as separator

        # SECTION 4: Query to startup mapping
        writer.writerow(['=== QUERY TO STARTUP MAPPING ==='])
        writer.writerow(['Query', 'Startups Found'])

        for query, startups in metrics_collector.query_startup_map.items():
            writer.writerow([query, ', '.join(sorted(startups))])

        writer.writerow([])  # Empty row as separator

        # SECTION 5: Trend Analysis
        writer.writerow(['=== TREND ANALYSIS ==='])
        writer.writerow(['Startup Name', 'Total Mentions', 'First Mention', 'Last Mention', 'Daily Mention Pattern'])

        report = metrics_collector.report()
        trend_metrics = report.get('trend_metrics', {})

        for name, trend_data in sorted(trend_metrics.items()):
            daily_pattern = ', '.join([f"{day}: {count}" for day, count in trend_data.get('daily_mentions', {}).items()])
            writer.writerow([
                name,
                trend_data.get('total_mentions', 0),
                trend_data.get('first_mention', 'N/A'),
                trend_data.get('last_mention', 'N/A'),
                daily_pattern
            ])

        writer.writerow([])  # Empty row as separator

        # SECTION 6: Keyword Relevance
        writer.writerow(['=== KEYWORD RELEVANCE ==='])
        writer.writerow(['Startup Name', 'Top Keywords', 'Keyword Count'])

        keyword_metrics = report.get('keyword_metrics', {})

        for name, keyword_data in sorted(keyword_metrics.items()):
            top_keywords = ', '.join([f"{kw} ({score:.2f})" for kw, score in keyword_data.get('top_keywords', {}).items()])
            writer.writerow([
                name,
                top_keywords,
                keyword_data.get('keyword_count', 0)
            ])

        writer.writerow([])  # Empty row as separator

        # Funding Information section has been removed

    report_files['metrics'] = metrics_file

    # 3. Export a context report with raw text and paragraphs where startups were mentioned
    context_file = f"output/reports/{base_filename}_context_{timestamp}.csv"

    with open(context_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header row
        writer.writerow(['Startup Name', 'Source URL', 'Context (Paragraph with Mention)', 'Top Keywords', 'Industry Trends'])

        # Get report data
        report = metrics_collector.report()
        keyword_metrics = report.get('keyword_metrics', {})

        # Write context data for each startup
        for name in sorted(metrics_collector.final_startup_names):
            # Get all URLs where this startup was mentioned
            urls = set()
            for url, startups in metrics_collector.startups_by_source.items():
                if name in startups:
                    urls.add(url)

            # Get keyword information
            keyword_info = "No keyword data available"
            if name in keyword_metrics:
                top_keywords = keyword_metrics[name].get('top_keywords', {})
                if top_keywords:
                    keyword_info = ', '.join([f"{kw} ({score:.2f})" for kw, score in top_keywords.items()])

            # Funding information has been removed

            # Get industry trends
            industry_trends = "No trend data available"
            if name in report.get('trend_metrics', {}):
                trend_data = report['trend_metrics'][name]
                industry_trends = f"Total mentions: {trend_data.get('total_mentions', 0)}, First mention: {trend_data.get('first_mention', 'N/A')}, Last mention: {trend_data.get('last_mention', 'N/A')}"

            # For each URL, extract context
            for url in sorted(urls):
                contexts = metrics_collector.extract_context_for_startup(name, url)

                if contexts:
                    # Write each context as a separate row
                    for context in contexts:
                        writer.writerow([name, url, context, keyword_info, industry_trends])
                else:
                    # If no specific context found, note that
                    writer.writerow([name, url, "No specific context found", keyword_info, industry_trends])

    report_files['context'] = context_file

    print(f"\nGenerated consolidated reports:")
    print(f"1. Startup data: {startup_data_file}")
    print(f"2. Metrics report: {metrics_file}")
    print(f"3. Context report: {context_file}")

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
    print(f"Processed: {report['url_metrics']['processed']} ({report['url_metrics']['success_rate']:.1f}%)")
    print(f"Failed: {report['url_metrics']['failed']}")

    # Print startup metrics
    print("\nSTARTUP METRICS:")
    print(f"Potential startups found: {report['startup_metrics']['potential_found']}")
    print(f"After LLM extraction: {report['startup_metrics']['after_llm_extraction']}")
    print(f"After validation: {report['startup_metrics']['after_validation']}")
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

    # Print trend metrics
    print("\nTREND METRICS:")
    trend_metrics = report.get('trend_metrics', {})
    if trend_metrics:
        for name, trend_data in sorted(trend_metrics.items())[:5]:  # Show top 5
            print(f"{name}: {trend_data.get('total_mentions', 0)} mentions, first: {trend_data.get('first_mention', 'N/A')}, last: {trend_data.get('last_mention', 'N/A')}")
    else:
        print("No trend data available")

    # Print keyword metrics
    print("\nKEYWORD METRICS:")
    keyword_metrics = report.get('keyword_metrics', {})
    if keyword_metrics:
        for name, keyword_data in sorted(keyword_metrics.items())[:5]:  # Show top 5
            top_keywords = ', '.join([f"{kw} ({score:.2f})" for kw, score in keyword_data.get('top_keywords', {}).items()][:3])
            print(f"{name}: {top_keywords}")
    else:
        print("No keyword data available")

    # Funding metrics section has been removed

    print("\n" + "=" * 80)
