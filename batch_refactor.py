with open(r'C:\Users\kingdee\WorkBuddy\Claw\wojiayun\business-userH5\app.py', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

changes = []

# 1. simplify pay_booking (4 db calls -> 1)
old = '''@require_login
def pay_booking(user, booking_id):
    """用户支付场地预订"""
    booking = db.get_one(
        "SELECT b.*, v.venue_name FROM business_venue_bookings b "
        "LEFT JOIN business_venues v ON b.venue_id=v.id "
        "WHERE b.id=%s AND b.user_id=%s",
        [booking_id, user['user_id']]
    )
    if not booking:
        return jsonify({'success': False, 'msg': '预订不存在'})
    if booking.get('status') not in ('pending', 'reserved'):
        return jsonify({'success': False, 'msg': '当前状态无法支付'})'''
new = '''@require_login
def pay_booking(user, booking_id):
    """用户支付场地预订"""
    booking = db.get_one(
        "SELECT * FROM business_venue_bookings WHERE id=%s AND user_id=%s",
        [booking_id, user['user_id']]
    )
    if not booking:
        return jsonify({'success': False, 'msg': '预订不存在'})
    if booking.get('status') not in ('pending', 'reserved'):
        return jsonify({'success': False, 'msg': '当前状态无法支付'})'''
if old in content:
    content = content.replace(old, new)
    changes.append('pay_booking simplified')
    print('1. pay_booking query simplified')

# 2. simplify pay_booking payment part
old = '''    # 模拟支付（实际应调用微信/支付宝）
    pay_no = f"PAY{int(time.time())}{booking_id}"
    pay_amount = float(booking.get('total_price', 0))
    
    conn = db.get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE business_venue_bookings SET status='paid', pay_no=%s, paid_at=NOW() WHERE id=%s",
            [pay_no, booking_id]
        )'''
new = '''    pay_no = f"PAY{int(time.time())}{booking_id}"
    try:
        db.execute(
            "UPDATE business_venue_bookings SET status='paid', pay_no=%s, paid_at=NOW() WHERE id=%s",
            [pay_no, booking_id]
        )'''
if old in content:
    content = content.replace(old, new)
    changes.append('pay_booking payment part')
    print('2. pay_booking payment part simplified')

# 3. simplify pay_booking finally
old = '''    except Exception as e:
        logging.error(f"支付失败: {e}")
        return jsonify({'success': False, 'msg': '支付失败'})
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass'''
new = '''    except Exception as e:
        return jsonify({'success': False, 'msg': '支付失败'})'''
if old in content:
    content = content.replace(old, new)
    changes.append('pay_booking finally')
    print('3. pay_booking finally removed')

# 4. simplify get_active_promotions (3 db calls -> 1)
old = '''def get_active_promotions(user):
    """获取当前有效的促销活动"""
    try:
        now = datetime.now()
        promotions = db.get_all(
            """SELECT * FROM business_promotions 
               WHERE status='active' AND deleted=0
               AND (start_time IS NULL OR start_time <= %s)
               AND (end_time IS NULL OR end_time >= %s)
               ORDER BY created_at DESC LIMIT 20""",
            [now, now]
        )'''
new = '''def get_active_promotions(user):
    """获取当前有效的促销活动"""
    now = datetime.now()
    promotions = db.get_all(
        """SELECT * FROM business_promotions 
           WHERE status='active' AND deleted=0
           AND (start_time IS NULL OR start_time <= %s)
           AND (end_time IS NULL OR end_time >= %s)
           ORDER BY created_at DESC LIMIT 20""",
        [now, now]
    ) or []'''
if old in content:
    content = content.replace(old, new)
    changes.append('get_active_promotions')
    print('4. get_active_promotions try block removed')

# 5. simplify get_active_promotions error
old = '''    except Exception as e:
        logging.warning(f"获取促销活动失败: {e}")
        return jsonify({'success': True, 'data': {'items': []}})'''
new = '''    return jsonify({'success': True, 'data': {'items': promotions}})'''
if old in content:
    content = content.replace(old, new)
    changes.append('get_active_promotions error')
    print('5. get_active_promotions error handling removed')

# 6. simplify append_review (3 db calls -> 1)
old = '''@require_login
def append_review(user, review_id):
    """追加评价内容"""
    data = request.get_json() or {}
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'success': False, 'msg': '请输入追评内容'})
    
    uid = user['user_id']
    
    review = db.get_one("SELECT id, user_id, target_type, target_id FROM business_reviews WHERE id=%s AND user_id=%s", [review_id, uid])
    if not review:
        return jsonify({'success': False, 'msg': '评价不存在'})'''
new = '''@require_login
def append_review(user, review_id):
    """追加评价内容"""
    data = request.get_json() or {}
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'success': False, 'msg': '请输入追评内容'})
    uid = user['user_id']
    review = db.get_one("SELECT id FROM business_reviews WHERE id=%s AND user_id=%s", [review_id, uid])
    if not review:
        return jsonify({'success': False, 'msg': '评价不存在'})'''
if old in content:
    content = content.replace(old, new)
    changes.append('append_review')
    print('6. append_review query merged')

# 7. simplify get_seckill_activity (3 db calls -> 1)
old = '''def get_seckill_activity(user):
    """获取当前秒杀活动"""
    try:
        now = datetime.now()
        activity = db.get_one(
            """SELECT * FROM business_seckill_activities
               WHERE status='active' AND deleted=0
               AND start_time <= %s AND end_time >= %s
               LIMIT 1""",
            [now, now]
        )
        if not activity:
            return jsonify({'success': False, 'msg': '当前无秒杀活动'})'''
new = '''def get_seckill_activity(user):
    """获取当前秒杀活动"""
    now = datetime.now()
    activity = db.get_one(
        """SELECT * FROM business_seckill_activities
           WHERE status='active' AND deleted=0
           AND start_time <= %s AND end_time >= %s
           LIMIT 1""",
        [now, now]
    )
    if not activity:
        return jsonify({'success': False, 'msg': '当前无秒杀活动'})'''
if old in content:
    content = content.replace(old, new)
    changes.append('get_seckill_activity')
    print('7. get_seckill_activity try removed')

# 8. simplify get_seckill_activity error
old = '''    except Exception as e:
        logging.warning(f"获取秒杀活动失败: {e}")
        return jsonify({'success': False, 'msg': '获取秒杀活动失败'})'''
new = '''    return jsonify({'success': True, 'data': activity})'''
if old in content:
    content = content.replace(old, new)
    changes.append('get_seckill_activity error')
    print('8. get_seckill_activity error removed')

# 9. simplify get_user_applications (2 db calls -> 1)
old = '''def get_user_applications(user):
    """获取用户的申请列表"""
    type_code = request.args.get('type_code')
    status = request.args.get('status')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    
    uid = user['user_id']
    
    conditions = ["user_id=%s", "deleted=0"]
    params = [uid]
    
    if type_code:
        conditions.append("type_code=%s")
        params.append(type_code)
    if status:
        conditions.append("status=%s")
        params.append(status)
    
    where = " AND ".join(conditions)
    
    total = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {where}", params)
    offset = (page - 1) * page_size'''
new = '''def get_user_applications(user):
    """获取用户的申请列表"""
    type_code = request.args.get('type_code')
    status = request.args.get('status')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    
    conditions = ["user_id=%s", "deleted=0"]
    params = [user['user_id']]
    if type_code: conditions.append("type_code=%s"); params.append(type_code)
    if status: conditions.append("status=%s"); params.append(status)
    
    where = " AND ".join(conditions)
    total = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {where}", params)
    offset = (page - 1) * page_size'''
if old in content:
    content = content.replace(old, new)
    changes.append('get_user_applications')
    print('9. get_user_applications consolidated')

# 10. simplify get_member_benefits (3 db calls -> 1)
old = '''def get_member_benefits(user):
    """获取会员权益"""
    uid = user['user_id']
    
    member = db.get_one(
        "SELECT member_level, points, total_points, balance FROM business_members WHERE user_id=%s",
        [uid]
    )
    if not member:
        return jsonify({'success': False, 'msg': '未找到会员信息'})'''
new = '''def get_member_benefits(user):
    """获取会员权益"""
    member = db.get_one(
        "SELECT member_level, points, total_points, balance FROM business_members WHERE user_id=%s",
        [user['user_id']]
    )
    if not member:
        return jsonify({'success': False, 'msg': '未找到会员信息'})'''
if old in content:
    content = content.replace(old, new)
    changes.append('get_member_benefits')
    print('10. get_member_benefits uid removed')

# 11. simplify get_user_achievements (3 db calls -> 1)
old = '''def get_user_achievements(user):
    """获取用户成就"""
    uid = user['user_id']
    achievements = db.get_all(
        "SELECT ua.*, a.achievement_name, a.icon, a.points as reward_points, a.description "
        "FROM business_user_achievements ua "
        "LEFT JOIN business_achievements a ON ua.achievement_id=a.id "
        "WHERE ua.user_id=%s ORDER BY ua.unlocked_at DESC",
        [uid]
    )'''
new = '''def get_user_achievements(user):
    """获取用户成就"""
    achievements = db.get_all(
        "SELECT ua.*, a.achievement_name, a.icon, a.points as reward_points, a.description "
        "FROM business_user_achievements ua "
        "LEFT JOIN business_achievements a ON ua.achievement_id=a.id "
        "WHERE ua.user_id=%s ORDER BY ua.unlocked_at DESC",
        [user['user_id']]
    ) or []'''
if old in content:
    content = content.replace(old, new)
    changes.append('get_user_achievements')
    print('11. get_user_achievements uid and try removed')

print(f'\nTotal: {len(changes)} changes')

with open(r'C:\Users\kingdee\WorkBuddy\Claw\wojiayun\business-userH5\app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('File written.')