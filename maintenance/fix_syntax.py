"""
Script to fix syntax errors in crawler.py
"""

# Read the file
with open('src/processor/crawler.py', 'r') as f:
    content = f.read()

# Fix all occurrences of the syntax error
fixed_content = content.replace('except Exception as e):', 'except Exception as e:')

# Write the fixed content back to the file
with open('src/processor/crawler.py', 'w') as f:
    f.write(fixed_content)

print("Fixed all syntax errors in crawler.py")
