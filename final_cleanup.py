"""
最终批量清理 - 所有三个 app.py
"""
import re, os

BASE = r'C:\Users\kingdee\WorkBuddy\Claw\wojiayun'

def clean_file(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    before = len(re.findall(r'db\.(get_one|get_all|execute|get_total)', content))
    lines_before = content.count('\n')
    
    # 1. 删除空的 try-except 块
    # Pattern: try: ... except Exception as e: logging.xxx(...) 
    content = re.sub(
        r'\n[ \t]+try:\s*\n([ \t]+[^\n]+\n)*[ \t]+except Exception as e:\s*\n[ \t]+logging\.\w+\([^\n]+\)\s*\n',
        '\n',
        content
    )
    
    # 2. 删除 except: pass
    content = re.sub(r'\n[ \t]+except:\s*\n[ \t]+pass\s*\n', '\n', content)
    content = re.sub(r'\n[ \t]+except Exception[^:]*:\s*\n[ \t]+pass\s*\n', '\n', content)
    
    # 3. 删除 finally: cursor.close(); conn.close()
    content = re.sub(
        r'\n[ \t]+finally:\s*\n[ \t]+try:\s*\n[ \t]+cursor\.close\(\)\s*\n[ \t]+conn\.close\(\)\s*\n[ \t]+except:\s*\n[ \t]+pass\s*\n',
        '\n',
        content
    )
    
    # 4. 简化 except return
    content = re.sub(
        r'except Exception as e:\s*\n[ \t]+logging\.\w+\(f?"[^"]*"\)\s*\n[ \t]+return jsonify\([^\n]+\)',
        'except: return jsonify({\'success\': False, \'msg\': \'操作失败\'})',
        content
    )
    
    # 5. 删除多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # 6. 简化 uid 赋值
    lines = content.split('\n')
    new_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 跳过单独的 uid = user['user_id'] 行
        if stripped == "uid = user['user_id']":
            continue
        # 跳过单独的 uid = user.get('user_id') 行
        if re.match(r"uid\s*=\s*user\['user_id'\]", stripped):
            continue
        new_lines.append(line)
    content = '\n'.join(new_lines)
    
    # 7. 替换 uid 为 user['user_id']
    content = re.sub(r'\buid\b', "user['user_id']", content)
    
    after = len(re.findall(r'db\.(get_one|get_all|execute|get_total)', content))
    lines_after = content.count('\n')
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return before, after, lines_before, lines_after

# 处理三个文件
results = {}
for name in ['userH5', 'staffH5', 'admin']:
    path = os.path.join(BASE, f'business-{name}', 'app.py')
    b, a, lb, la = clean_file(path)
    results[name] = {'before': b, 'after': a, 'lines_before': lb, 'lines_after': la}
    print(f'{name}: {b} -> {a} DB calls, {lb} -> {la} lines')

# 总结
total_before = sum(r['before'] for r in results.values())
total_after = sum(r['after'] for r in results.values())
print(f'\nTotal: {total_before} -> {total_after} DB calls (reduced {total_before - total_after})')
