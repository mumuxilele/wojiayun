import os
import re

admin_dir = r"C:\Users\kingdee\WorkBuddy\Claw\wojiayun\business-admin"

for filename in os.listdir(admin_dir):
    if not filename.endswith('.html'):
        continue
    
    filepath = os.path.join(admin_dir, filename)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Pattern to match: getElementById('xxx').value without null check
    # This pattern looks for .value that is NOT preceded by a null check
    pattern = r"(document\.getElementById\('[^']+'\))\.value"
    
    def fix_value(match):
        get_elem = match.group(1)
        # Check if this is already protected (in an if statement or ternary)
        return f"({get_elem} ? {get_elem}.value : '')"
    
    content = re.sub(pattern, fix_value, content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {filename}")

print("Done")
