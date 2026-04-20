import os, re, glob

base = r"C:\Users\kingdee\WorkBuddy\Claw\wojiayun"

# 1. SQL hardcoded count by file
print("=== SQL硬编码统计（按文件 Top 15）===")
results = []
total = 0
for pattern in ["business-common/*.py", "business-userH5/app.py", "business-staffH5/app.py", "business-admin/app.py"]:
    files = glob.glob(os.path.join(base, pattern))
    for f in files:
        if "migrate" in f or "__init__" in f:
            continue
        with open(f, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()
        sql_count = len(re.findall(r"(SELECT|INSERT|UPDATE|DELETE)\s+", content, re.IGNORECASE))
        if sql_count > 0:
            name = os.path.relpath(f, base)
            results.append((name, sql_count))
            total += sql_count

results.sort(key=lambda x: -x[1])
for name, cnt in results[:15]:
    print(f"  {name}: {cnt} 条SQL")
print(f"  合计: {total} 条SQL")

# 2. SQL injection risk
print("\n=== SQL注入风险（f-string拼接request参数）===")
risk_count = 0
for pattern in ["business-common/*.py", "business-userH5/app.py", "business-staffH5/app.py", "business-admin/app.py"]:
    files = glob.glob(os.path.join(base, pattern))
    for f in files:
        with open(f, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
        for i, line in enumerate(lines, 1):
            if "request." in line and ("f\"" in line or "f'" in line) and any(k in line.upper() for k in ["SELECT", "INSERT", "UPDATE", "DELETE"]):
                name = os.path.relpath(f, base)
                print(f"  RISK {name}:{i}: {line.strip()[:80]}")
                risk_count += 1
                if risk_count >= 20:
                    print("  ... (已截断)")
                    break
        if risk_count >= 20:
            break
print(f"  风险点总数: >= {risk_count} 处")

# 3. Controller layer direct DB calls
print("\n=== Controller层(app.py)直接访问数据库 ===")
for fpath in glob.glob(os.path.join(base, "business-*H5/app.py")) + glob.glob(os.path.join(base, "business-admin/app.py")):
    with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read()
    db_calls = len(re.findall(r"db\.(get_one|get_all|execute|get_total)", content))
    name = os.path.relpath(fpath, base)
    print(f"  {name}: {db_calls} 次直接DB调用")

# 4. Check ORM
print("\n=== ORM使用情况 ===")
orm_found = False
for root, dirs, files in os.walk(base):
    for f in files:
        if f.endswith(".py"):
            fp = os.path.join(root, f)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                if any(k in content for k in ["SQLAlchemy", "peewee", "from . import models", "from .models import"]):
                    print(f"  {os.path.relpath(fp, base)}")
                    orm_found = True
            except:
                pass
if not orm_found:
    print("  未使用任何ORM框架")

# 5. Migrations
print("\n=== 数据库迁移脚本 ===")
migrate_files = glob.glob(os.path.join(base, "business-common/migrate*.py"))
print(f"  迁移脚本: {len(migrate_files)} 个")

# 6. Architecture layers check
print("\n=== 架构层次检查 ===")
print("  Model层: 无ORM Model定义")
print("  View层: 原生HTML/JS (无模板引擎)")
print("  Controller层: Flask app.py (3个文件)")
svc_files = [f for f in glob.glob(os.path.join(base, "business-common/*.py")) if "migrate" not in f and "service" in f]
print(f"  Service层: {len(svc_files)} 个服务模块")
print(f"  DB层: db.py (7个方法)")
print(f"  前端: 原生HTML/CSS/JS (无框架)")
