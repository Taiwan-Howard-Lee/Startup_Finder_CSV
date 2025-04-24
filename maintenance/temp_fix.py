"""
This is a temporary script to fix the indentation in crawler.py
"""

import re

# Read the original file
with open('src/processor/crawler.py', 'r') as f:
    content = f.read()

# Fix the indentation issues
content = re.sub(r'try:\n\s+# Try to find location', 'try:\n                # Try to find location', content)

# Fix other indentation issues
content = re.sub(r'except Exception as e:.*?\n\s+logger\.error', 'except Exception as e):\n                logger.error', content, flags=re.DOTALL)

# Remove the "Add to enriched results" section that's causing issues
content = re.sub(r'# Add to enriched results.*?return enriched_results', 'return merged_data', content, flags=re.DOTALL)

# Write the fixed content back to the file
with open('src/processor/crawler.py', 'w') as f:
    f.write(content)

print("Fixed indentation issues in crawler.py")
