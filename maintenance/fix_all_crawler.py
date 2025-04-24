"""
Script to fix all indentation issues in crawler.py
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

# Fix the break statement outside of a loop
content = content.replace('                break\n\n        logger.info', '        logger.info')

# Fix indentation in the extract_startup_names method
content = content.replace('        except Exception as e:\n                    logger.error', '        except Exception as e:\n            logger.error')

# Fix indentation in the validate_startup_names method
content = content.replace('        except Exception as e:\n                    logger.error(f"Error validating startup names with Gemini: {e}")', '        except Exception as e:\n            logger.error(f"Error validating startup names with Gemini: {e}")')

# Fix indentation in the filter_relevant_startups method
content = content.replace('        except Exception as e:\n                    logger.error(f"Error filtering relevant startups with Gemini Pro: {e}")', '        except Exception as e:\n            logger.error(f"Error filtering relevant startups with Gemini Pro: {e}")')

# Fix indentation in the fetch_webpage method
content = content.replace('        except Exception as e:\n                    logger.error(f"Error fetching webpage {url}: {e}")', '        except Exception as e:\n            logger.error(f"Error fetching webpage {url}: {e}")')

# Write the fixed content back to the file
with open('src/processor/crawler.py', 'w') as f:
    f.write(content)

print("Fixed all indentation issues in crawler.py")
