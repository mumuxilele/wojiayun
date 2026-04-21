"""
更新三个 app.py 使用 StatisticsService
"""
import re, os

BASE = r'C:\Users\kingdee\WorkBuddy\Claw\wojiayun'

def count_db(content):
    return len(re.findall(r'db\.(get_one|get_all|execute|get_total)', content))

# === staffH5 ===
path = os.path.join(BASE, 'business-staffH5', 'app.py')
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
before = count_db(content)

# 替换 staff_dashboard_stats
old = re.search(r'def staff_dashboard_stats\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)', content, re.DOTALL)
if old:
    content = content[:old.start()] + '''def staff_dashboard_stats(user):
    """员工端仪表盘统计"""
    from business_common.statistics_service import get_stats_service
    stats = get_stats_service().staff_dashboard_stats(
        user.get('user_id'), user.get('ec_id'), user.get('project_id')
    )
    return jsonify({'success': True, 'data': stats})

''' + content[old.end():]
    print('staffH5: staff_dashboard_stats')

# 替换 get_staff_stats
old = re.search(r'def get_staff_stats\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)', content, re.DOTALL)
if old:
    content = content[:old.start()] + '''def get_staff_stats(user):
    """员工端统计"""
    from business_common.statistics_service import get_stats_service
    stats = get_stats_service().get_staff_stats(user.get('ec_id'), user.get('project_id'))
    return jsonify({'success': True, 'data': stats})

''' + content[old.end():]
    print('staffH5: get_staff_stats')

# 替换 get_staff_statistics
old = re.search(r'def get_staff_statistics\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)', content, re.DOTALL)
if old:
    content = content[:old.start()] + '''def get_staff_statistics(user):
    """员工端统计"""
    from business_common.statistics_service import get_stats_service
    stats = get_stats_service().get_staff_statistics(user.get('ec_id'), user.get('project_id'))
    return jsonify({'success': True, 'data': stats})

''' + content[old.end():]
    print('staffH5: get_staff_statistics')

# 替换 staff_pending_refunds
old = re.search(r'def staff_pending_refunds\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)', content, re.DOTALL)
if old:
    content = content[:old.start()] + '''def staff_pending_refunds(user):
    """待处理退款"""
    from business_common.statistics_service import get_stats_service
    result = get_stats_service().staff_pending_refunds(user.get('ec_id'), user.get('project_id'))
    return jsonify({'success': True, 'data': result})

''' + content[old.end():]
    print('staffH5: staff_pending_refunds')

# 替换 get_staff_member_activity
old = re.search(r'def get_staff_member_activity\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)', content, re.DOTALL)
if old:
    content = content[:old.start()] + '''def get_staff_member_activity(user):
    """会员活动统计"""
    from business_common.statistics_service import get_stats_service
    days = int(request.args.get('days', 7))
    stats = get_stats_service().get_staff_member_activity(
        user.get('ec_id'), user.get('project_id'), days
    )
    return jsonify({'success': True, 'data': stats})

''' + content[old.end():]
    print('staffH5: get_staff_member_activity')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
after = count_db(content)
print(f'staffH5: {before} -> {after}')

# === admin ===
path = os.path.join(BASE, 'business-admin', 'app.py')
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
before = count_db(content)

# 替换 admin_statistics
old = re.search(r'def admin_statistics\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)', content, re.DOTALL)
if old:
    content = content[:old.start()] + '''def admin_statistics(user):
    """管理端统计"""
    from business_common.statistics_service import get_stats_service
    stats = get_stats_service().admin_statistics(user.get('ec_id'), user.get('project_id'))
    return jsonify({'success': True, 'data': stats})

''' + content[old.end():]
    print('admin: admin_statistics')

# 替换 admin_user_profile
old = re.search(r'def admin_user_profile\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)', content, re.DOTALL)
if old:
    content = content[:old.start()] + '''def admin_user_profile(user, user_id):
    """用户详情统计"""
    from business_common.statistics_service import get_stats_service
    result = get_stats_service().admin_user_profile(user_id)
    return jsonify(result)

''' + content[old.end():]
    print('admin: admin_user_profile')

# 替换 venue_statistics
old = re.search(r'def venue_statistics\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)', content, re.DOTALL)
if old:
    content = content[:old.start()] + '''def venue_statistics(user):
    """场地统计"""
    from business_common.statistics_service import get_stats_service
    venue_id = request.args.get('venue_id')
    stats = get_stats_service().venue_statistics(int(venue_id) if venue_id else None)
    return jsonify({'success': True, 'data': stats})

''' + content[old.end():]
    print('admin: venue_statistics')

# 替换 admin_points_stats
old = re.search(r'def admin_points_stats\([^)]*\):.*?(?=\n@app\.route|\nclass |\Z)', content, re.DOTALL)
if old:
    content = content[:old.start()] + '''def admin_points_stats(user):
    """积分统计"""
    from business_common.statistics_service import get_stats_service
    stats = get_stats_service().admin_points_stats(user.get('ec_id'), user.get('project_id'))
    return jsonify({'success': True, 'data': stats})

''' + content[old.end():]
    print('admin: admin_points_stats')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
after = count_db(content)
print(f'admin: {before} -> {after}')

print('\nDone!')
