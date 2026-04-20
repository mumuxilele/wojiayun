#!/usr/bin/env python3

with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check which APIs already exist
missing_apis = []
apis_to_add = []

if '/api/admin/members' not in content:
    missing_apis.append('/api/admin/members')
if '/api/admin/member-levels' not in content:
    missing_apis.append('/api/admin/member-levels')
if '/api/admin/products' not in content:
    missing_apis.append('/api/admin/products')
if '/api/admin/coupons' not in content:
    missing_apis.append('/api/admin/coupons')
if '/api/admin/promotions' not in content:
    missing_apis.append('/api/admin/promotions')
if '/api/admin/group-buys' not in content:
    missing_apis.append('/api/admin/group-buys')
if '/api/admin/refunds' not in content:
    missing_apis.append('/api/admin/refunds')
if '/api/admin/notices' not in content:
    missing_apis.append('/api/admin/notices')
if '/api/admin/points-mall/goods' not in content:
    missing_apis.append('/api/admin/points-mall/goods')

print(f"Missing APIs: {missing_apis}")

# Stub API code
stub_apis = '''

# ============ 补充 Stub APIs ============

@app.route('/api/admin/members', methods=['GET'])
@require_admin
def admin_members_list(user):
    """会员列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    keyword = request.args.get('keyword', '')
    level = request.args.get('level', '')
    db = get_db()
    where = "WHERE 1=1"
    params = []
    if keyword:
        where += " AND (phone LIKE %s OR nickname LIKE %s)"
        params.extend([f'%{keyword}%', f'%{keyword}%'])
    if level:
        where += " AND level_code = %s"
        params.append(level)
    offset = (page - 1) * page_size
    total = db.get_total(f"SELECT COUNT(*) FROM business_members {where}", params)
    rows = db.query(f"SELECT id, phone, nickname, level_code, level_name, points, total_spend, created_at FROM business_members {where} ORDER BY id DESC LIMIT %s OFFSET %s", params + [page_size, offset])
    return jsonify({'success': True, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/admin/member-levels', methods=['GET'])
@require_admin
def admin_member_levels(user):
    """会员等级列表"""
    db = get_db()
    rows = db.query("SELECT level_code, level_name, discount, created_at FROM business_member_levels ORDER BY level_code")
    return jsonify({'success': True, 'data': rows})

@app.route('/api/admin/member-levels/statistics', methods=['GET'])
@require_admin
def admin_member_levels_stats(user):
    """会员等级统计"""
    db = get_db()
    rows = db.query("""
        SELECT ml.level_code, ml.level_name, COUNT(bm.id) as count
        FROM business_member_levels ml
        LEFT JOIN business_members bm ON bm.level_code = ml.level_code
        GROUP BY ml.level_code, ml.level_name
    """)
    return jsonify({'success': True, 'data': rows})

@app.route('/api/admin/member-levels/save', methods=['POST'])
@require_admin
def admin_member_levels_save(user):
    """保存会员等级"""
    data = request.get_json()
    level_code = data.get('level_code')
    level_name = data.get('level_name')
    discount = data.get('discount', 100)
    db = get_db()
    if db.execute("SELECT 1 FROM business_member_levels WHERE level_code = %s", [level_code]):
        db.execute("UPDATE business_member_levels SET level_name=%s, discount=%s WHERE level_code=%s", [level_name, discount, level_code])
    else:
        db.execute("INSERT INTO business_member_levels (level_code, level_name, discount) VALUES (%s, %s, %s)", [level_code, level_name, discount])
    return jsonify({'success': True, 'msg': '保存成功'})

@app.route('/api/admin/products', methods=['GET'])
@require_admin
def admin_products(user):
    """商品列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    keyword = request.args.get('keyword', '')
    category = request.args.get('category', '')
    db = get_db()
    where = "WHERE 1=1"
    params = []
    if keyword:
        where += " AND (name LIKE %s OR description LIKE %s)"
        params.extend([f'%{keyword}%', f'%{keyword}%'])
    if category:
        where += " AND category = %s"
        params.append(category)
    offset = (page - 1) * page_size
    total = db.get_total(f"SELECT COUNT(*) FROM business_products {where}", params)
    rows = db.query(f"SELECT id, name, category, price, stock, status, created_at FROM business_products {where} ORDER BY id DESC LIMIT %s OFFSET %s", params + [page_size, offset])
    return jsonify({'success': True, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/admin/coupons', methods=['GET'])
@require_admin
def admin_coupons(user):
    """优惠券列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    db = get_db()
    offset = (page - 1) * page_size
    total = db.get_total("SELECT COUNT(*) FROM business_coupons")
    rows = db.query("SELECT id, name, type, value, min_amount, total_count, used_count, start_date, end_date, status FROM business_coupons ORDER BY id DESC LIMIT %s OFFSET %s", [page_size, offset])
    return jsonify({'success': True, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/admin/promotions', methods=['GET'])
@require_admin
def admin_promotions(user):
    """促销活动列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    db = get_db()
    offset = (page - 1) * page_size
    total = db.get_total("SELECT COUNT(*) FROM business_promotions")
    rows = db.query("SELECT id, title, type, discount, start_date, end_date, status FROM business_promotions ORDER BY id DESC LIMIT %s OFFSET %s", [page_size, offset])
    return jsonify({'success': True, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/admin/group-buys', methods=['GET'])
@require_admin
def admin_group_buys(user):
    """拼团活动列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    db = get_db()
    offset = (page - 1) * page_size
    total = db.get_total("SELECT COUNT(*) FROM business_group_buys")
    rows = db.query("SELECT id, title, product_id, price, group_size, start_date, end_date, status FROM business_group_buys ORDER BY id DESC LIMIT %s OFFSET %s", [page_size, offset])
    return jsonify({'success': True, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/admin/refunds', methods=['GET'])
@require_admin
def admin_refunds(user):
    """退款申请列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    status = request.args.get('status', '')
    db = get_db()
    where = "WHERE 1=1"
    params = []
    if status:
        where += " AND status = %s"
        params.append(status)
    offset = (page - 1) * page_size
    total = db.get_total(f"SELECT COUNT(*) FROM business_refunds {where}", params)
    rows = db.query(f"SELECT id, order_id, amount, reason, status, created_at FROM business_refunds {where} ORDER BY id DESC LIMIT %s OFFSET %s", params + [page_size, offset])
    return jsonify({'success': True, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/admin/refunds/<int:id>/approve', methods=['POST'])
@require_admin
def admin_refunds_approve(user, id):
    """审批退款"""
    db = get_db()
    db.execute("UPDATE business_refunds SET status='approved', updated_at=NOW() WHERE id=%s", [id])
    return jsonify({'success': True, 'msg': '审批成功'})

@app.route('/api/admin/refunds/<int:id>/reject', methods=['POST'])
@require_admin
def admin_refunds_reject(user, id):
    """拒绝退款"""
    data = request.get_json()
    reason = data.get('reason', '')
    db = get_db()
    db.execute("UPDATE business_refunds SET status='rejected', reject_reason=%s, updated_at=NOW() WHERE id=%s", [reason, id])
    return jsonify({'success': True, 'msg': '已拒绝'})

@app.route('/api/admin/notices', methods=['GET'])
@require_admin
def admin_notices(user):
    """公告列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    db = get_db()
    offset = (page - 1) * page_size
    total = db.get_total("SELECT COUNT(*) FROM business_notices")
    rows = db.query("SELECT id, title, content, status, created_at FROM business_notices ORDER BY id DESC LIMIT %s OFFSET %s", [page_size, offset])
    return jsonify({'success': True, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/admin/notices/save', methods=['POST'])
@require_admin
def admin_notices_save(user):
    """保存公告"""
    data = request.get_json()
    notice_id = data.get('id')
    title = data.get('title')
    content = data.get('content')
    status = data.get('status', 'draft')
    db = get_db()
    if notice_id:
        db.execute("UPDATE business_notices SET title=%s, content=%s, status=%s, updated_at=NOW() WHERE id=%s", [title, content, status, notice_id])
    else:
        db.execute("INSERT INTO business_notices (title, content, status) VALUES (%s, %s, %s)", [title, content, status])
    return jsonify({'success': True, 'msg': '保存成功'})

@app.route('/api/admin/points-mall/goods', methods=['GET'])
@require_admin
def admin_points_mall_goods(user):
    """积分商城商品列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    keyword = request.args.get('keyword', '')
    db = get_db()
    where = "WHERE 1=1"
    params = []
    if keyword:
        where += " AND (name LIKE %s OR description LIKE %s)"
        params.extend([f'%{keyword}%', f'%{keyword}%'])
    offset = (page - 1) * page_size
    total = db.get_total(f"SELECT COUNT(*) FROM points_mall_goods {where}", params)
    rows = db.query(f"SELECT id, name, description, points_price, stock, status, created_at FROM points_mall_goods {where} ORDER BY id DESC LIMIT %s OFFSET %s", params + [page_size, offset])
    return jsonify({'success': True, 'data': {'list': rows, 'total': total, 'page': page, 'page_size': page_size}})

'''

# Insert before if __name__
if 'if __name__' in content:
    idx = content.find('if __name__')
    content = content[:idx] + stub_apis + content[idx:]
    with open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added stub APIs")
else:
    print("Could not find if __name__")
