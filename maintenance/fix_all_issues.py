"""
Script to fix all issues in crawler.py
"""

import re

# Read the file
with open('src/processor/crawler.py', 'r') as f:
    content = f.read()

# Fix all occurrences of the syntax error
content = content.replace('except Exception as e):', 'except Exception as e:')

# Fix indentation after except statements
pattern = r'except Exception as e:\n(\s+)(\S)'
replacement = r'except Exception as e:\n\1    \2'
content = re.sub(pattern, replacement, content)

# Write the fixed content back to the file
with open('src/processor/crawler.py', 'w') as f:
    f.write(content)

print("Fixed all issues in crawler.py")
