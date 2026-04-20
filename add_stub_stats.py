#!/usr/bin/env python3
# Read old version
with open('/www/wwwroot/wojiayun/business-admin/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the broken insertion
if 'from business_common.analytics_service' in content:
    # Find and remove the bad insertion
    idx1 = content.find('# ============ 积分商城 API ============')
    if idx1 > 0:
        idx2 = content.find('\nif __name__', idx1)
        content = content[:content.rfind('\n\n# ============', 0, idx1)] + content[idx2:]
        print("Removed bad insertion")
    with open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8') as f:
        f.write(content)

# Now add simple stub endpoints
stub_code = '''
@app.route('/api/admin/statistics/overview', methods=['GET'])
@require_admin
def admin_statistics_overview(user):
    """数据概览"""
    days = request.args.get('days', 7, type=int)
    return jsonify({'success': True, 'data': {
        'totalIncome': 0, 'totalOrders': 0, 'newMembers': 0,
        'activeShops': 0, 'avgRating': 0, 'incomeChange': 0
    }})

@app.route('/api/admin/statistics/trend', methods=['GET'])
@require_admin
def admin_statistics_trend(user):
    """数据趋势"""
    days = request.args.get('days', 7, type=int)
    return jsonify({'success': True, 'data': {
        'dates': [], 'income': [], 'orders': []
    }})

'''

if 'statistics/overview' not in content:
    idx = content.find('if __name__')
    content = content[:idx] + stub_code + content[idx:]
    with open('/www/wwwroot/wojiayun/business-admin/app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added stub endpoints")
else:
    print("Endpoints already exist")
