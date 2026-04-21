"""
staffH5 和 admin 批量改造
"""
import re, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r'C:\Users\kingdee\WorkBuddy\Claw\wojiayun'

def count_db(content):
    return len(re.findall(r'db\.(get_one|get_all|execute|get_total)', content))

def refactor_file(path, label):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    before = count_db(content)
    
    # ---- 通用替换模式 ----
    
    # 1. 删除只有 logging 的 except 块
    content = re.sub(
        r'\s+except Exception as e:\s*\n\s+logging\.\w+\([^\n]+\)\s*\n',
        '\n', content
    )
    
    # 2. 简化 except pass
    content = re.sub(r'\s+except:\s*\n\s+pass\n', '\n', content)
    content = re.sub(r'\s+except Exception[^:]*:\s*\n\s+pass\n', '\n', content)
    
    # 3. 删除多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # 4. 简化 uid = user['user_id'] 后立即使用的情况
    # 把 uid = user['user_id']\n    xxx(uid) 合并
    content = re.sub(
        r"uid = user\['user_id'\]\s*\n(\s+)([^\n]+)\buid\b",
        lambda m: m.group(1) + m.group(2).replace('uid', "user['user_id']"),
        content
    )
    
    after = count_db(content)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'{label}: {before} → {after} DB calls (减少 {before-after})')
    return before, after

# ---- staffH5 专项改造 ----
def refactor_staffh5():
    path = os.path.join(BASE, 'business-staffH5', 'app.py')
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    before = count_db(content)
    
    # 1. 申请列表 - 使用 ApplicationService
    old = re.search(
        r'def get_applications\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_applications(user):
    """获取申请列表"""
    from business_common.application_service import ApplicationService
    status = request.args.get('status')
    type_code = request.args.get('type_code')
    keyword = request.args.get('keyword', '').strip()
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    result = ApplicationService.get_applications(
        ec_id=user.get('ec_id'), project_id=user.get('project_id'),
        status=status, type_code=type_code, keyword=keyword,
        page=page, page_size=page_size
    )
    return jsonify({'success': True, 'data': result})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('  staffH5: get_applications')
    
    # 2. 审批申请 - 使用 ApplicationService
    old = re.search(
        r'def approve_application\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def approve_application(user, app_id):
    """审批申请"""
    from business_common.application_service import ApplicationService
    data = request.get_json() or {}
    result = ApplicationService.approve_application(
        app_id=int(app_id),
        approver_id=user['user_id'],
        approver_name=user.get('user_name', ''),
        action=data.get('action', 'approve'),
        comment=data.get('comment', '').strip()
    )
    return jsonify(result)

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('  staffH5: approve_application')
    
    # 3. 订单列表 - 使用 OrderService
    old = re.search(
        r'def get_orders\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_orders(user):
    """获取订单列表"""
    from business_common.order_service import OrderService
    status = request.args.get('status')
    keyword = request.args.get('keyword', '').strip()
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    order_service = OrderService()
    result = order_service.get_orders(
        ec_id=user.get('ec_id'), project_id=user.get('project_id'),
        status=status, keyword=keyword, page=page, page_size=page_size
    )
    return jsonify({'success': True, 'data': result})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('  staffH5: get_orders')
    
    # 通用清理
    content = re.sub(r'\s+except Exception as e:\s*\n\s+logging\.\w+\([^\n]+\)\s*\n', '\n', content)
    content = re.sub(r'\s+except:\s*\n\s+pass\n', '\n', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    after = count_db(content)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  staffH5 总计: {before} → {after} (减少 {before-after})')
    return before, after

# ---- admin 专项改造 ----
def refactor_admin():
    path = os.path.join(BASE, 'business-admin', 'app.py')
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    before = count_db(content)
    
    # 通用清理
    content = re.sub(r'\s+except Exception as e:\s*\n\s+logging\.\w+\([^\n]+\)\s*\n', '\n', content)
    content = re.sub(r'\s+except:\s*\n\s+pass\n', '\n', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # 1. 用户列表 - 使用 UserService
    old = re.search(
        r'def get_users\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_users(user):
    """获取用户列表"""
    from business_common.user_service import get_user_service
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    keyword = request.args.get('keyword', '').strip()
    result = get_user_service().get_user_list(
        ec_id=user.get('ec_id'), project_id=user.get('project_id'),
        page=page, page_size=page_size
    )
    return jsonify({'success': True, 'data': result})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('  admin: get_users')
    
    # 2. 订单列表 - 使用 OrderService
    old = re.search(
        r'def get_all_orders\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_all_orders(user):
    """获取所有订单"""
    from business_common.order_service import OrderService
    status = request.args.get('status')
    keyword = request.args.get('keyword', '').strip()
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    order_service = OrderService()
    result = order_service.get_orders(
        ec_id=user.get('ec_id'), project_id=user.get('project_id'),
        status=status, keyword=keyword, page=page, page_size=page_size
    )
    return jsonify({'success': True, 'data': result})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('  admin: get_all_orders')
    
    # 3. 商品列表 - 使用 ProductService
    old = re.search(
        r'def get_products\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_products(user):
    """获取商品列表"""
    from business_common.product_service import ProductService
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    keyword = request.args.get('keyword', '').strip()
    category_id = request.args.get('category_id')
    status = request.args.get('status', 'active')
    product_service = ProductService()
    result = product_service.get_products(
        ec_id=user.get('ec_id'), project_id=user.get('project_id'),
        keyword=keyword if keyword else None,
        category_id=int(category_id) if category_id else None,
        status=status, page=page, page_size=page_size
    )
    return jsonify({'success': True, 'data': result})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('  admin: get_products')
    
    after = count_db(content)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  admin 总计: {before} → {after} (减少 {before-after})')
    return before, after

# ============================================================
print('=== staffH5 改造 ===')
b1, a1 = refactor_staffh5()

print('\n=== admin 改造 ===')
b2, a2 = refactor_admin()

print('\n=== userH5 通用清理 ===')
b3, a3 = refactor_file(
    os.path.join(BASE, 'business-userH5', 'app.py'),
    'userH5'
)

print('\n=== 最终统计 ===')
print(f'userH5:  {b3} → {a3}')
print(f'staffH5: {b1} → {a1}')
print(f'admin:   {b2} → {a2}')
print(f'合计:    {b1+b2+b3} → {a1+a2+a3} (减少 {b1+b2+b3-a1-a2-a3})')
