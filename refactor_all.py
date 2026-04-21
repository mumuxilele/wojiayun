"""
MVC批量改造脚本 - 全量处理
处理 userH5 / staffH5 / admin 三个 app.py
策略：
  1. 3+次DB调用的函数 → 迁移到对应Service
  2. 1-2次DB调用的函数 → 保留但清理冗余代码
  3. 删除重复函数
"""
import re, os

BASE = r'C:\Users\kingdee\WorkBuddy\Claw\wojiayun'

def count_db(content):
    return len(re.findall(r'db\.(get_one|get_all|execute|get_total)', content))

def analyze_functions(content):
    """分析每个函数的DB调用数"""
    lines = content.split('\n')
    func_db = {}
    current = 'init'
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('def ') and not stripped.startswith('def _'):
            current = stripped.split('(')[0].replace('def ', '')
        if re.search(r'db\.(get_one|get_all|execute|get_total)', line):
            func_db[current] = func_db.get(current, 0) + 1
    return func_db

# ============================================================
# 通用清理函数
# ============================================================
def clean_code(content):
    """通用代码清理"""
    # 1. 删除多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # 2. 简化 except pass
    content = re.sub(r'\s+except:\s*\n\s+pass\n', '\n', content)
    content = re.sub(r'\s+except Exception[^:]*:\s*\n\s+pass\n', '\n', content)
    
    # 3. 删除只有logging的except块
    content = re.sub(
        r'\s+except Exception as e:\s*\n\s+logging\.\w+\(f?"[^"]*"\)\s*\n',
        '\n',
        content
    )
    
    return content

# ============================================================
# userH5 改造
# ============================================================
def refactor_userh5():
    path = os.path.join(BASE, 'business-userH5', 'app.py')
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    before = count_db(content)
    
    # --- 1. create_review (5次) ---
    # 找到函数并替换
    old = re.search(
        r'(@app\.route\([^\n]+reviews[^\n]+\)\n@require_login\ndef create_review\(user\):.*?)(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''@app.route('/api/user/reviews', methods=['POST'])
@require_login
def create_review(user):
    """创建评价"""
    from business_common.review_service import get_review_service
    data = request.get_json() or {}
    rating = int(data.get('rating', 5))
    if rating < 1 or rating > 5:
        return jsonify({'success': False, 'msg': '评分必须在1-5之间'})
    review_service = get_review_service()
    return jsonify(review_service.create_review(
        user_id=user['user_id'],
        user_name=user.get('user_name', ''),
        order_id=int(data['order_id']) if data.get('order_id') else None,
        product_id=int(data['product_id']) if data.get('product_id') else None,
        rating=rating,
        content=data.get('content', '').strip(),
        images=data.get('images', [])
    ))

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ create_review')
    
    # --- 2. get_user_orders (2次) ---
    old = re.search(
        r'def get_user_orders\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_user_orders(user):
    """获取用户订单列表"""
    status = request.args.get('status')
    keyword = request.args.get('keyword', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 10)), 50)
    offset = (page - 1) * page_size
    
    conditions = ["user_id=%s", "deleted=0"]
    params = [user['user_id']]
    if status: conditions.append("order_status=%s"); params.append(status)
    if keyword:
        conditions.append("(order_no LIKE %s OR shipping_address LIKE %s)")
        params.extend([f'%{keyword}%', f'%{keyword}%'])
    
    where = " AND ".join(conditions)
    total = db.get_total(f"SELECT COUNT(*) FROM business_orders WHERE {where}", params)
    orders = db.get_all(
        f"SELECT id,order_no,order_type,total_amount,actual_amount,order_status,pay_status,"
        f"refund_status,created_at,shipping_address FROM business_orders WHERE {where} "
        f"ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    ) or []
    return jsonify({'success': True, 'data': {
        'items': orders, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_user_orders')
    
    # --- 3. apply_invoice_from_order (4次) → InvoiceService ---
    old = re.search(
        r'def apply_invoice_from_order\(user, order_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def apply_invoice_from_order(user, order_id):
    """申请发票"""
    from business_common.invoice_service_v2 import get_invoice_service
    data = request.get_json() or {}
    return jsonify(get_invoice_service().apply_invoice_from_order(
        user_id=user['user_id'],
        order_id=int(order_id),
        title_id=data.get('title_id'),
        title_type=data.get('title_type'),
        title_name=data.get('title_name'),
        tax_no=data.get('tax_no')
    ))

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ apply_invoice_from_order')
    
    # --- 4. update_invoice_title (3次) → InvoiceService ---
    old = re.search(
        r'def update_invoice_title\(user, title_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def update_invoice_title(user, title_id):
    """更新发票抬头"""
    from business_common.invoice_service_v2 import get_invoice_service
    data = request.get_json() or {}
    return jsonify(get_invoice_service().update_invoice_title(
        title_id=int(title_id),
        user_id=user['user_id'],
        title_name=data.get('title_name'),
        tax_no=data.get('tax_no'),
        bank_name=data.get('bank_name'),
        bank_account=data.get('bank_account'),
        address=data.get('address'),
        phone=data.get('phone'),
        is_default=data.get('is_default')
    ))

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ update_invoice_title')
    
    # --- 5. create_invoice_title (2次) → InvoiceService ---
    old = re.search(
        r'def create_invoice_title\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def create_invoice_title(user):
    """创建发票抬头"""
    from business_common.invoice_service_v2 import get_invoice_service
    data = request.get_json() or {}
    return jsonify(get_invoice_service().create_invoice_title(
        user_id=user['user_id'],
        title_type=data.get('title_type', 'personal'),
        title_name=data.get('title_name', '').strip(),
        tax_no=data.get('tax_no', ''),
        bank_name=data.get('bank_name', ''),
        bank_account=data.get('bank_account', ''),
        address=data.get('address', ''),
        phone=data.get('phone', ''),
        is_default=bool(data.get('is_default', False)),
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id')
    ))

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ create_invoice_title')
    
    # --- 6. delete_invoice_title (2次) → InvoiceService ---
    old = re.search(
        r'def delete_invoice_title\(user, title_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def delete_invoice_title(user, title_id):
    """删除发票抬头"""
    from business_common.invoice_service_v2 import get_invoice_service
    return jsonify(get_invoice_service().delete_invoice_title(int(title_id), user['user_id']))

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ delete_invoice_title')
    
    # --- 7. cancel_invoice (2次) → InvoiceService ---
    old = re.search(
        r'def cancel_invoice\(user, invoice_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def cancel_invoice(user, invoice_id):
    """取消发票申请"""
    from business_common.invoice_service_v2 import get_invoice_service
    return jsonify(get_invoice_service().cancel_invoice(int(invoice_id), user['user_id']))

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ cancel_invoice')
    
    # --- 8. get_invoice_titles (1次) → InvoiceService ---
    old = re.search(
        r'def get_invoice_titles\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_invoice_titles(user):
    """获取发票抬头列表"""
    from business_common.invoice_service_v2 import get_invoice_service
    return jsonify({'success': True, 'data': {'items': get_invoice_service().get_invoice_titles(user['user_id'])}})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_invoice_titles')
    
    # --- 9. get_user_invoices (2次) → InvoiceService ---
    old = re.search(
        r'def get_user_invoices\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_user_invoices(user):
    """获取发票列表"""
    from business_common.invoice_service_v2 import get_invoice_service
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    result = get_invoice_service().get_invoices(user['user_id'], page, page_size)
    return jsonify({'success': True, 'data': result})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_user_invoices')
    
    # --- 10. get_my_reviews (2次) → ReviewService ---
    old = re.search(
        r'def get_my_reviews\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_my_reviews(user):
    """获取我的评价列表"""
    from business_common.review_service import get_review_service
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    result = get_review_service().get_user_reviews(user['user_id'], page, page_size)
    return jsonify({'success': True, 'data': result})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_my_reviews')
    
    # --- 11. get_product_reviews (2次) → ReviewService ---
    old = re.search(
        r'def get_product_reviews\(product_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_product_reviews(product_id):
    """获取商品评价列表"""
    from business_common.review_service import get_review_service
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 10)), 50)
    result = get_review_service().get_product_reviews(int(product_id), page, page_size)
    return jsonify({'success': True, 'data': result})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_product_reviews')
    
    # --- 12. get_user_search_history (1次) → SearchHistoryService ---
    old = re.search(
        r'def get_user_search_history\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_user_search_history(user):
    """获取搜索历史"""
    from business_common.search_history_service import get_search_history_service
    return jsonify({'success': True, 'data': {'items': get_search_history_service().get_history(user['user_id'])}})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_user_search_history')
    
    # --- 13. delete_review (2次) ---
    old = re.search(
        r'def delete_review\(user, review_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def delete_review(user, review_id):
    """删除评价"""
    affected = db.execute(
        "UPDATE business_reviews SET deleted=1, updated_at=NOW() WHERE id=%s AND user_id=%s",
        [review_id, user['user_id']]
    )
    return jsonify({'success': affected > 0, 'msg': '已删除' if affected > 0 else '评价不存在'})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ delete_review')
    
    # --- 14. get_review_stats (1次) → ReviewService ---
    old = re.search(
        r'def get_review_stats\(\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_review_stats():
    """获取评价统计"""
    from business_common.review_service import get_review_service
    target_type = request.args.get('target_type', 'product')
    target_id = int(request.args.get('target_id', 0))
    stats = get_review_service().get_review_stats(target_type, target_id)
    return jsonify({'success': True, 'data': stats})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_review_stats')
    
    # --- 15. get_user_member (2次) ---
    old = re.search(
        r'def get_user_member\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_user_member(user):
    """获取会员信息"""
    member = db.get_one(
        "SELECT m.*, l.level_name, l.discount_rate, l.privileges "
        "FROM business_members m "
        "LEFT JOIN business_member_levels l ON m.member_level=l.level_code "
        "WHERE m.user_id=%s",
        [user['user_id']]
    )
    if not member:
        member = {'user_id': user['user_id'], 'points': 0, 'total_points': 0, 'balance': 0, 'member_level': 'L1'}
    return jsonify({'success': True, 'data': member})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_user_member')
    
    # --- 16. get_user_points_logs (2次) ---
    old = re.search(
        r'def get_user_points_logs\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_user_points_logs(user):
    """获取积分记录"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size
    total = db.get_total("SELECT COUNT(*) FROM business_points_log WHERE user_id=%s", [user['user_id']])
    logs = db.get_all(
        "SELECT * FROM business_points_log WHERE user_id=%s ORDER BY created_at DESC LIMIT %s OFFSET %s",
        [user['user_id'], page_size, offset]
    ) or []
    return jsonify({'success': True, 'data': {'items': logs, 'total': total, 'page': page, 'page_size': page_size}})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_user_points_logs')
    
    # --- 17. confirm_order (2次) ---
    old = re.search(
        r'def confirm_order\(user, order_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def confirm_order(user, order_id):
    """确认收货"""
    order = db.get_one(
        "SELECT id FROM business_orders WHERE id=%s AND user_id=%s AND order_status='shipped' AND deleted=0",
        [order_id, user['user_id']]
    )
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在或状态不允许确认'})
    db.execute(
        "UPDATE business_orders SET order_status='completed', completed_at=NOW(), updated_at=NOW() WHERE id=%s",
        [order_id]
    )
    return jsonify({'success': True, 'msg': '已确认收货'})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ confirm_order')
    
    # --- 18. get_product_categories (2次) ---
    old = re.search(
        r'def get_product_categories\(\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_product_categories():
    """获取商品分类"""
    categories = db.get_all(
        "SELECT id, name, parent_id, icon, sort_order FROM business_product_categories "
        "WHERE status=1 AND deleted=0 ORDER BY sort_order ASC, id ASC"
    ) or []
    return jsonify({'success': True, 'data': {'items': categories}})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_product_categories')
    
    # --- 19. get_shops (2次) ---
    old = re.search(
        r'def get_shops\(\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_shops():
    """获取门店列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size
    total = db.get_total("SELECT COUNT(*) FROM business_shops WHERE status='active' AND deleted=0")
    shops = db.get_all(
        "SELECT id,shop_name,address,phone,rating,cover_image FROM business_shops "
        "WHERE status='active' AND deleted=0 ORDER BY sort_order ASC LIMIT %s OFFSET %s",
        [page_size, offset]
    ) or []
    return jsonify({'success': True, 'data': {'items': shops, 'total': total, 'page': page, 'page_size': page_size}})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_shops')
    
    # --- 20. get_notices (2次) ---
    old = re.search(
        r'def get_notices\(\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_notices():
    """获取公告列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size
    try:
        total = db.get_total(
            "SELECT COUNT(*) FROM business_notices WHERE status='published' AND deleted=0 AND (end_date IS NULL OR end_date >= CURDATE())"
        )
        notices = db.get_all(
            "SELECT id,title,content,notice_type,importance,created_at FROM business_notices "
            "WHERE status='published' AND deleted=0 AND (end_date IS NULL OR end_date >= CURDATE()) "
            "ORDER BY importance DESC, created_at DESC LIMIT %s OFFSET %s",
            [page_size, offset]
        ) or []
        return jsonify({'success': True, 'data': {'items': notices, 'total': total, 'page': page, 'page_size': page_size}})
    except:
        return jsonify({'success': True, 'data': {'items': [], 'total': 0, 'page': page, 'page_size': page_size}})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_notices')
    
    # --- 21. get_user_bookings (2次) ---
    old = re.search(
        r'def get_user_bookings\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_user_bookings(user):
    """获取用户预约列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size
    total = db.get_total(
        "SELECT COUNT(*) FROM business_venue_bookings WHERE user_id=%s AND deleted=0",
        [user['user_id']]
    )
    bookings = db.get_all(
        "SELECT b.*,v.venue_name FROM business_venue_bookings b "
        "LEFT JOIN business_venues v ON b.venue_id=v.id "
        "WHERE b.user_id=%s AND b.deleted=0 ORDER BY b.created_at DESC LIMIT %s OFFSET %s",
        [user['user_id'], page_size, offset]
    ) or []
    return jsonify({'success': True, 'data': {'items': bookings, 'total': total, 'page': page, 'page_size': page_size}})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_user_bookings')
    
    # --- 22. get_venues (2次) ---
    old = re.search(
        r'def get_venues\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_venues(user):
    """获取场地列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size
    total = db.get_total("SELECT COUNT(*) FROM business_venues WHERE status='active' AND deleted=0")
    venues = db.get_all(
        "SELECT id,venue_name,venue_type,price,capacity,cover_image,address FROM business_venues "
        "WHERE status='active' AND deleted=0 ORDER BY sort_order ASC LIMIT %s OFFSET %s",
        [page_size, offset]
    ) or []
    return jsonify({'success': True, 'data': {'items': venues, 'total': total, 'page': page, 'page_size': page_size}})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_venues')
    
    # --- 23. cancel_booking (2次) ---
    old = re.search(
        r'def cancel_booking\(user, booking_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def cancel_booking(user, booking_id):
    """取消预约"""
    booking = db.get_one(
        "SELECT id,status FROM business_venue_bookings WHERE id=%s AND user_id=%s AND deleted=0",
        [booking_id, user['user_id']]
    )
    if not booking:
        return jsonify({'success': False, 'msg': '预约不存在'})
    if booking.get('status') not in ('pending', 'reserved'):
        return jsonify({'success': False, 'msg': '当前状态无法取消'})
    db.execute(
        "UPDATE business_venue_bookings SET status='cancelled', updated_at=NOW() WHERE id=%s",
        [booking_id]
    )
    return jsonify({'success': True, 'msg': '预约已取消'})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ cancel_booking')
    
    # --- 24. get_member_benefits (3次) ---
    old = re.search(
        r'def get_member_benefits\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_member_benefits(user):
    """获取会员权益"""
    member = db.get_one(
        "SELECT m.*,l.level_name,l.discount_rate,l.privileges "
        "FROM business_members m LEFT JOIN business_member_levels l ON m.member_level=l.level_code "
        "WHERE m.user_id=%s",
        [user['user_id']]
    )
    if not member:
        return jsonify({'success': False, 'msg': '未找到会员信息'})
    return jsonify({'success': True, 'data': member})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_member_benefits')
    
    # --- 25. get_member_card (2次) ---
    old = re.search(
        r'def get_member_card\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_member_card(user):
    """获取会员卡信息"""
    member = db.get_one(
        "SELECT m.*,l.level_name,l.discount_rate,l.icon "
        "FROM business_members m LEFT JOIN business_member_levels l ON m.member_level=l.level_code "
        "WHERE m.user_id=%s",
        [user['user_id']]
    )
    return jsonify({'success': True, 'data': member or {}})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_member_card')
    
    # --- 26. get_user_achievements (3次) ---
    old = re.search(
        r'def get_user_achievements\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_user_achievements(user):
    """获取用户成就"""
    achievements = db.get_all(
        "SELECT ua.*,a.achievement_name,a.icon,a.points as reward_points,a.description "
        "FROM business_user_achievements ua "
        "LEFT JOIN business_achievements a ON ua.achievement_id=a.id "
        "WHERE ua.user_id=%s ORDER BY ua.unlocked_at DESC",
        [user['user_id']]
    ) or []
    return jsonify({'success': True, 'data': {'items': achievements}})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_user_achievements')
    
    # --- 27. get_points_exchanges (2次) ---
    old = re.search(
        r'def get_points_exchanges\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_points_exchanges(user):
    """获取积分兑换记录"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    offset = (page - 1) * page_size
    total = db.get_total("SELECT COUNT(*) FROM business_points_exchanges WHERE user_id=%s", [user['user_id']])
    items = db.get_all(
        "SELECT * FROM business_points_exchanges WHERE user_id=%s ORDER BY created_at DESC LIMIT %s OFFSET %s",
        [user['user_id'], page_size, offset]
    ) or []
    return jsonify({'success': True, 'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size}})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_points_exchanges')
    
    # --- 28. get_order_detail (2次) ---
    old = re.search(
        r'def get_order_detail\(user, order_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_order_detail(user, order_id):
    """获取订单详情"""
    order = db.get_one(
        "SELECT * FROM business_orders WHERE id=%s AND user_id=%s AND deleted=0",
        [order_id, user['user_id']]
    )
    if not order:
        return jsonify({'success': False, 'msg': '订单不存在'})
    items = db.get_all(
        "SELECT * FROM business_order_items WHERE order_id=%s",
        [order_id]
    ) or []
    order['items'] = items
    return jsonify({'success': True, 'data': order})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_order_detail')
    
    # --- 29. get_venue_detail (2次) ---
    old = re.search(
        r'def get_venue_detail\(user, venue_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_venue_detail(user, venue_id):
    """获取场地详情"""
    venue = db.get_one(
        "SELECT * FROM business_venues WHERE id=%s AND status='active' AND deleted=0",
        [venue_id]
    )
    if not venue:
        return jsonify({'success': False, 'msg': '场地不存在'})
    time_slots = db.get_all(
        "SELECT * FROM business_venue_time_slots WHERE venue_id=%s AND status=1 ORDER BY start_time",
        [venue_id]
    ) or []
    venue['time_slots'] = time_slots
    return jsonify({'success': True, 'data': venue})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_venue_detail')
    
    # --- 30. get_user_invoice_detail (1次) ---
    old = re.search(
        r'def get_user_invoice_detail\(user, invoice_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_user_invoice_detail(user, invoice_id):
    """获取发票详情"""
    invoice = db.get_one(
        "SELECT i.*,o.order_no FROM business_invoices i "
        "LEFT JOIN business_orders o ON i.order_id=o.id "
        "WHERE i.id=%s AND i.user_id=%s AND i.deleted=0",
        [invoice_id, user['user_id']]
    )
    if not invoice:
        return jsonify({'success': False, 'msg': '发票不存在'})
    return jsonify({'success': True, 'data': invoice})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_user_invoice_detail')
    
    # --- 31. get_shop_detail (1次) ---
    old = re.search(
        r'def get_shop_detail\(shop_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_shop_detail(shop_id):
    """获取门店详情"""
    shop = db.get_one(
        "SELECT * FROM business_shops WHERE id=%s AND status='active' AND deleted=0",
        [shop_id]
    )
    if not shop:
        return jsonify({'success': False, 'msg': '门店不存在'})
    return jsonify({'success': True, 'data': shop})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_shop_detail')
    
    # --- 32. get_notice_detail (1次) ---
    old = re.search(
        r'def get_notice_detail\(notice_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_notice_detail(notice_id):
    """获取公告详情"""
    try:
        notice = db.get_one(
            "SELECT * FROM business_notices WHERE id=%s AND status='published' AND deleted=0",
            [notice_id]
        )
        if not notice:
            return jsonify({'success': False, 'msg': '公告不存在'})
        return jsonify({'success': True, 'data': notice})
    except:
        return jsonify({'success': False, 'msg': '公告不存在'})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_notice_detail')
    
    # --- 33. get_checkin_rank (1次) ---
    old = re.search(
        r'def get_checkin_rank\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_checkin_rank(user):
    """获取签到排名"""
    from business_common.checkin_service import get_checkin_service
    import time
    today = time.strftime('%Y-%m-%d')
    rank = get_checkin_service().get_checkin_rank(user['user_id'], today)
    return jsonify({'success': True, 'data': {'rank': rank, 'date': today}})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_checkin_rank')
    
    # --- 34. get_order_logistics (1次) ---
    old = re.search(
        r'def get_order_logistics\(user, order_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_order_logistics(user, order_id):
    """获取订单物流"""
    order = db.get_one(
        "SELECT tracking_no,logistics_company FROM business_orders WHERE id=%s AND user_id=%s",
        [order_id, user['user_id']]
    )
    if not order or not order.get('tracking_no'):
        return jsonify({'success': False, 'msg': '暂无物流信息'})
    return jsonify({'success': True, 'data': order})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_order_logistics')
    
    # --- 35. get_optimal_discount (1次) ---
    old = re.search(
        r'def get_optimal_discount\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_optimal_discount(user):
    """获取最优折扣"""
    from business_common.discount_calculator_service import discount_calculator
    data = request.get_json() or {}
    result = discount_calculator.get_optimal_discount(
        user_id=user['user_id'],
        items=data.get('items', []),
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id')
    )
    return jsonify({'success': True, 'data': result})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_optimal_discount')
    
    # --- 36. get_favorite_applications (2次) ---
    old = re.search(
        r'def get_favorite_applications\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_favorite_applications(user):
    """获取收藏的申请"""
    from business_common.application_service import ApplicationService
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    result = ApplicationService.get_favorite_applications(
        user_id=user['user_id'], page=page, page_size=page_size
    )
    return jsonify({'success': True, 'data': result})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_favorite_applications')
    
    # --- 37. track_user_behavior (2次) ---
    old = re.search(
        r'def track_user_behavior\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def track_user_behavior(user):
    """记录用户行为"""
    data = request.get_json() or {}
    try:
        user_behavior.track(
            user_id=user['user_id'],
            action=data.get('action'),
            target_type=data.get('target_type'),
            target_id=data.get('target_id'),
            ec_id=user.get('ec_id'),
            project_id=user.get('project_id')
        )
    except:
        pass
    return jsonify({'success': True})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ track_user_behavior')
    
    # --- 38. get_user_applications (2次) ---
    old = re.search(
        r'def get_user_applications\(user\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def get_user_applications(user):
    """获取用户申请列表"""
    from business_common.application_service import ApplicationService
    type_code = request.args.get('type_code')
    status = request.args.get('status')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    result = ApplicationService.get_user_applications(
        user_id=user['user_id'], type_code=type_code, status=status,
        page=page, page_size=page_size
    )
    return jsonify({'success': True, 'data': result})

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ get_user_applications')
    
    # --- 39. cancel_application (2次) ---
    old = re.search(
        r'def cancel_application\(user, app_id\):.*?(?=\n@app\.route|\nclass |\Z)',
        content, re.DOTALL
    )
    if old:
        new_func = '''def cancel_application(user, app_id):
    """取消申请"""
    from business_common.application_service import ApplicationService
    result = ApplicationService.cancel_application(
        app_id=int(app_id), user_id=user['user_id']
    )
    return jsonify(result)

'''
        content = content[:old.start()] + new_func + content[old.end():]
        print('✓ cancel_application')
    
    # 清理多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    after = count_db(content)
    print(f'\nuserH5: {before} → {after} DB calls (减少 {before-after})')
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return before, after

# ============================================================
# 运行
# ============================================================
print('=== 开始改造 userH5 ===')
b, a = refactor_userh5()
print(f'\n✅ userH5 改造完成: {b} → {a} (减少 {b-a} 处, {(b-a)*100//b if b else 0}%)')
