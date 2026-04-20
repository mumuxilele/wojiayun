#!/usr/bin/env python3
import re

with open('/www/wwwroot/wojiayun/business-userH5/app.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

# Find all function definitions with their line numbers
func_pattern = re.compile(r'^(\s*)def\s+(\w+)\s*\(')
funcs = {}
for i, line in enumerate(lines, 1):
    match = func_pattern.match(line)
    if match:
        indent = len(match.group(1))
        name = match.group(2)
        if name not in funcs:
            funcs[name] = []
        funcs[name].append((i, indent, line))

# Find duplicates
duplicates = {name: locs for name, locs in funcs.items() if len(locs) > 1}
print(f"Found {len(duplicates)} duplicate functions:")
for name, locs in duplicates.items():
    print(f"  {name}: lines {[l[0] for l in locs]}")

# Remove duplicates (keep first occurrence, remove others)
# Process in reverse order to keep line numbers valid
lines_to_remove = []
for name, locs in duplicates.items():
    # Keep the first one, mark others for removal
    for line_no, indent, line in locs[1:]:
        # Find where this function ends (next function at same or lower indent, or EOF)
        start_idx = line_no - 1
        end_idx = len(lines)
        for j in range(start_idx + 1, len(lines)):
            match = func_pattern.match(lines[j])
            if match:
                next_indent = len(match.group(1))
                if next_indent <= indent:
                    end_idx = j
                    break
        # Also remove preceding decorators
        dec_start = start_idx
        for j in range(start_idx - 1, max(0, start_idx - 10), -1):
            if lines[j].strip().startswith('@'):
                dec_start = j
            elif lines[j].strip() and not lines[j].strip().startswith('#'):
                break
        lines_to_remove.append((dec_start, end_idx, name))
        print(f"  Will remove {name} at lines {dec_start+1}-{end_idx}")

# Sort by start line in reverse order
lines_to_remove.sort(key=lambda x: x[0], reverse=True)

# Remove the lines
for start, end, name in lines_to_remove:
    del lines[start:end]
    print(f"Removed {name} (lines {start+1}-{end})")

# Write back
with open('/www/wwwroot/wojiayun/business-userH5/app.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"\nDone! Removed {len(lines_to_remove)} duplicate functions.")
print(f"File now has {len(lines)} lines.")
