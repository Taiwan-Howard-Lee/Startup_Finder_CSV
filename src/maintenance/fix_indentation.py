"""
Script to fix indentation issues in crawler.py
"""

# Read the file
with open('src/processor/crawler.py', 'r') as f:
    lines = f.readlines()

# Fix indentation issues
fixed_lines = []
for i, line in enumerate(lines):
    # Fix the location_patterns indentation
    if i >= 830 and i <= 834 and line.startswith('                    '):
        fixed_lines.append(line.replace('                    ', '                '))
    # Fix the for pattern indentation
    elif i >= 836 and i <= 842 and line.startswith('                    '):
        fixed_lines.append(line.replace('                    ', '                '))
    # Fix the year_pattern indentation
    elif i >= 844 and i <= 850 and line.startswith('                    '):
        fixed_lines.append(line.replace('                    ', '                '))
    # Fix the website indentation
    elif i >= 852 and i <= 856 and line.startswith('                    '):
        fixed_lines.append(line.replace('                    ', '                '))
    # Fix the product description indentation
    elif i >= 858 and i <= 861 and line.startswith('                    '):
        fixed_lines.append(line.replace('                    ', '                '))
    # Fix the except line
    elif i == 863 and 'except Exception as e):' in line:
        fixed_lines.append('                except Exception as e:\n')
    # Fix the logger.error line
    elif i == 864 and line.startswith('                logger.error'):
        fixed_lines.append('                    logger.error(f"Error extracting data from {url}: {e}")\n')
    else:
        fixed_lines.append(line)

# Write the fixed content back to the file
with open('src/processor/crawler.py', 'w') as f:
    f.writelines(fixed_lines)

print("Fixed all indentation issues in crawler.py")
