#!/usr/bin/env python3
"""
Modify Startup Finder

This script modifies the Startup Finder to append intermediate results to a single CSV file
instead of creating multiple intermediate files.
"""

import os
import sys
import re
import logging
from typing import List, Dict, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_files_to_modify() -> List[str]:
    """
    Find files that need to be modified.
    
    Returns:
        List of file paths
    """
    files_to_modify = [
        "src/processor/enhanced_crawler.py",
        "src/processor/startup_processor.py",
        "startup_finder.py"
    ]
    
    # Check if files exist
    existing_files = []
    for file_path in files_to_modify:
        if os.path.exists(file_path):
            existing_files.append(file_path)
        else:
            logger.warning(f"File not found: {file_path}")
    
    return existing_files

def modify_enhanced_crawler(file_path: str) -> bool:
    """
    Modify the EnhancedStartupCrawler to use the CSV appender.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add import for CSV appender
        import_pattern = r"from src\.utils\.metrics_collector import MetricsCollector"
        import_replacement = "from src.utils.metrics_collector import MetricsCollector\nfrom src.utils.csv_appender import CSVAppender, create_csv_appender"
        
        if import_pattern in content:
            content = content.replace(import_pattern, import_replacement)
        else:
            # Add import at the top of the file
            import_section = "import os\nimport time\nimport logging\n"
            if import_section in content:
                content = content.replace(import_section, import_section + "from src.utils.csv_appender import CSVAppender, create_csv_appender\n")
        
        # Modify the constructor to add CSV appender
        init_pattern = r"def __init__\(self, google_search=None, web_crawler=None, metrics_collector=None\):"
        init_replacement = "def __init__(self, google_search=None, web_crawler=None, metrics_collector=None, csv_appender=None):"
        
        if init_pattern in content:
            content = content.replace(init_pattern, init_replacement)
        
        # Add CSV appender initialization
        init_body_pattern = r"self\.metrics_collector = metrics_collector"
        init_body_replacement = "self.metrics_collector = metrics_collector\n        self.csv_appender = csv_appender or create_csv_appender()"
        
        if init_body_pattern in content:
            content = content.replace(init_body_pattern, init_body_replacement)
        
        # Modify save_intermediate_results method
        save_pattern = r"def save_intermediate_results\(self, results: List\[Dict\[str, Any\]\], batch_info: str\) -> str:"
        save_replacement = "def save_intermediate_results(self, results: List[Dict[str, Any]], batch_info: str) -> str:"
        
        if save_pattern in content:
            # Find the method body
            method_start = content.find(save_pattern)
            if method_start >= 0:
                # Find the end of the method
                method_end = content.find("def ", method_start + 1)
                if method_end < 0:
                    method_end = len(content)
                
                # Extract the method body
                method_body = content[method_start:method_end]
                
                # Create the new method body
                new_method_body = f"""def save_intermediate_results(self, results: List[Dict[str, Any]], batch_info: str) -> str:
        \"\"\"
        Save intermediate results to a single CSV file.
        
        Args:
            results: List of result dictionaries
            batch_info: Batch information to add to the results
            
        Returns:
            Path to the output file
        \"\"\"
        if not results:
            logger.warning("No results to save")
            return ""
        
        # Append results to the CSV file
        if self.csv_appender:
            num_appended = self.csv_appender.append_results(results, batch_info)
            logger.info(f"Appended {num_appended} results to {self.csv_appender.output_file}")
            return self.csv_appender.output_file
        
        # Fall back to original implementation if no CSV appender
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = "output/intermediate"
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a unique filename
        filename = f"{batch_info}_{timestamp}.csv"
        output_file = os.path.join(output_dir, filename)
        
        # Write results to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if results:
                fieldnames = results[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
        
        logger.info(f"Saved {len(results)} results to {output_file}")
        return output_file"""
                
                # Replace the method body
                content = content.replace(method_body, new_method_body)
        
        # Write the modified content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Modified {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error modifying {file_path}: {e}")
        return False

def modify_startup_processor(file_path: str) -> bool:
    """
    Modify the StartupProcessor to use the CSV appender.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add import for CSV appender
        import_pattern = r"from src\.utils\.metrics_collector import MetricsCollector"
        import_replacement = "from src.utils.metrics_collector import MetricsCollector\nfrom src.utils.csv_appender import CSVAppender, create_csv_appender"
        
        if import_pattern in content:
            content = content.replace(import_pattern, import_replacement)
        else:
            # Add import at the top of the file
            import_section = "import os\nimport time\nimport logging\n"
            if import_section in content:
                content = content.replace(import_section, import_section + "from src.utils.csv_appender import CSVAppender, create_csv_appender\n")
        
        # Modify the constructor to add CSV appender
        init_pattern = r"def __init__\(self, crawler=None, metrics_collector=None\):"
        init_replacement = "def __init__(self, crawler=None, metrics_collector=None, csv_appender=None):"
        
        if init_pattern in content:
            content = content.replace(init_pattern, init_replacement)
        
        # Add CSV appender initialization
        init_body_pattern = r"self\.metrics_collector = metrics_collector"
        init_body_replacement = "self.metrics_collector = metrics_collector\n        self.csv_appender = csv_appender or create_csv_appender()"
        
        if init_body_pattern in content:
            content = content.replace(init_body_pattern, init_body_replacement)
        
        # Pass CSV appender to crawler
        crawler_init_pattern = r"self\.crawler = crawler or EnhancedStartupCrawler\(metrics_collector=metrics_collector\)"
        crawler_init_replacement = "self.crawler = crawler or EnhancedStartupCrawler(metrics_collector=metrics_collector, csv_appender=self.csv_appender)"
        
        if crawler_init_pattern in content:
            content = content.replace(crawler_init_pattern, crawler_init_replacement)
        
        # Write the modified content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Modified {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error modifying {file_path}: {e}")
        return False

def modify_startup_finder(file_path: str) -> bool:
    """
    Modify the main startup_finder.py file to use the CSV appender.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add import for CSV appender
        import_pattern = r"from src\.utils\.metrics_collector import MetricsCollector"
        import_replacement = "from src.utils.metrics_collector import MetricsCollector\nfrom src.utils.csv_appender import CSVAppender, create_csv_appender"
        
        if import_pattern in content:
            content = content.replace(import_pattern, import_replacement)
        else:
            # Add import at the top of the file
            import_section = "import os\nimport time\nimport logging\n"
            if import_section in content:
                content = content.replace(import_section, import_section + "from src.utils.csv_appender import CSVAppender, create_csv_appender\n")
        
        # Modify the run_startup_finder function to use CSV appender
        run_pattern = r"def run_startup_finder\("
        if run_pattern in content:
            # Find the function signature
            func_start = content.find(run_pattern)
            if func_start >= 0:
                # Find the end of the signature
                func_end = content.find(")", func_start)
                if func_end >= 0:
                    # Extract the signature
                    signature = content[func_start:func_end+1]
                    
                    # Add csv_appender parameter
                    if "csv_appender=None" not in signature:
                        new_signature = signature.replace(")", ", csv_appender=None)")
                        content = content.replace(signature, new_signature)
        
        # Modify the processor initialization to use CSV appender
        processor_init_pattern = r"processor = StartupProcessor\(metrics_collector=metrics_collector\)"
        processor_init_replacement = "# Create CSV appender if not provided\nif not csv_appender:\n        csv_appender = create_csv_appender(output_file)\n\n    processor = StartupProcessor(metrics_collector=metrics_collector, csv_appender=csv_appender)"
        
        if processor_init_pattern in content:
            content = content.replace(processor_init_pattern, processor_init_replacement)
        
        # Write the modified content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Modified {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error modifying {file_path}: {e}")
        return False

def main():
    """Main function to run the script."""
    print("\n=== MODIFYING STARTUP FINDER ===")
    print("This script will modify the Startup Finder to append intermediate results to a single CSV file.")
    print("The original files will be backed up before modification.")
    
    # Find files to modify
    files_to_modify = find_files_to_modify()
    
    if not files_to_modify:
        print("No files found to modify.")
        return 1
    
    print(f"\nFound {len(files_to_modify)} files to modify:")
    for file_path in files_to_modify:
        print(f"- {file_path}")
    
    # Confirm with user
    print("\nDo you want to proceed with the modification? (y/n)")
    choice = input().strip().lower()
    
    if choice != 'y':
        print("Modification cancelled.")
        return 0
    
    # Create backups
    for file_path in files_to_modify:
        backup_path = f"{file_path}.bak"
        try:
            with open(file_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            logger.info(f"Created backup: {backup_path}")
        except Exception as e:
            logger.error(f"Error creating backup for {file_path}: {e}")
            print(f"Error creating backup for {file_path}: {e}")
            return 1
    
    # Modify files
    success = True
    
    for file_path in files_to_modify:
        if "enhanced_crawler.py" in file_path:
            if not modify_enhanced_crawler(file_path):
                success = False
        elif "startup_processor.py" in file_path:
            if not modify_startup_processor(file_path):
                success = False
        elif "startup_finder.py" in file_path:
            if not modify_startup_finder(file_path):
                success = False
    
    if success:
        print("\nModification complete!")
        print("The Startup Finder now appends intermediate results to a single CSV file.")
        print("You can run the Startup Finder as usual, and all results will be appended to the same file.")
        return 0
    else:
        print("\nModification failed. See logs for details.")
        print("The original files have been backed up with .bak extension.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
