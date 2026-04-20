#!/usr/bin/env python3
import re

with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Use regex to find jsonify calls with missing closing parens
# Pattern: jsonify({...}(  -> should be jsonify({...})
def fix_jsonify(text):
    # Find all jsonify calls
    result = []
    i = 0
    fixed_count = 0
    while i < len(text):
        idx = text.find('jsonify(', i)
        if idx == -1:
            result.append(text[i:])
            break
        result.append(text[i:idx])
        # Find the matching closing
        start = idx + 8  # after 'jsonify('
        paren_count = 1
        j = start
        while j < len(text) and paren_count > 0:
            if text[j] == '(':
                paren_count += 1
            elif text[j] == ')':
                paren_count -= 1
            j += 1
        # Check if there's an extra '(' right before the closing ')'
        if text[j-2] == '(':
            # Missing closing brace, fix it
            result.append(text[start:j-1])  # content without extra (
            result.append('})')  # close the dict and paren
            fixed_count += 1
        else:
            result.append(text[start:j])
        i = j
    
    return ''.join(result), fixed_count

new_content, count = fix_jsonify(content)
print(f'Fixed {count} issues')

with open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Written')
