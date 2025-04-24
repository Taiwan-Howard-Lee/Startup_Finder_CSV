#!/usr/bin/env python
"""
Test runner for the Startup Finder project.
"""

import os
import sys
import importlib
import argparse

def discover_tests():
    """Discover all test files in the tests directory and its subdirectories."""
    test_files = []

    # Check main tests directory
    for file in os.listdir('tests'):
        if file.startswith('test_') and file.endswith('.py'):
            test_files.append(file[:-3])  # Remove .py extension

    # Check subdirectories
    for subdir in ['crawler', 'collector', 'utils']:
        subdir_path = os.path.join('tests', subdir)
        if os.path.isdir(subdir_path):
            for file in os.listdir(subdir_path):
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(f"{subdir}.{file[:-3]}")  # Format as subdir.test_name

    return test_files

def run_test(test_name):
    """Run a specific test module."""
    try:
        # Import the test module
        module_name = f"tests.{test_name}"
        module = importlib.import_module(module_name)

        # If the module has a main function, run it
        if hasattr(module, 'main'):
            module.main()
        # Otherwise, run all functions that start with 'test_'
        else:
            for name in dir(module):
                if name.startswith('test_'):
                    func = getattr(module, name)
                    if callable(func):
                        print(f"Running {name}...")
                        func()

        print(f"✅ {test_name} completed successfully")
        return True
    except ModuleNotFoundError as e:
        # Try to find the module in subdirectories
        for subdir in ['crawler', 'collector', 'utils']:
            try:
                module_name = f"tests.{subdir}.{test_name}"
                module = importlib.import_module(module_name)

                # If the module has a main function, run it
                if hasattr(module, 'main'):
                    module.main()
                # Otherwise, run all functions that start with 'test_'
                else:
                    for name in dir(module):
                        if name.startswith('test_'):
                            func = getattr(module, name)
                            if callable(func):
                                print(f"Running {name}...")
                                func()

                print(f"✅ {subdir}.{test_name} completed successfully")
                return True
            except ModuleNotFoundError:
                continue

        print(f"❌ {test_name} failed: {e}")
        return False
    except Exception as e:
        print(f"❌ {test_name} failed: {e}")
        return False

def run_all_tests():
    """Run all tests in the tests directory."""
    test_files = discover_tests()

    # Skip utility scripts
    test_files = [f for f in test_files if not f.startswith('fix_') and f != 'temp_fix']

    print(f"Found {len(test_files)} test files")

    successful = 0
    failed = 0

    # Group tests by directory
    grouped_tests = {}
    for test_file in test_files:
        if '.' in test_file:
            directory = test_file.split('.', 1)[0]
            if directory not in grouped_tests:
                grouped_tests[directory] = []
            grouped_tests[directory].append(test_file)
        else:
            if 'root' not in grouped_tests:
                grouped_tests['root'] = []
            grouped_tests['root'].append(test_file)

    # Run tests by group
    for group, tests in grouped_tests.items():
        print(f"\n{'='*50}")
        print(f"Running tests in {group} directory...")
        print(f"{'='*50}")

        for test_file in tests:
            print(f"\n{'-'*50}")
            print(f"Running {test_file}...")
            print(f"{'-'*50}")

            if run_test(test_file):
                successful += 1
            else:
                failed += 1

    print(f"\n{'='*50}")
    print(f"Test Results: {successful} passed, {failed} failed")
    print(f"{'='*50}")

    return failed == 0

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Run tests for the Startup Finder project.')
    parser.add_argument('test', nargs='?', help='Specific test to run')
    args = parser.parse_args()

    if args.test:
        success = run_test(args.test)
    else:
        success = run_all_tests()

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
