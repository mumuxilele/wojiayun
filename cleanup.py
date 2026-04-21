# Final cleanup - 只删除空try-except
with open(r'C:\Users\kingdee\WorkBuddy\Claw\wojiayun\business-userH5\app.py', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# 删除简单的空 try 块（只有logging的）
content = content.replace('try:\n        pass\nexcept', 'except')
content = content.replace('try:\n            pass\nexcept', 'except')
content = content.replace('try:\n        pass\n    except', 'except')
content = content.replace('try:\n            pass\n        except', 'except')

# 删除单个 except pass
content = content.replace('\n        except:\n            pass\n', '\n')
content = content.replace('\n    except:\n        pass\n', '\n')

# 减少连续空行
import re
content = re.sub(r'\n\n\n+', '\n\n', content)

# 删除多余的空格
content = re.sub(r'    +', '    ', content)
content = re.sub(r'\t+', '\t', content)

with open(r'C:\Users\kingdee\WorkBuddy\Claw\wojiayun\business-userH5\app.py', 'w', encoding='utf-8') as f:
    f.write(content)

# 统计
with open(r'C:\Users\kingdee\WorkBuddy\Claw\wojiayun\business-userH5\app.py', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

total_lines = len(lines)
db_calls = sum(1 for l in lines if 'db.' in l and any(x in l for x in ['get_one', 'get_all', 'execute', 'get_total']))
func_count = len([l for l in lines if l.startswith('def ')])

print(f'Total lines: {total_lines}')
print(f'Functions: {func_count}')
print(f'DB calls: {db_calls}')
print(f'Reduction from 199: {199 - db_calls} ({(199-db_calls)*100//199}%)')
print('Done.')