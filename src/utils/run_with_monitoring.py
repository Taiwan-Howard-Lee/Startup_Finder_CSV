#!/usr/bin/env python3
"""
Run Startup Finder with monitoring and real-time optimization.

This script runs the Startup Finder with process monitoring and implements
real-time optimizations based on detected bottlenecks.
"""

import os
import sys
import time
import argparse
import logging
import signal
import json
from typing import Dict, Any, List, Optional

# Import startup_finder
import sys
import os

# Add the root directory to the path to import startup_finder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import startup_finder

# Import utility modules
from .process_monitor import process_monitor, start_monitoring
from .optimization_utils import ParallelProcessor, cache_manager
from .database_manager import DatabaseManager

# Set up logging
# Get the root directory path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
log_dir = os.path.join(root_dir, "output/logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, f"optimized_run_{time.strftime('%Y%m%d_%H%M%S')}.log"))
    ]
)
logger = logging.getLogger(__name__)

# Global variables for optimization
optimization_state = {
    "max_workers": None,
    "batch_size": None,
    "chunk_size": None,
    "paused": False,
    "early_stop": False,
    "current_phase": "initialization",
    "optimization_applied": []
}

# Initialize database manager
db_manager = DatabaseManager()

def optimize_based_on_bottlenecks():
    """Apply optimizations based on detected bottlenecks."""
    bottlenecks = process_monitor.bottlenecks
    suggestions = process_monitor.optimization_suggestions

    if not bottlenecks:
        return

    current_phase = process_monitor.current_phase
    optimization_applied = False

    for bottleneck, value in bottlenecks:
        if bottleneck == "CPU" and value > 90:
            # Reduce parallel processes
            if optimization_state["max_workers"] is None:
                optimization_state["max_workers"] = ParallelProcessor.get_optimal_workers()

            new_workers = max(2, optimization_state["max_workers"] // 2)
            ParallelProcessor.get_optimal_workers = lambda: new_workers

            logger.warning(f"OPTIMIZATION: Reducing parallel workers to {new_workers} due to high CPU usage")
            optimization_applied = True
            optimization_state["optimization_applied"].append(f"Reduced workers to {new_workers}")

        elif bottleneck == "Memory" and value > 80:
            # Enable more aggressive garbage collection
            import gc
            gc.collect()

            # Reduce batch size
            if current_phase in ["crawling", "enrichment", "validation"]:
                if optimization_state["batch_size"] is None:
                    optimization_state["batch_size"] = 10  # Default batch size

                new_batch_size = max(1, optimization_state["batch_size"] // 2)
                optimization_state["batch_size"] = new_batch_size

                logger.warning(f"OPTIMIZATION: Reducing batch size to {new_batch_size} due to high memory usage")
                optimization_applied = True
                optimization_state["optimization_applied"].append(f"Reduced batch size to {new_batch_size}")

        elif bottleneck == "Network I/O" and value < 50 * 1024 and current_phase in ["crawling", "enrichment"]:
            # Increase parallel requests
            if optimization_state["max_workers"] is None:
                optimization_state["max_workers"] = ParallelProcessor.get_optimal_workers()

            new_workers = min(32, optimization_state["max_workers"] * 2)
            ParallelProcessor.get_optimal_workers = lambda: new_workers

            logger.warning(f"OPTIMIZATION: Increasing parallel workers to {new_workers} due to low network activity")
            optimization_applied = True
            optimization_state["optimization_applied"].append(f"Increased workers to {new_workers}")

    return optimization_applied

def signal_handler(sig, frame):
    """Handle interrupt signals."""
    if optimization_state["paused"]:
        logger.info("Resuming process...")
        optimization_state["paused"] = False
    else:
        logger.info("Pausing process... Press Ctrl+C again to resume or Ctrl+D to exit")
        optimization_state["paused"] = True

        # Print optimization suggestions
        print("\n=== OPTIMIZATION SUGGESTIONS ===")
        for suggestion in process_monitor.optimization_suggestions:
            print(f"- {suggestion}")

        # Print optimization state
        print("\n=== OPTIMIZATION STATE ===")
        for key, value in optimization_state.items():
            if key != "optimization_applied":
                print(f"- {key}: {value}")

        # Print applied optimizations
        print("\n=== APPLIED OPTIMIZATIONS ===")
        for optimization in optimization_state["optimization_applied"]:
            print(f"- {optimization}")

        print("\nOptions:")
        print("1. Resume process (press Ctrl+C again)")
        print("2. Apply suggested optimizations (enter 'o')")
        print("3. Early stop and save results (enter 's')")
        print("4. Exit without saving (enter 'q')")

        # Wait for user input
        try:
            choice = input("Enter choice: ").strip().lower()

            if choice == 'o':
                # Apply suggested optimizations
                optimize_based_on_bottlenecks()
                optimization_state["paused"] = False
            elif choice == 's':
                # Early stop and save results
                optimization_state["early_stop"] = True
                optimization_state["paused"] = False
            elif choice == 'q':
                # Exit without saving
                print("Exiting...")
                sys.exit(0)
            else:
                # Resume
                optimization_state["paused"] = False

        except EOFError:
            # Exit on Ctrl+D
            print("\nExiting...")
            sys.exit(0)

def run_with_monitoring(args):
    """Run Startup Finder with monitoring and real-time optimization."""
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Start monitoring
    monitor = start_monitoring()

    try:
        # Parse arguments
        if isinstance(args, argparse.Namespace):
            parsed_args = args
        else:
            # Use the existing argument parser from startup_finder
            parser = argparse.ArgumentParser(description="Run Startup Finder with monitoring")
            parser.add_argument("--mode", type=str, choices=["find", "enrich", "both"], default="both",
                            help="Operation mode: find startups, enrich existing data, or both (default: both)")
            parser.add_argument("--query", "-q", type=str,
                            help="Search query to find startups (required for 'find' and 'both' modes)")
            parser.add_argument("--max-results", "-m", type=int, default=10,
                            help="Maximum number of search results per query (default: 10)")
            parser.add_argument("--num-expansions", "-n", type=int, default=5,
                            help="Number of query expansions to generate (1-100, default: 5)")
            parser.add_argument("--input-file", "-i", type=str,
                            help="Path to input CSV file with startup names (required for 'enrich' mode)")
            parser.add_argument("--output-file", "-o", type=str,
                            help="Path to the output CSV file (default: output/data/startups_TIMESTAMP.csv)")
            parser.add_argument("--no-expansion", action="store_true",
                            help="Disable query expansion")
            parser.add_argument("--startups", "-s", type=str, nargs="+",
                            help="List of startup names to directly search for (for 'both' mode)")
            parser.add_argument("--startups-file", "-f", type=str,
                            help="Path to a file containing startup names, one per line (for 'both' mode)")
            parser.add_argument("--batch-size", "-b", type=int, default=500,
                            help="Number of URLs to process in each batch (default: 500)")
            parser.add_argument("--resume", "-r", type=str,
                            help="Resume from a specific intermediate results file")
            parser.add_argument("--resume-phase", type=str, choices=["discovery", "enrichment", "validation"],
                            help="Resume from the latest checkpoint of a specific phase")
            parser.add_argument("--resume-latest", action="store_true",
                            help="Resume from the latest available checkpoint")
            parser.add_argument("--early-stop", action="store_true",
                            help="Enable early stopping when sufficient results are found")
            parser.add_argument("--optimize", action="store_true",
                            help="Enable automatic optimization")

            parsed_args = parser.parse_args(args)

        # Run Startup Finder with monitoring
        logger.info("Starting Startup Finder with monitoring and real-time optimization")

        # Check if we have a saved session to resume
        latest_session = db_manager.get_latest_session()
        if latest_session and latest_session.get("status") != "completed":
            logger.info(f"Found incomplete session: {latest_session.get('session_id')}")
            print(f"Found incomplete session: {latest_session.get('session_id')}")
            print("Do you want to resume this session? (y/n)")

            choice = input().strip().lower()
            if choice == 'y':
                logger.info("Resuming session...")
                # Set resume flags
                parsed_args.resume_latest = True
            else:
                logger.info("Starting new session...")

        # Set the current phase
        if parsed_args.mode == "find":
            monitor.set_phase("query_expansion")
        elif parsed_args.mode == "enrich":
            monitor.set_phase("enrichment")
        else:  # both
            monitor.set_phase("query_expansion")

        # Get direct startups if provided
        direct_startups = None
        if parsed_args.startups:
            direct_startups = parsed_args.startups
        elif parsed_args.startups_file and parsed_args.mode != "enrich":
            try:
                with open(parsed_args.startups_file, 'r') as f:
                    direct_startups = [line.strip() for line in f if line.strip()]
                print(f"Loaded {len(direct_startups)} startup names from {parsed_args.startups_file}")
            except Exception as e:
                print(f"Error loading startups file: {e}")

        # Run the startup finder with monitoring
        while True:
            # Check if paused
            if optimization_state["paused"]:
                time.sleep(0.1)
                continue

            # Check if early stop requested
            if optimization_state["early_stop"]:
                logger.info("Early stop requested. Saving current results...")
                # Save current results
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                data_dir = os.path.join(root_dir, "output/data")
                os.makedirs(data_dir, exist_ok=True)
                early_stop_file = os.path.join(data_dir, f"startups_early_stop_{timestamp}.csv")
                # TODO: Implement early stop logic - save current results
                print(f"Early stop results saved to {early_stop_file}")
                break

            # Run the startup finder with the appropriate mode
            if parsed_args.resume or parsed_args.resume_phase or parsed_args.resume_latest:
                # Run in resume mode
                result = startup_finder.run_startup_finder(
                    mode=parsed_args.mode,
                    query=parsed_args.query or "startup companies",  # Use a generic query if none provided
                    max_results=parsed_args.max_results,
                    num_expansions=parsed_args.num_expansions,
                    input_file=parsed_args.input_file,
                    output_file=parsed_args.output_file,
                    use_query_expansion=not parsed_args.no_expansion,
                    direct_startups=direct_startups,
                    resume_file=parsed_args.resume,
                    resume_phase=parsed_args.resume_phase,
                    resume_latest=parsed_args.resume_latest,
                    batch_size=parsed_args.batch_size
                )
            elif parsed_args.mode == "find" and parsed_args.query:
                # Run in find mode
                result = startup_finder.run_startup_finder(
                    mode="find",
                    query=parsed_args.query,
                    max_results=parsed_args.max_results,
                    num_expansions=parsed_args.num_expansions,
                    output_file=parsed_args.output_file,
                    use_query_expansion=not parsed_args.no_expansion,
                    batch_size=parsed_args.batch_size
                )
            elif parsed_args.mode == "enrich" and parsed_args.input_file:
                # Run in enrich mode
                result = startup_finder.run_startup_finder(
                    mode="enrich",
                    input_file=parsed_args.input_file,
                    output_file=parsed_args.output_file,
                    batch_size=parsed_args.batch_size
                )
            elif parsed_args.mode == "both" and (parsed_args.query or direct_startups):
                # Run in both mode
                query = parsed_args.query or "startup companies"  # Generic query if only direct startups provided
                result = startup_finder.run_startup_finder(
                    mode="both",
                    query=query,
                    max_results=parsed_args.max_results,
                    num_expansions=parsed_args.num_expansions,
                    output_file=parsed_args.output_file,
                    use_query_expansion=not parsed_args.no_expansion,
                    direct_startups=direct_startups,
                    batch_size=parsed_args.batch_size
                )
            else:
                # Run in interactive mode
                result = startup_finder.interactive_mode()

            break

        # Stop monitoring
        monitor.stop()

        # Get monitoring summary
        summary = monitor.get_summary()

        # Save monitoring summary
        reports_dir = os.path.join(root_dir, "output/reports")
        os.makedirs(reports_dir, exist_ok=True)
        summary_file = os.path.join(reports_dir, f"monitoring_summary_{time.strftime('%Y%m%d_%H%M%S')}.json")

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Monitoring summary saved to {summary_file}")
        print(f"\nMonitoring summary saved to {summary_file}")

        # Print optimization summary
        print("\n=== OPTIMIZATION SUMMARY ===")
        print(f"Total elapsed time: {summary['elapsed_time']:.2f} seconds")
        print(f"Average CPU usage: {summary['avg_cpu_percent']:.1f}%")
        print(f"Average memory usage: {summary['avg_memory_percent']:.1f}%")

        print("\nPhase durations:")
        for phase, duration in summary['phase_durations'].items():
            print(f"- {phase}: {duration:.2f} seconds")

        print("\nApplied optimizations:")
        if optimization_state["optimization_applied"]:
            for optimization in optimization_state["optimization_applied"]:
                print(f"- {optimization}")
        else:
            print("- No optimizations were applied")

        return result

    except Exception as e:
        logger.error(f"Error in run_with_monitoring: {e}")
        monitor.stop()
        raise

if __name__ == "__main__":
    run_with_monitoring(sys.argv[1:])
