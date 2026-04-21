import re, os
BASE = r'C:\Users\kingdee\WorkBuddy\Claw\wojiayun'

for name in ['userH5', 'staffH5', 'admin']:
    path = os.path.join(BASE, f'business-{name}', 'app.py')
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    before = len(re.findall(r'db\.(get_one|get_all|execute|get_total)', content))
    
    # Simple cleanup
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r'except:\s+pass', 'except: pass', content)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    after = len(re.findall(r'db\.(get_one|get_all|execute|get_total)', content))
    print(f'{name}: {before} -> {after}')
