#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import re

filename = '/www/wwwroot/wojiayun/business-admin/app.py'

with open(filename, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix all f-strings in logging.warning
# Pattern: logging.warning(f"...{var}...")
pattern = r'logging\.warning\(f"([^"]*):\s*\{([^}]+)\}"\)'
replacement = r'logging.warning("\1: %s", \2)'

content = re.sub(pattern, replacement, content)

# Also fix other f-string patterns
# Pattern: f"...{var}..."
content = re.sub(r'f"([^"]*\{[^}]+\}[^"]*)"', r'"\1"', content)

with open(filename, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed f-strings in logging.warning")
