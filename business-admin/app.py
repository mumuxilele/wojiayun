#!/usr/bin/env python3
"""
社区商业 - 管理端 Web 服务（MVC 架构）
端口: 22313
路由层仅处理 HTTP 请求/响应，业务逻辑委托给 AdminService
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_common import config, auth, error_handler
from business_common.services import AdminService

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

error_handler.register_error_handlers(app)


<<<<<<< Updated upstream
=======
def log_admin_action(action, details=None):
    """记录管理员操作日志"""
    user = g.get('admin_user')
    if user:
        try:
            audit_log.log_action(
                user_id=user.get('user_id'),
                user_name=user.get('user_name'),
                action=action,
                details=details,
                ip=request.remote_addr,
                ec_id=user.get('ec_id'),
                project_id=user.get('project_id')
            )
        except Exception as e:
            logger.error(f"记录审计日志失败: {e}")

>>>>>>> Stashed changes
# ============ 管理员认证 ============

def get_current_admin():
    token = request.args.get('access_token') or request.headers.get('Token')
    isdev = request.args.get('isdev') or '0'
    return auth.verify_staff(token, isdev) if token else None


def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_admin()
        if not user:
            return jsonify({'success': False, 'msg': '请使用管理员账号登录'})
        return f(user, *args, **kwargs)
    return decorated

<<<<<<< Updated upstream
=======
# 认证钩子 - 在每个请求前检查登录状态
@app.before_request
def check_admin():
    # V15安全修复：仅排除健康检查和静态资源
    exempt_paths = ['/health', '/debugtest']
    if request.path in exempt_paths:
        return None

    # 静态资源免认证（CSS/JS/图片/HTML）
    # HTML文件免认证，由前端JS检查token并处理登录跳转
    if request.path.endswith('.css') or request.path.endswith('.js') or \
       request.path.endswith('.png') or request.path.endswith('.jpg') or \
       request.path.endswith('.jpeg') or request.path.endswith('.gif') or \
       request.path.endswith('.ico') or request.path.endswith('.svg') or \
       request.path.endswith('.html') or request.path.endswith('.htm') or \
       request.path.startswith('/uploads/') or request.path.startswith('/business-common/'):
        return None

    # 根路径返回index.html，免认证
    if request.path == '/':
        return None

    # API认证检查
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    g.admin_user = user
    return None

@app.after_request
def add_headers(response):
    response.headers['X-Response-Time'] = str(int(time.time() * 1000))
    return response

# ============ 用户信息 API ============

@app.route('/api/admin/userinfo', methods=['GET'])
def get_admin_userinfo():
    """获取当前管理员信息"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    return jsonify({
        'success': True, 
        'data': {
            'user_id': user.get('user_id'),
            'user_name': user.get('user_name'),
            'phone': user.get('phone'),
            'ec_id': user.get('ec_id'),
            'project_id': user.get('project_id'),
            'is_staff': user.get('is_staff')
        }
    })

# ============ 统计概览 ============

@app.route('/api/admin/statistics', methods=['GET'])
def admin_statistics(user):
    """管理端统计"""
    from business_common.statistics_service import get_stats_service
    stats = get_stats_service().admin_statistics(user.get('ec_id'), user.get('project_id'))
    return jsonify({'success': True, 'data': stats})


@app.route('/api/admin/statistics/overview', methods=['GET'])
@require_admin
def admin_statistics_overview(user):
    """V26.0：管理端运营看板概览数据"""
    from business_common.cache_service import cache_get, cache_set

    try:
        days = max(1, min(int(request.args.get('days', 30)), 90))
    except (TypeError, ValueError):
        days = 30

    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    cache_key = f"admin_stats_overview_{ec_id or 'all'}_{project_id or 'all'}_{days}"
    cached = cache_get(cache_key)
    if cached:
        return jsonify({'success': True, 'data': cached})

    try:
        data = analytics_service.get_overview(days=days, ec_id=ec_id, project_id=project_id)
        cache_set(cache_key, data, 180)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': True, 'data': {'days': days, 'productRank': [], 'memberRank': [], 'alerts': [], 'funnel': {}}})

@app.route('/api/admin/statistics/trend', methods=['GET'])
@require_admin
def admin_statistics_trend(user):
    """V26.0：管理端收入/订单趋势数据"""
    from business_common.cache_service import cache_get, cache_set

    try:
        days = max(1, min(int(request.args.get('days', 30)), 90))
    except (TypeError, ValueError):
        days = 30

    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    cache_key = f"admin_stats_trend_{ec_id or 'all'}_{project_id or 'all'}_{days}"
    cached = cache_get(cache_key)
    if cached:
        return jsonify({'success': True, 'data': cached})

    try:
        data = analytics_service.get_trend(days=days, ec_id=ec_id, project_id=project_id)
        cache_set(cache_key, data, 180)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': True, 'data': {'days': days, 'dates': [], 'orders': [], 'income': [], 'trend': []}})

@app.route('/api/admin/products/top', methods=['GET'])
@require_admin
def admin_top_products(user):
    """V26.0：热销商品排行榜"""
    from business_common.cache_service import cache_get, cache_set

    try:
        days = max(1, min(int(request.args.get('days', 30)), 90))
    except (TypeError, ValueError):
        days = 30
    try:
        limit = max(1, min(int(request.args.get('limit', 10)), 20))
    except (TypeError, ValueError):
        limit = 10

    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    cache_key = f"admin_top_products_{ec_id or 'all'}_{project_id or 'all'}_{days}_{limit}"
    cached = cache_get(cache_key)
    if cached:
        return jsonify({'success': True, 'data': cached})

    try:
        data = analytics_service.get_top_products(ec_id=ec_id, project_id=project_id, days=days, limit=limit)
        cache_set(cache_key, data, 180)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': True, 'data': []})

@app.route('/api/admin/statistics/refund-analysis', methods=['GET'])
@require_admin
def admin_refund_analysis(user):
    """退款分析接口：近30天退款趋势"""
    from business_common.cache_service import cache_get, cache_set
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    cache_key = f"admin_refund_{ec_id}_{project_id}"
    cached = cache_get(cache_key)
    if cached:
        return jsonify({'success': True, 'data': cached})

    where = "deleted=0"
    params = []
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)

    try:
        # 近30天退款趋势
        trend = db.get_all(
            f"""SELECT DATE(updated_at) as date, COUNT(*) as cnt,
                       SUM(actual_amount) as amount
                FROM business_orders
                WHERE order_status='refunded' AND {where}
                AND updated_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY DATE(updated_at)
                ORDER BY date ASC""",
            params
        )
        # 退款原因分析
        reasons = db.get_all(
            f"""SELECT COALESCE(refund_reason, '未填写') as reason, COUNT(*) as cnt
                FROM business_orders
                WHERE order_status IN ('refunding','refunded') AND {where}
                GROUP BY refund_reason
                ORDER BY cnt DESC LIMIT 10""",
            params
        )
        data = {'trend': trend or [], 'reasons': reasons or []}
        cache_set(cache_key, data, 300)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': True, 'data': {'trend': [], 'reasons': []}})

@app.route('/api/admin/statistics/member-growth', methods=['GET'])
@require_admin
def admin_member_growth(user):
    """会员增长趋势：近30天每日新增会员"""
    from business_common.cache_service import cache_get, cache_set
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    cache_key = f"admin_member_growth_{ec_id}_{project_id}"
    cached = cache_get(cache_key)
    if cached:
        return jsonify({'success': True, 'data': cached})

    where = "1=1"
    params = []
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)

    try:
        trend = db.get_all(
            f"""SELECT DATE(created_at) as date, COUNT(*) as new_members
                FROM business_members
                WHERE {where} AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY DATE(created_at)
                ORDER BY date ASC""",
            params
        )
        # 会员等级分布
        level_dist = db.get_all(
            f"SELECT member_level, COUNT(*) as cnt FROM business_members WHERE {where} GROUP BY member_level",
            params
        )
        # 积分消费统计
        points_stats = db.get_one(
            f"""SELECT SUM(points) as total_issued,
                       SUM(CASE WHEN log_type='spend' THEN ABS(points) ELSE 0 END) as total_spent
                FROM business_points_log WHERE 1=1""",
            []
        )
        data = {
            'trend': trend or [],
            'level_distribution': level_dist or [],
            'points_issued': float(points_stats.get('total_issued') or 0) if points_stats else 0,
            'points_spent': float(points_stats.get('total_spent') or 0) if points_stats else 0
        }
        cache_set(cache_key, data, 300)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/statistics/inventory-warning', methods=['GET'])
@require_admin
def admin_inventory_warning(user):
    """商品库存预警：库存低于阈值的商品列表"""
    threshold = int(request.args.get('threshold', 5))
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')

    where = "deleted=0 AND status='active' AND stock <= %s"
    params = [threshold]
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)

    try:
        items = db.get_all(
            f"SELECT id, product_name, category, price, stock, sales_count FROM business_products WHERE {where} ORDER BY stock ASC LIMIT 50",
            params
        )
        return jsonify({'success': True, 'data': {'items': items or [], 'threshold': threshold}})
        return jsonify({'success': True, 'data': {'items': [], 'threshold': threshold}})

# ============ V27.0 RFM用户分析 ============

@app.route('/api/admin/statistics/rfm-overview', methods=['GET'])
@require_admin
def admin_rfm_overview(user):
    """V27.0: RFM用户分析概览"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        # 查询RFM分群统计
        stats = db.get_all("""
            SELECT 
                rfm_type,
                COUNT(*) as count,
                ROUND(AVG(monetary_total), 2) as avg_consume,
                ROUND(AVG(frequency_orders), 1) as avg_orders
            FROM rfm_analysis_view v
            JOIN business_members m ON v.member_id = m.user_id
            WHERE 1=1
            AND m.ec_id=%s
            AND m.project_id=%s
            GROUP BY rfm_type
            ORDER BY count DESC
        """, [ec_id, project_id]) or []
        
        # 计算各类型占比
        total = sum(s['count'] for s in stats)
        for s in stats:
            s['percentage'] = round(s['count'] / total * 100, 1) if total > 0 else 0
        
        # 获取RFM分布颜色
        type_colors = {
            '重要价值用户': '#52c41a',
            '重要发展用户': '#1890ff',
            '重要保持用户': '#faad14',
            '重要挽留用户': '#ff4d4f'
        }
        for s in stats:
            s['color'] = type_colors.get(s['rfm_type'], '#999999')
        
        return jsonify({'success': True, 'data': {
            'stats': stats,
            'total': total,
            'overview': {
                'value_users': next((s['count'] for s in stats if s['rfm_type'] == '重要价值用户'), 0),
                'developing_users': next((s['count'] for s in stats if s['rfm_type'] == '重要发展用户'), 0),
                'keeping_users': next((s['count'] for s in stats if s['rfm_type'] == '重要保持用户'), 0),
                'retaining_users': next((s['count'] for s in stats if s['rfm_type'] == '重要挽留用户'), 0),
            }
        }})
        return jsonify({'success': True, 'data': {'stats': [], 'total': 0, 'overview': {}}})

@app.route('/api/admin/statistics/rfm-list', methods=['GET'])
@require_admin
def admin_rfm_list(user):
    """V27.0: RFM用户明细列表"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(max(1, int(request.args.get('page_size', 20))), 100)
    rfm_type = request.args.get('rfm_type')  # 可选：按RFM类型筛选
    sort_by = request.args.get('sort_by', 'recency')  # recency/frequency/monetary
    
    try:
        where = "1=1"
        params = []
        if ec_id:
            where += " AND m.ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND m.project_id=%s"
            params.append(project_id)
        if rfm_type:
            where += " AND v.rfm_type=%s"
            params.append(rfm_type)
        
        # 排序
        order_map = {
            'recency': 'v.recency_days ASC',
            'frequency': 'v.frequency_orders DESC',
            'monetary': 'v.monetary_total DESC'
        }
        order_by = order_map.get(sort_by, 'v.recency_days ASC')
        
        # 查询总数
        count_where = where.replace("v.", "v.").replace("m.", "m.")
        total = db.get_total(f"""
            SELECT COUNT(*) FROM rfm_analysis_view v
            JOIN business_members m ON v.member_id = m.user_id
            WHERE {where}
        """, params)
        
        # 分页查询
        offset = (page - 1) * page_size
        items = db.get_all(f"""
            SELECT 
                v.member_id, v.user_name, v.phone, v.member_level,
                v.recency_days, v.frequency_orders, v.monetary_total,
                v.rfm_type, v.r_score, v.f_score, v.m_score,
                m.points, m.checkin_streak, m.last_checkin_date
            FROM rfm_analysis_view v
            JOIN business_members m ON v.member_id = m.user_id
            WHERE {where}
            ORDER BY {order_by}
            LIMIT %s OFFSET %s
        """, params + [page_size, offset]) or []
        
        return jsonify({'success': True, 'data': {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0, 'page': 1, 'page_size': page_size, 'pages': 0}})

@app.route('/api/admin/statistics/rfm-trend', methods=['GET'])
@require_admin
def admin_rfm_trend(user):
    """V27.0: RFM分布趋势（近6个月）"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        from datetime import date, timedelta
        today = date.today()
        months = []
        
        for i in range(5, -1, -1):
            # 计算月份
            month_date = date(today.year, today.month, 1)
            if i > 0:
                # 往前推i个月
                year = month_date.year - (month_date.month - 1 - i) // 12
                month = (month_date.month - 1 - i) % 12 + 1
                month_date = date(year, month, 1)
            
            months.append({
                'month': month_date.strftime('%Y-%m'),
                'month_label': month_date.strftime('%m月')
            })
        
        # 查询近6个月的RFM分布（基于订单时间）
        trend_data = []
        for m in months:
            month_start = m['month'] + '-01'
            # 计算该月的RFM分布（简化版：按会员数和消费会员数估算）
            try:
                total_members = db.get_total("""
                    SELECT COUNT(*) FROM business_members m
                    WHERE m.created_at < %s
                    AND m.ec_id=%s AND m.project_id=%s
                """, [month_start + ' 23:59:59', ec_id, project_id])
                
                active_members = db.get_total("""
                    SELECT COUNT(DISTINCT user_id) FROM business_orders
                    WHERE created_at >= %s AND created_at < %s AND pay_status='paid' AND deleted=0
                    AND ec_id=%s AND project_id=%s
                """, [month_start, month_start[:7] + '-31 23:59:59', ec_id, project_id])
                
                # 计算活跃率
                active_rate = round(active_members / total_members * 100, 1) if total_members > 0 else 0
                
                trend_data.append({
                    'month': m['month'],
                    'month_label': m['month_label'],
                    'total_members': total_members,
                    'active_members': active_members,
                    'active_rate': active_rate
                })
            except Exception as month_e:
                logging.warning(f"查询{m['month']}数据失败: {month_e}")
                trend_data.append({
                    'month': m['month'],
                    'month_label': m['month_label'],
                    'total_members': 0,
                    'active_members': 0,
                    'active_rate': 0
                })
        
        return jsonify({'success': True, 'data': trend_data})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/statistics/rfm-export', methods=['GET'])
@require_admin
def admin_rfm_export(user):
    """V27.0: 导出RFM分析数据"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    rfm_type = request.args.get('rfm_type')
    
    try:
        where = "1=1"
        params = []
        if ec_id:
            where += " AND m.ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND m.project_id=%s"
            params.append(project_id)
        if rfm_type:
            where += " AND v.rfm_type=%s"
            params.append(rfm_type)
        
        items = db.get_all(f"""
            SELECT 
                v.member_id as user_id, v.user_name, v.phone, v.member_level,
                v.recency_days, v.frequency_orders, v.monetary_total,
                v.rfm_type, 
                CONCAT(v.r_score, '-', v.f_score, '-', v.m_score) as rfm_score,
                m.points, m.checkin_streak, m.last_checkin_date
            FROM rfm_analysis_view v
            JOIN business_members m ON v.member_id = m.user_id
            WHERE {where}
            ORDER BY v.monetary_total DESC
        """, params) or []
        
        return jsonify({'success': True, 'data': items})
        return jsonify({'success': True, 'data': []})
>>>>>>> Stashed changes

# ============ 申请单管理 ============

@app.route('/api/admin/applications', methods=['GET'])
@require_admin
def list_applications(user):
    """申请单列表"""
    svc = AdminService()
    return jsonify(svc.list_applications(
        status=request.args.get('status'),
        app_type=request.args.get('app_type'),
        keyword=request.args.get('keyword', ''),
        start_date=request.args.get('start_date'),
        end_date=request.args.get('end_date'),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


@app.route('/api/admin/applications/<int:app_id>', methods=['GET'])
@require_admin
def get_application(user, app_id):
    """申请单详情"""
    svc = AdminService()
    return jsonify(svc.get_application(app_id))


@app.route('/api/admin/applications/<int:app_id>', methods=['PUT'])
@require_admin
def update_application(user, app_id):
    """修改申请单"""
    data = request.get_json() or {}
    svc = AdminService()
    return jsonify(svc.update_application(app_id, data))


@app.route('/api/admin/applications/<int:app_id>', methods=['DELETE'])
@require_admin
def delete_application(user, app_id):
    """删除申请单"""
    svc = AdminService()
    return jsonify(svc.delete_application(app_id))


# ============ 订单管理 ============

@app.route('/api/admin/orders', methods=['GET'])
@require_admin
def list_orders(user):
    """订单列表"""
    svc = AdminService()
    return jsonify(svc.list_orders(
        status=request.args.get('status'),
        keyword=request.args.get('keyword', ''),
        start_date=request.args.get('start_date'),
        end_date=request.args.get('end_date'),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))


@app.route('/api/admin/orders/<int:order_id>', methods=['GET'])
@require_admin
def get_order(user, order_id):
    """订单详情"""
    svc = AdminService()
    return jsonify(svc.get_order(order_id))


@app.route('/api/admin/orders/<int:order_id>', methods=['PUT'])
@require_admin
def update_order(user, order_id):
    """修改订单"""
    data = request.get_json() or {}
    svc = AdminService()
    return jsonify(svc.update_order(order_id, data))


@app.route('/api/admin/orders/<int:order_id>', methods=['DELETE'])
@require_admin
def delete_order(user, order_id):
    """删除订单"""
    svc = AdminService()
    return jsonify(svc.delete_order(order_id))


# ============ 门店管理 ============

@app.route('/api/admin/shops', methods=['GET'])
@require_admin
def list_shops(user):
    """门店列表"""
    svc = AdminService()
    return jsonify(svc.list_shops())


@app.route('/api/admin/shops/<int:shop_id>', methods=['GET'])
@require_admin
def get_shop(user, shop_id):
    """门店详情"""
    svc = AdminService()
    return jsonify(svc.get_shop(shop_id))


@app.route('/api/admin/shops', methods=['POST'])
@require_admin
def create_shop(user):
    """创建门店"""
    data = request.get_json() or {}
    svc = AdminService()
    return jsonify(svc.create_shop(data))


@app.route('/api/admin/shops/<int:shop_id>', methods=['PUT'])
@require_admin
def update_shop(user, shop_id):
    """修改门店"""
    data = request.get_json() or {}
    svc = AdminService()
    return jsonify(svc.update_shop(shop_id, data))


@app.route('/api/admin/shops/<int:shop_id>', methods=['DELETE'])
@require_admin
def delete_shop(user, shop_id):
    """删除门店"""
    svc = AdminService()
    return jsonify(svc.delete_shop(shop_id))


# ============ 统计数据 ============

@app.route('/api/admin/statistics', methods=['GET'])
@require_admin
<<<<<<< Updated upstream
def get_statistics(user):
    """综合统计"""
    svc = AdminService()
    return jsonify(svc.get_statistics())

=======
def admin_create_product(user):
    """创建商品"""
    data = request.get_json() or {}
    product_name = data.get('product_name', '').strip()
    shop_id = data.get('shop_id')
    category = data.get('category', '').strip()
    price = float(data.get('price', 0))
    description = data.get('description', '')
    images = data.get('images', [])
    stock = int(data.get('stock', 0))
    unit = data.get('unit', '件')
    
    if not product_name or not shop_id:
        return jsonify({'success': False, 'msg': '商品名称和所属门店不能为空'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        db.execute(
            """INSERT INTO business_products 
               (product_name, shop_id, category, price, description, images, stock, unit, ec_id, project_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            [product_name, shop_id, category, price, description, json.dumps(images), stock, unit, ec_id, project_id]
        )
        log_admin_action('create_product', {'product_name': product_name})
        return jsonify({'success': True, 'msg': '商品创建成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/products/<int:product_id>', methods=['PUT'])
@require_admin
def admin_update_product(user, product_id):
    """更新商品"""
    data = request.get_json() or {}
    
    allowed_fields = ['product_name', 'shop_id', 'category', 'price', 'original_price', 'description', 'images', 'stock', 'unit', 'status', 'sort_order']
    updates = []
    params = []
    for f in allowed_fields:
        if f in data:
            if f == 'images':
                updates.append(f + "=%s")
                params.append(json.dumps(data[f]))
            else:
                updates.append(f + "=%s")
                params.append(data[f])
    
    if not updates:
        return jsonify({'success': False, 'msg': '没有要更新的字段'})
    
    params.append(product_id)
    try:
        db.execute("UPDATE business_products SET " + ", ".join(updates) + " WHERE id=%s", params)
        log_admin_action('update_product', {'product_id': product_id})
        return jsonify({'success': True, 'msg': '更新成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/products/<int:product_id>', methods=['DELETE'])
@require_admin
def admin_delete_product(user, product_id):
    """删除商品"""
    db.execute("UPDATE business_products SET deleted=1 WHERE id=%s", [product_id])
    log_admin_action('delete_product', {'product_id': product_id})
    return jsonify({'success': True, 'msg': '删除成功'})

# ============ 商品SKU规格管理 ============

@app.route('/api/admin/products/<int:product_id>/skus', methods=['GET'])
@require_admin
def admin_list_product_skus(user, product_id):
    """获取商品SKU列表"""
    
    try:
        items = db.get_all(
            """SELECT id, sku_name, sku_code, specs, price, original_price, stock, sales_count, status 
               FROM business_product_skus WHERE product_id=%s AND deleted=0 ORDER BY id""",
            [product_id]
        )
        return jsonify({'success': True, 'data': {'items': items or []}})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/products/<int:product_id>/skus', methods=['POST'])
@require_admin
def admin_create_sku(user, product_id):
    """创建商品SKU"""
    data = request.get_json() or {}
    sku_name = data.get('sku_name', '').strip()
    sku_code = data.get('sku_code', '').strip()
    specs = data.get('specs', {})
    price = float(data.get('price', 0))
    original_price = float(data.get('original_price', 0))
    stock = int(data.get('stock', 0))
    
    if not sku_name:
        return jsonify({'success': False, 'msg': 'SKU名称不能为空'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        db.execute(
            """INSERT INTO business_product_skus 
               (product_id, sku_name, sku_code, specs, price, original_price, stock, ec_id, project_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            [product_id, sku_name, sku_code, json.dumps(specs), price, original_price, stock, ec_id, project_id]
        )
        return jsonify({'success': True, 'msg': 'SKU创建成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/products/skus/<int:sku_id>', methods=['PUT'])
@require_admin
def admin_update_sku(user, sku_id):
    """更新SKU"""
    data = request.get_json() or {}
    
    allowed_fields = ['sku_name', 'sku_code', 'specs', 'price', 'original_price', 'stock', 'status']
    updates = []
    params = []
    for f in allowed_fields:
        if f in data:
            if f == 'specs':
                updates.append(f + "=%s")
                params.append(json.dumps(data[f]))
            else:
                updates.append(f + "=%s")
                params.append(data[f])
    
    if not updates:
        return jsonify({'success': False, 'msg': '没有要更新的字段'})
    
    params.append(sku_id)
    try:
        db.execute("UPDATE business_product_skus SET " + ", ".join(updates) + " WHERE id=%s", params)
        return jsonify({'success': True, 'msg': '更新成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/products/skus/<int:sku_id>', methods=['DELETE'])
@require_admin
def admin_delete_sku(user, sku_id):
    """删除SKU"""
    db.execute("UPDATE business_product_skus SET deleted=1 WHERE id=%s", [sku_id])
    return jsonify({'success': True, 'msg': '删除成功'})
>>>>>>> Stashed changes

# ============ 用户管理 ============

@app.route('/api/admin/users', methods=['GET'])
@require_admin
def list_users(user):
    """用户列表"""
    svc = AdminService()
    return jsonify(svc.list_members(
        keyword=request.args.get('keyword', ''),
        page=int(request.args.get('page', 1)),
        page_size=int(request.args.get('page_size', 20))
    ))

<<<<<<< Updated upstream
=======
@app.route('/api/admin/venues/<venue_id>', methods=['GET'])
def get_venue(venue_id):
    """获取场地详情"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    where = "id=%s AND deleted=0"
    params = [venue_id]
    where, params = add_scope_filter(where, params)
    
    venue = db.get_one("SELECT * FROM business_venues WHERE " + where, params)
    if not venue:
        return jsonify({'success': False, 'msg': '场地不存在'})
    return jsonify({'success': True, 'data': venue})

@app.route('/api/admin/venues/<venue_id>', methods=['PUT'])
def update_venue(venue_id):
    data = request.get_json() or {}
    updates = []
    fields = ['venue_name','venue_code','venue_type','description','rules','capacity','price','images','facilities','open_hours','status']
    params = []
    
    # 检查venue_code唯一性
    if 'venue_code' in data:
        venue_code = data['venue_code']
        existing = db.get_one("SELECT id FROM business_venues WHERE venue_code=%s AND id!=%s AND deleted=0", [venue_code, venue_id])
        if existing:
            return jsonify({'success': False, 'msg': '场馆编号已存在，请使用不同的编号'})
    
    for f in fields:
        if f in data:
            val = data[f]
            if f in ('images','facilities','open_hours') and isinstance(val, (list, dict)):
                val = json.dumps(val)
            updates.append(f + "=%s")
            params.append(val)
    
    if not updates:
        return jsonify({'success': False, 'msg': '没有更新字段'})
    
    params.append(venue_id)
    db.execute("UPDATE business_venues SET " + ",".join(updates) + " WHERE id=%s", params)
    return jsonify({'success': True, 'msg': '更新成功'})

@app.route('/api/admin/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    """删除场地"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    db.execute("UPDATE business_venues SET deleted=1 WHERE id=%s", [venue_id])
    # 记录审计日志
    log_admin_action('delete_venue', {'venue_id': venue_id})
    return jsonify({'success': True, 'msg': '删除成功'})

# ============ 预约时段管理 API ============

@app.route('/api/admin/venue-bookings', methods=['GET'])
def list_venue_bookings():
    """所有场地预约列表"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    venue_id = request.args.get('venue_id')
    status = request.args.get('status')
    date = request.args.get('date')
    keyword = request.args.get('keyword', '')
    
    where = "vb.deleted=0"
    params = []
    if venue_id:
        where += " AND vb.venue_id=%s"
        params.append(venue_id)
    if status:
        where += " AND vb.status=%s"
        params.append(status)
    if date:
        where += " AND vb.book_date=%s"
        params.append(date)
    if keyword:
        where += " AND (vb.user_name LIKE %s OR vb.verify_code LIKE %s)"
        params.extend(['%' + keyword + '%', '%' + keyword + '%'])
    where, params = add_scope_filter(where, params, 'vb')
    
    total = db.get_total("SELECT COUNT(*) FROM business_venue_bookings vb WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT vb.id, vb.venue_id, vb.user_id, vb.user_name, vb.user_phone, "
        "CAST(vb.book_date AS CHAR) as book_date, "
        "CAST(vb.start_time AS CHAR) as start_time, CAST(vb.end_time AS CHAR) as end_time, "
        "CAST(vb.total_hours AS CHAR) as total_hours, vb.total_price, vb.status, vb.pay_status, vb.verify_code, vb.created_at, "
        "v.venue_name, v.venue_type "
        "FROM business_venue_bookings vb "
        "LEFT JOIN business_venues v ON vb.venue_id=v.id "
        "WHERE " + where + " ORDER BY vb.book_date DESC, vb.start_time ASC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/admin/venue-bookings/<booking_id>', methods=['PUT'])
def update_venue_booking(booking_id):
    """更新预约状态（确认/取消）"""
    data = request.get_json() or {}
    new_status = data.get('status')
    if new_status not in ('pending','confirmed','completed','cancelled'):
        return jsonify({'success': False, 'msg': '状态值无效'})
    db.execute("UPDATE business_venue_bookings SET status=%s WHERE id=%s", [new_status, booking_id])
    return jsonify({'success': True, 'msg': '状态更新成功'})

@app.route('/api/admin/venue-bookings/<booking_id>/pay', methods=['POST'])
def confirm_booking_pay(booking_id):
    """确认预约缴费"""
    data = request.get_json() or {}
    pay_status = data.get('pay_status', 'paid')
    db.execute(
        "UPDATE business_venue_bookings SET pay_status=%s, status='confirmed' WHERE id=%s",
        [pay_status, booking_id]
    )
    return jsonify({'success': True, 'msg': '缴费确认成功'})

@app.route('/api/admin/venue-bookings/<booking_id>/complete', methods=['POST'])
def complete_booking(booking_id):
    """完成预约（confirmed → completed）"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    booking = db.get_one("SELECT id, status FROM business_venue_bookings WHERE id=%s AND deleted=0", [booking_id])
    if not booking:
        return jsonify({'success': False, 'msg': '预约不存在'})
    if booking.get('status') != 'confirmed':
        return jsonify({'success': False, 'msg': '只有已确认的预约才能标记完成'})
    db.execute("UPDATE business_venue_bookings SET status='completed', updated_at=NOW() WHERE id=%s", [booking_id])
    # 记录审计日志
    log_admin_action('complete_booking', {'booking_id': booking_id})
    return jsonify({'success': True, 'msg': '预约已完成'})

@app.route('/api/admin/venue-bookings/verify', methods=['POST'])
def verify_booking_code():
    """核销码验证 - 根据核销码查找预约并完成核销"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    data = request.get_json() or {}
    verify_code = (data.get('verify_code') or '').strip().upper()
    if not verify_code:
        return jsonify({'success': False, 'msg': '请输入核销码'})
    where = "verify_code=%s AND deleted=0"
    params = [verify_code]
    where, params = add_scope_filter(where, params, '')
    booking = db.get_one(
        "SELECT vb.*, v.venue_name FROM business_venue_bookings vb "
        "LEFT JOIN business_venues v ON vb.venue_id=v.id "
        "WHERE vb." + where,
        params
    )
    if not booking:
        return jsonify({'success': False, 'msg': '核销码无效或不属于本项目'})
    if booking.get('status') == 'completed':
        return jsonify({'success': False, 'msg': '该预约已核销', 'data': booking})
    if booking.get('status') == 'cancelled':
        return jsonify({'success': False, 'msg': '该预约已取消', 'data': booking})
    if booking.get('status') == 'pending':
        return jsonify({'success': False, 'msg': '该预约尚未确认，无法核销', 'data': booking})
    # confirmed 状态可以核销
    db.execute(
        "UPDATE business_venue_bookings SET status='completed', updated_at=NOW() WHERE id=%s",
        [booking['id']]
    )
    booking['status'] = 'completed'
    return jsonify({'success': True, 'msg': '核销成功', 'data': booking})

# ============ 场地统计 ============

@app.route('/api/admin/venue-statistics', methods=['GET'])
def venue_statistics(user):
    """场地统计"""
    from business_common.statistics_service import get_stats_service
    venue_id = request.args.get('venue_id')
    stats = get_stats_service().venue_statistics(int(venue_id) if venue_id else None)
    return jsonify({'success': True, 'data': stats})


@app.route('/api/admin/points/members', methods=['GET'])
def admin_points_members():
    """会员积分列表"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    keyword = request.args.get('keyword', '')
    level = request.args.get('level')
    
    where = "1=1"
    params = []
    if keyword:
        where += " AND user_name LIKE %s"
        params.append('%' + keyword + '%')
    if level:
        where += " AND member_level=%s"
        params.append(level)
    where, params = add_scope_filter(where, params)
    
    total = db.get_total("SELECT COUNT(*) FROM business_members WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT id, user_id, user_name, phone, member_level, points, total_points "
        "FROM business_members WHERE " + where + " ORDER BY id DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {'items': items, 'total': total, 'page': page, 'page_size': page_size}})

@app.route('/api/admin/points/logs', methods=['GET'])
def admin_points_logs():
    """积分记录列表"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    user_id = request.args.get('user_id')
    log_type = request.args.get('type')
    keyword = request.args.get('keyword', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    where = "1=1"
    params = []
    if user_id:
        where += " AND user_id=%s"
        params.append(user_id)
    if log_type:
        where += " AND log_type=%s"
        params.append(log_type)
    if keyword:
        where += " AND (user_name LIKE %s OR phone LIKE %s)"
        kw = '%' + keyword + '%'
        params.extend([kw, kw])
    if date_from:
        where += " AND DATE(created_at)>=%s"
        params.append(date_from)
    if date_to:
        where += " AND DATE(created_at)<=%s"
        params.append(date_to)
    where, params = add_scope_filter(where, params)
    
    total = db.get_total("SELECT COUNT(*) FROM business_points_log WHERE " + where, params)
    offset = (page - 1) * page_size
    items = db.get_all(
        "SELECT id, user_id, user_name, log_type as type, points, balance_after, description, created_at "
        "FROM business_points_log WHERE " + where + " ORDER BY id DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items, 'total': total, 'page': page, 'page_size': page_size,
        'pages': (total + page_size - 1) // page_size if total else 0
    }})

@app.route('/api/admin/points/adjust', methods=['POST'])
@require_admin
@rate_limiter.rate_limit(limit=10, window_seconds=60)  # 限流：每分钟最多10次积分调整
def admin_points_adjust(user):
    """管理员调整会员积分"""
    data = request.get_json() or {}
    target_user_id = data.get('user_id')
    points = int(data.get('points', 0))
    adjust_type = data.get('type', 'add')  # add / reduce
    description = data.get('description', '管理员调整')
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    if not target_user_id:
        return jsonify({'success': False, 'msg': '用户ID不能为空'})
    if points <= 0:
        return jsonify({'success': False, 'msg': '积分数量必须大于0'})
    
    # 使用事务保证积分调整的原子性（修复并发安全问题）
    conn = db.get_db()
    try:
        cursor = conn.cursor()
        conn.begin()
        
        # 行锁读取当前积分（FOR UPDATE防止并发修改）
        cursor.execute(
            "SELECT points, user_name FROM business_members WHERE user_id=%s FOR UPDATE",
            [target_user_id]
        )
        member_row = cursor.fetchone()
        if not member_row:
            conn.rollback()
            return jsonify({'success': False, 'msg': '会员不存在或无权限'})
        
        current = member_row[0] or 0
        member_name = member_row[1] or ''
        
        delta = points if adjust_type != 'reduce' else -points
        new_balance = current + delta
        
        if new_balance < 0:
            conn.rollback()
            return jsonify({'success': False, 'msg': '积分余额不足，当前余额：' + str(current)})
        
        # 更新会员积分
        cursor.execute(
            "UPDATE business_members SET points=%s, total_points=total_points+%s WHERE user_id=%s",
            [new_balance, delta if delta > 0 else 0, target_user_id]
        )
        
        # 记录日志
        cursor.execute(
            "INSERT INTO business_points_log (user_id, user_name, log_type, points, balance_after, description, ec_id, project_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            [target_user_id, member_name, 'admin', delta, new_balance, description, ec_id, project_id]
        )
        
        conn.commit()
        
        # 发送积分变动通知
        try:
            notification.notify_points_change(target_user_id, delta, new_balance, description)
        
        # 记录审计日志
        log_admin_action('adjust_points', {
            'target_user_id': target_user_id,
            'points': points,
            'adjust_type': adjust_type,
            'description': description,
            'new_balance': new_balance
        })
        
        return jsonify({'success': True, 'msg': '积分调整成功', 'data': {'new_balance': new_balance}})
    except Exception as e:
        conn.rollback()
        logging.error(f"积分调整失败: {e}")
        return jsonify({'success': False, 'msg': '积分调整失败'})
    finally:
        try:
            cursor.close()
            conn.close()

@app.route('/api/admin/points/stats', methods=['GET'])
def admin_points_stats(user):
    """积分统计"""
    from business_common.statistics_service import get_stats_service
    stats = get_stats_service().admin_points_stats(user.get('ec_id'), user.get('project_id'))
    return jsonify({'success': True, 'data': stats})


@app.route('/api/admin/applications/stats/by-status', methods=['GET'])
def admin_applications_stats():
    """申请单各状态数量统计（一次性返回，避免前端4次请求）"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "deleted=0"
    params = []
    where, params = add_scope_filter(where, params)
    rows = db.get_all(
        "SELECT status, COUNT(*) as cnt FROM business_applications WHERE " + where + " GROUP BY status",
        params
    )
    result = {r['status']: r['cnt'] for r in (rows or [])}
    return jsonify({'success': True, 'data': result})

@app.route('/api/admin/applications/stats/by-type', methods=['GET'])
def admin_applications_by_type():
    """申请单各类型数量统计"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "deleted=0"
    params = []
    where, params = add_scope_filter(where, params)
    rows = db.get_all(
        "SELECT app_type, COUNT(*) as cnt FROM business_applications WHERE " + where + " GROUP BY app_type",
        params
    )
    result = {r['app_type']: r['cnt'] for r in (rows or [])}
    return jsonify({'success': True, 'data': result})

# ============ 订单趋势接口（近N日） ============

@app.route('/api/admin/orders/trend', methods=['GET'])
def admin_orders_trend():
    """近N天订单趋势（订单数+收入）"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    days = min(int(request.args.get('days', 7)), 30)
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    scope = "deleted=0"
    params = []
    if ec_id:
        scope += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        scope += " AND project_id=%s"; params.append(project_id)
    rows = db.get_all(
        f"SELECT DATE(created_at) as d, COUNT(*) as order_cnt, "
        f"COALESCE(SUM(CASE WHEN pay_status='paid' THEN actual_amount ELSE 0 END),0) as income "
        f"FROM business_orders WHERE {scope} AND created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY) "
        f"GROUP BY DATE(created_at) ORDER BY d ASC",
        params + [days]
    )
    # 填充缺失日期
    from datetime import date, timedelta
    date_map = {}
    for r in (rows or []):
        k = str(r['d']) if r.get('d') else ''
        if k:
            date_map[k] = {'order_cnt': r['order_cnt'], 'income': float(r['income'] or 0)}
    result = []
    for i in range(days - 1, -1, -1):
        d = (date.today() - timedelta(days=i)).strftime('%Y-%m-%d')
        result.append({'date': d, 'order_cnt': date_map.get(d, {}).get('order_cnt', 0), 'income': date_map.get(d, {}).get('income', 0)})
    return jsonify({'success': True, 'data': result})

# ============ 申请单趋势接口（近N日） ============

@app.route('/api/admin/applications/trend', methods=['GET'])
def admin_applications_trend():
    """近N天申请单趋势"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    days = min(int(request.args.get('days', 7)), 30)
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    scope = "deleted=0"
    params = []
    if ec_id:
        scope += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        scope += " AND project_id=%s"; params.append(project_id)
    rows = db.get_all(
        f"SELECT DATE(created_at) as d, COUNT(*) as app_cnt "
        f"FROM business_applications WHERE {scope} AND created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY) "
        f"GROUP BY DATE(created_at) ORDER BY d ASC",
        params + [days]
    )
    from datetime import date, timedelta
    date_map = {str(r['d']): r['app_cnt'] for r in (rows or []) if r.get('d')}
    result = []
    for i in range(days - 1, -1, -1):
        d = (date.today() - timedelta(days=i)).strftime('%Y-%m-%d')
        result.append({'date': d, 'app_cnt': date_map.get(d, 0)})
    return jsonify({'success': True, 'data': result})

# ============ 批量处理申请单 ============

@app.route('/api/admin/applications/batch', methods=['POST'])
def admin_batch_applications():
    """批量操作申请单（批量改状态/批量删除）"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    data = request.get_json() or {}
    action = data.get('action')  # 'delete' or 'status'
    ids = data.get('ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'success': False, 'msg': '请选择要操作的申请单'})
    if len(ids) > 50:
        return jsonify({'success': False, 'msg': '单次批量操作不超过50条'})
    
    # 修复：添加数据范围过滤
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    scope_filter = "deleted=0"
    scope_params = []
    if ec_id:
        scope_filter += " AND ec_id=%s"
        scope_params.append(ec_id)
    if project_id:
        scope_filter += " AND project_id=%s"
        scope_params.append(project_id)
    
    placeholders = ','.join(['%s'] * len(ids))
    
    if action == 'delete':
        sql = f"UPDATE business_applications SET deleted=1 WHERE id IN ({placeholders}) AND {scope_filter}"
        db.execute(sql, ids + scope_params)
        affected = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE id IN ({placeholders}) AND deleted=1", ids)
        log_admin_action('batch_delete_applications', {'ids': ids, 'count': affected})
        return jsonify({'success': True, 'msg': f'已删除 {affected} 条申请单'})
    elif action == 'status':
        new_status = data.get('status')
        if new_status not in ('processing', 'completed', 'rejected', 'pending'):
            return jsonify({'success': False, 'msg': '状态值无效'})
        sql = f"UPDATE business_applications SET status=%s, updated_at=NOW() WHERE id IN ({placeholders}) AND {scope_filter}"
        db.execute(sql, [new_status] + ids + scope_params)
        log_admin_action('batch_update_status', {'ids': ids, 'new_status': new_status})
        return jsonify({'success': True, 'msg': f'已更新申请单状态'})
    return jsonify({'success': False, 'msg': '不支持的操作类型'})

# ============ 用户积分详情（管理端查询某用户） ============

@app.route('/api/admin/users/<user_id>/points', methods=['GET'])
def admin_user_points(user_id):
    """查询某用户积分详情"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    member = db.get_one("SELECT user_id, user_name, phone, points, total_points, balance, member_level FROM business_members WHERE user_id=%s", [user_id])
    if not member:
        return jsonify({'success': False, 'msg': '用户不存在'})
    logs = db.get_all(
        "SELECT log_type as type, points, balance_after, description, created_at "
        "FROM business_points_log WHERE user_id=%s ORDER BY id DESC LIMIT 20",
        [user_id]
    )
    return jsonify({'success': True, 'data': {'member': member, 'recent_logs': logs or []}})

# ============ V30.0 会员360度画像 ============

@app.route('/api/admin/users/<int:user_id>/profile', methods=['GET'])
def admin_user_profile(user, user_id):
    """用户详情统计"""
    from business_common.statistics_service import get_stats_service
    result = get_stats_service().admin_user_profile(user_id)
    return jsonify(result)


@app.route('/api/admin/export/applications', methods=['GET'])
def export_applications():
    """导出申请单CSV"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "deleted=0"
    params = []
    status = request.args.get('status')
    app_type = request.args.get('app_type')
    if status:
        where += " AND status=%s"; params.append(status)
    if app_type:
        where += " AND app_type=%s"; params.append(app_type)
    where, params = add_scope_filter(where, params)
    items = db.get_all(
        "SELECT app_no,app_type,title,user_name,user_phone,status,priority,created_at,updated_at "
        "FROM business_applications WHERE " + where + " ORDER BY created_at DESC LIMIT 1000",
        params
    )
    import io, csv
    from flask import Response
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['申请单号', '类型', '标题', '申请人', '联系电话', '状态', '优先级', '提交时间', '更新时间'])
    type_map = {'repair': '报修', 'booking': '预约', 'complaint': '投诉', 'consult': '咨询', 'other': '其他'}
    status_map = {'pending': '待处理', 'processing': '处理中', 'completed': '已完成', 'rejected': '已拒绝', 'cancelled': '已撤销'}
    for item in (items or []):
        writer.writerow([
            item.get('app_no', ''), type_map.get(item.get('app_type', ''), item.get('app_type', '')),
            item.get('title', ''), item.get('user_name', ''), item.get('user_phone', ''),
            status_map.get(item.get('status', ''), item.get('status', '')),
            item.get('priority', 0), item.get('created_at', ''), item.get('updated_at', '')
        ])
    output.seek(0)
    return Response(
        '\ufeff' + output.getvalue(),  # BOM for Excel
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=applications.csv'}
    )

@app.route('/api/admin/export/orders', methods=['GET'])
def export_orders():
    """导出订单CSV（V15增强：支持时间段、订单类型、状态筛选）"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "deleted=0"
    params = []
    # V15: 自定义时间段筛选
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    if date_from:
        where += " AND created_at >= %s"; params.append(date_from)
    if date_to:
        where += " AND created_at <= %s"; params.append(date_to + ' 23:59:59')
    # V15: 订单状态筛选
    status = request.args.get('status')
    if status:
        where += " AND order_status = %s"; params.append(status)
    # V15: 订单类型筛选
    order_type = request.args.get('order_type')
    if order_type:
        where += " AND order_type = %s"; params.append(order_type)
    where, params = add_scope_filter(where, params)
    items = db.get_all(
        "SELECT order_no,order_type,user_name,user_phone,total_amount,actual_amount,order_status,pay_status,created_at "
        "FROM business_orders WHERE " + where + " ORDER BY created_at DESC LIMIT 1000",
        params
    )
    import io, csv
    from flask import Response
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['订单号', '类型', '用户', '电话', '总金额', '实付金额', '订单状态', '支付状态', '创建时间'])
    for item in (items or []):
        writer.writerow([
            item.get('order_no', ''), item.get('order_type', ''), item.get('user_name', ''),
            item.get('user_phone', ''), item.get('total_amount', 0), item.get('actual_amount', 0),
            item.get('order_status', ''), item.get('pay_status', ''), item.get('created_at', '')
        ])
    output.seek(0)
    return Response(
        '\ufeff' + output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=orders.csv'}
    )

# ============ 会员管理 ============

@app.route('/api/admin/members', methods=['GET'])
def admin_list_members():
    """会员列表查询"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    # 获取查询参数
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    phone = request.args.get('phone', '').strip()
    level = request.args.get('level', '').strip()
    
    # 构建查询条件
    where = "deleted=0"
    params = []
    
    # 数据隔离
    where, params = add_scope_filter(where, params)
    
    if phone:
        where += " AND phone LIKE %s"
        params.append(f'%{phone}%')
    
    if level:
        where += " AND member_level=%s"
        params.append(level)
    
    # 查询总数
    count_sql = f"SELECT COUNT(*) as cnt FROM business_members WHERE {where}"
    total = db.get_one(count_sql, params)
    total_count = total['cnt'] if total else 0
    
    # 查询列表
    offset = (page - 1) * page_size
    sql = f"""SELECT id, user_id, phone, member_name, member_level,
               points, total_points, created_at, updated_at
               FROM business_members
               WHERE {where}
               ORDER BY created_at DESC
               LIMIT %s OFFSET %s"""
    params.extend([page_size, offset])
    
    rows = db.get_all(sql, params)
    
    return jsonify({
        'success': True,
        'data': {
            'items': rows or [],
            'total': total_count,
            'page': page,
            'page_size': page_size
        }
    })

# ============ 会员等级分布统计 ============

@app.route('/api/admin/members/stats/by-level', methods=['GET'])
def admin_members_by_level():
    """会员等级分布统计"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "1=1"
    params = []
    where, params = add_scope_filter(where, params)
    rows = db.get_all(
        "SELECT member_level, COUNT(*) as cnt FROM business_members WHERE " + where + " GROUP BY member_level",
        params
    )
    result = {r['member_level']: r['cnt'] for r in (rows or [])}
    return jsonify({'success': True, 'data': result})

# ============ 场地热度排行榜 ============

@app.route('/api/admin/venues/stats/hot', methods=['GET'])
def admin_venues_hot():
    """场地热度排行：按预约次数和收入排序"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    scope = "vb.deleted=0"
    params = []
    if ec_id:
        scope += " AND vb.ec_id=%s"
        params.append(ec_id)
    if project_id:
        scope += " AND vb.project_id=%s"
        params.append(project_id)
    rows = db.get_all(
        "SELECT v.id, v.venue_name, v.venue_type, "
        "COUNT(vb.id) as book_cnt, "
        "COALESCE(SUM(CASE WHEN vb.pay_status='paid' THEN vb.total_price ELSE 0 END), 0) as total_income, "
        "COUNT(CASE WHEN vb.status='completed' THEN 1 END) as completed_cnt "
        "FROM business_venues v "
        "LEFT JOIN business_venue_bookings vb ON v.id=vb.venue_id AND " + scope + " "
        "WHERE v.deleted=0 "
        "GROUP BY v.id, v.venue_name, v.venue_type "
        "ORDER BY book_cnt DESC LIMIT 10",
        params
    )
    return jsonify({'success': True, 'data': rows or []})

# ============ 评价管理（回复和统计）============
# 注意：评价列表在 V21.0 新版本中定义（见文件后面）

@app.route('/api/admin/reviews/<review_id>/reply', methods=['POST'])
def admin_reply_review(review_id):
    """回复评价"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    data = request.get_json() or {}
    reply = data.get('reply', '').strip()

    if not reply:
        return jsonify({'success': False, 'msg': '回复内容不能为空'})

    try:
        db.execute(
            "UPDATE business_reviews SET reply=%s, replied_at=NOW() WHERE id=%s",
            [reply, review_id]
        )
        log_admin_action('reply_review', {'review_id': review_id, 'reply': reply})
        return jsonify({'success': True, 'msg': '回复成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/reviews/stats', methods=['GET'])
def admin_reviews_stats():
    """评价统计"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where, params = "deleted=0", []
    where, params = add_scope_filter(where, params)

    try:
        total = db.get_total("SELECT COUNT(*) FROM business_reviews WHERE " + where, params)
        avg_rating = db.get_one(
            "SELECT AVG(rating) as avg FROM business_reviews WHERE " + where, params
        )
        rating_stats = db.get_all(
            "SELECT rating, COUNT(*) as cnt FROM business_reviews WHERE " + where + " GROUP BY rating",
            params
        )
        rating_map = {r['rating']: r['cnt'] for r in rating_stats}
        return jsonify({'success': True, 'data': {
            'total': total,
            'avg_rating': round(float(avg_rating['avg'] or 0), 1) if avg_rating else 0,
            'rating_distribution': rating_map
        }})
        return jsonify({'success': True, 'data': {'total': 0, 'avg_rating': 0, 'rating_distribution': {}}})

# ============ 优惠券管理 ============

# ============ 优惠券管理 ============

@app.route('/api/admin/member-levels', methods=['GET'])
def admin_list_member_levels():
    """获取会员等级列表"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    try:
        levels = db.get_all("""
            SELECT * FROM business_member_levels 
            WHERE status='active' 
            ORDER BY sort_order ASC
        """)
        
        # 如果表不存在或无数据，返回默认等级
        if not levels:
            default_levels = [
                {'level_code': 'L1', 'level_name': '普通会员', 'min_amount': 0, 'discount_rate': 1.00, 'points_rate': 1.00, 'privileges': '["基础积分倍率"]', 'sort_order': 1},
                {'level_code': 'L2', 'level_name': '铜牌会员', 'min_amount': 500, 'discount_rate': 0.95, 'points_rate': 1.20, 'privileges': '["9.5折优惠", "积分1.2倍"]', 'sort_order': 2},
                {'level_code': 'L3', 'level_name': '银牌会员', 'min_amount': 2000, 'discount_rate': 0.90, 'points_rate': 1.50, 'privileges': '["9折优惠", "积分1.5倍", "优先预约"]', 'sort_order': 3},
                {'level_code': 'L4', 'level_name': '金牌会员', 'min_amount': 5000, 'discount_rate': 0.85, 'points_rate': 2.00, 'privileges': '["8.5折优惠", "积分2倍", "专属客服"]', 'sort_order': 4},
                {'level_code': 'L5', 'level_name': '钻石会员', 'min_amount': 10000, 'discount_rate': 0.80, 'points_rate': 3.00, 'privileges': '["8折优惠", "积分3倍", "免费场地"]', 'sort_order': 5},
            ]
            return jsonify({'success': True, 'data': default_levels})
        
        return jsonify({'success': True, 'data': levels or []})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/member-levels/save', methods=['POST'])
def admin_save_member_level():
    """保存会员等级"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    data = request.get_json() or {}
    level_code = data.get('level_code')
    level_name = data.get('level_name')
    
    if not level_code or not level_name:
        return jsonify({'success': False, 'msg': '请填写等级编码和名称'})
    
    try:
        # 检查是否已存在
        existing = db.get_one("SELECT id FROM business_member_levels WHERE level_code=%s", [level_code])
        
        if existing:
            # 更新
            db.execute("""
                UPDATE business_member_levels 
                SET level_name=%s, min_amount=%s, discount_rate=%s, points_rate=%s, 
                    privileges=%s, sort_order=%s, updated_at=NOW()
                WHERE level_code=%s
            """, [level_name, data.get('min_amount', 0), data.get('discount_rate', 1.00),
                  data.get('points_rate', 1.00), data.get('privileges', '[]'),
                  data.get('sort_order', 0), level_code])
            log_admin_action('update_member_level', {'level_code': level_code})
            return jsonify({'success': True, 'msg': '修改成功'})
        else:
            # 新增
            db.execute("""
                INSERT INTO business_member_levels 
                (level_code, level_name, min_amount, discount_rate, points_rate, privileges, sort_order, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
            """, [level_code, level_name, data.get('min_amount', 0), data.get('discount_rate', 1.00),
                  data.get('points_rate', 1.00), data.get('privileges', '[]'), data.get('sort_order', 0)])
            log_admin_action('create_member_level', {'level_code': level_code})
            return jsonify({'success': True, 'msg': '创建成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/member-levels/statistics', methods=['GET'])
def admin_member_levels_statistics():
    """会员等级统计"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        where = "deleted=0"
        params = []
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        
        stats = db.get_all(f"""
            SELECT 
                COALESCE(m.member_level, 'L1') as level_code,
                COUNT(*) as count,
                SUM(COALESCE(m.total_consume, 0)) as total_amount,
                AVG(COALESCE(m.total_consume, 0)) as avg_amount
            FROM business_members m
            WHERE {where}
            GROUP BY m.member_level
            ORDER BY m.member_level
        """, params)
        
        # 获取等级名称映射
        levels = db.get_all("SELECT level_code, level_name FROM business_member_levels")
        level_names = {l['level_code']: l['level_name'] for l in levels}
        
        for stat in stats:
            stat['level_name'] = level_names.get(stat['level_code'], '普通会员')
        
        return jsonify({'success': True, 'data': stats or []})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/coupons', methods=['GET'])
def admin_list_coupons():
    """优惠券列表"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    
    where = "1=1"
    params = []
    if status:
        where += " AND status=%s"
        params.append(status)
    where, params = add_scope_filter(where, params)
    
    try:
        total = db.get_total("SELECT COUNT(*) FROM business_coupons WHERE " + where, params)
        offset = (page - 1) * page_size
        items = db.get_all(
            """SELECT id, coupon_name, coupon_type, discount_value, min_amount, max_discount,
                      points_cost, total_count, used_count, valid_from, valid_until, status, created_at
               FROM business_coupons WHERE """ + where + " ORDER BY id DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        return jsonify({'success': True, 'data': {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size
        }})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/coupons', methods=['POST'])
@require_admin
def admin_create_coupon(user):
    """创建优惠券"""
    data = request.get_json() or {}
    coupon_name = data.get('coupon_name', '').strip()
    coupon_type = data.get('coupon_type', 'cash')
    discount_value = float(data.get('discount_value', 0))
    min_amount = float(data.get('min_amount', 0))
    max_discount = data.get('max_discount')
    points_cost = int(data.get('points_cost', 0))
    total_count = int(data.get('total_count', 0))
    valid_from = data.get('valid_from')
    valid_until = data.get('valid_until')
    
    if not coupon_name:
        return jsonify({'success': False, 'msg': '优惠券名称不能为空'})
    if discount_value <= 0:
        return jsonify({'success': False, 'msg': '优惠值必须大于0'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        db.execute(
            """INSERT INTO business_coupons 
               (coupon_name, coupon_type, discount_value, min_amount, max_discount, 
                points_cost, total_count, valid_from, valid_until, ec_id, project_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            [coupon_name, coupon_type, discount_value, min_amount, max_discount,
             points_cost, total_count, valid_from, valid_until, ec_id, project_id]
        )
        log_admin_action('create_coupon', {'coupon_name': coupon_name, 'coupon_type': coupon_type})
        return jsonify({'success': True, 'msg': '优惠券创建成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/coupons/<coupon_id>', methods=['PUT'])
def admin_update_coupon(coupon_id):
    """更新优惠券"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    data = request.get_json() or {}
    
    allowed_fields = ['coupon_name', 'discount_value', 'min_amount', 'max_discount', 
                      'points_cost', 'total_count', 'valid_from', 'valid_until', 'status']
    updates = []
    params = []
    for f in allowed_fields:
        if f in data:
            updates.append(f + "=%s")
            params.append(data[f])
    
    if not updates:
        return jsonify({'success': False, 'msg': '没有要更新的字段'})
    
    params.append(coupon_id)
    try:
        db.execute("UPDATE business_coupons SET " + ", ".join(updates) + " WHERE id=%s", params)
        log_admin_action('update_coupon', {'coupon_id': coupon_id})
        return jsonify({'success': True, 'msg': '更新成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/coupons/<coupon_id>/issue', methods=['POST'])
@require_admin
def admin_issue_coupon(user, coupon_id):
    """发放优惠券给用户"""
    data = request.get_json() or {}
    user_ids = data.get('user_ids', [])  # 用户ID列表
    
    if not user_ids or not isinstance(user_ids, list):
        return jsonify({'success': False, 'msg': '请提供用户ID列表'})
    if len(user_ids) > 100:
        return jsonify({'success': False, 'msg': '单次发放不超过100人'})
    
    # 获取优惠券信息
    coupon = db.get_one("SELECT * FROM business_coupons WHERE id=%s AND status='active'", [coupon_id])
    if not coupon:
        return jsonify({'success': False, 'msg': '优惠券不存在或已失效'})
    
    import uuid
    count = 0
    for uid in user_ids:
        coupon_code = uuid.uuid4().hex[:12].upper()
        try:
            db.execute(
                """INSERT INTO business_user_coupons (coupon_id, user_id, coupon_code, ec_id, project_id)
                   VALUES (%s, %s, %s, %s, %s)""",
                [coupon_id, uid, coupon_code, user.get('ec_id'), user.get('project_id')]
            )
            count += 1
    
    log_admin_action('issue_coupon', {'coupon_id': coupon_id, 'user_count': len(user_ids), 'success_count': count})
    return jsonify({'success': True, 'msg': f'成功发放 {count} 张优惠券'})

@app.route('/api/admin/coupons/<coupon_id>/targeted-issue', methods=['POST'])
@require_admin
def admin_targeted_issue_coupon(user, coupon_id):
    """
    V30.0 定向发放优惠券：按会员等级/消费区间/签到活跃度筛选目标人群
    V31.0 增强：新增直接传入 user_ids 列表支持（用于 RFM 分群批量操作）
    支持参数：
      - user_ids: [uid1, uid2, ...] 直接指定用户列表（优先级最高）
      - level_list: ['gold','platinum','diamond']  会员等级列表
      - min_total_consume / max_total_consume: 消费区间
      - min_checkin_streak: 最低连续签到天数（活跃用户）
      - inactive_days: 最近N天未下单（促活用途）
      - dry_run: true 仅预估人数，不实际发放
      - max_count: 最多发放人数上限（默认1000）
    """
    data = request.get_json() or {}
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    dry_run = bool(data.get('dry_run', False))
    max_count = min(int(data.get('max_count', 1000)), 5000)

    # 校验优惠券
    coupon = db.get_one("SELECT * FROM business_coupons WHERE id=%s AND status='active'", [coupon_id])
    if not coupon:
        return jsonify({'success': False, 'msg': '优惠券不存在或已失效'})
    if int(coupon.get('stock') or 0) <= 0 and not coupon.get('unlimited_stock'):
        return jsonify({'success': False, 'msg': '优惠券库存不足'})

    # V31.0 新增：如果直接传了 user_ids，优先使用
    direct_user_ids = data.get('user_ids')
    if direct_user_ids and isinstance(direct_user_ids, list) and len(direct_user_ids) > 0:
        # 限制最多5000个
        direct_user_ids = [str(uid) for uid in direct_user_ids[:5000]]
        if len(direct_user_ids) == 0:
            return jsonify({'success': False, 'msg': '用户列表为空'})
        placeholders = ','.join(['%s'] * len(direct_user_ids))
        # 排除已持有该券的用户
        target_users = db.get_all(
            f"""SELECT m.user_id, m.user_name, m.phone, m.member_level
                FROM business_members m
                WHERE m.user_id IN ({placeholders})
                AND m.user_id NOT IN (SELECT user_id FROM business_user_coupons WHERE coupon_id=%s)
                LIMIT %s""",
            direct_user_ids + [coupon_id, max_count]
        ) or []
        est_count = len(target_users)
        if dry_run:
            sample = [{'user_id': u['user_id'], 'user_name': u.get('user_name',''), 'level': u.get('member_level','')}
                      for u in target_users[:10]]
            return jsonify({'success': True, 'data': {
                'estimated_count': est_count,
                'issued_count': est_count,
                'sample_users': sample,
                'message': f'将向 {est_count} 名选定会员发放优惠券'
            }})
        if not target_users:
            return jsonify({'success': False, 'msg': '所选用户均已持有该券'})
        import uuid as _uuid
        count = 0
        expire_days = int(coupon.get('expire_days') or 30)
        for u in target_users:
            coupon_code = _uuid.uuid4().hex[:12].upper()
            try:
                db.execute(
                    """INSERT INTO business_user_coupons
                       (coupon_id, user_id, coupon_code, ec_id, project_id, expire_at)
                       VALUES (%s, %s, %s, %s, %s, DATE_ADD(NOW(), INTERVAL %s DAY))""",
                    [coupon_id, u['user_id'], coupon_code, ec_id, project_id, expire_days]
                )
                try:
                    from business_common.notification import send_notification
                    send_notification(
                        user_id=u['user_id'],
                        title='您收到一张优惠券',
                        content=f"恭喜！您获得了「{coupon.get('coupon_name', '优惠券')}」，有效期{expire_days}天，快去使用吧！",
                        notify_type='coupon',
                        ec_id=ec_id, project_id=project_id
                    )
                except Exception:
                    pass
                count += 1
            except Exception:
                pass
        log_admin_action('targeted_issue_coupon', {
            'coupon_id': coupon_id, 'mode': 'direct_user_ids',
            'target_count': est_count, 'success_count': count
        })
        return jsonify({'success': True, 'msg': f'发放完成，成功发放 {count} 张',
                        'data': {'success_count': count, 'issued_count': count, 'total_target': est_count}})

    # 构建会员筛选条件
    where = "1=1"
    params = []
    if ec_id:
        where += " AND (m.ec_id=%s OR m.ec_id IS NULL)"; params.append(ec_id)
    if project_id:
        where += " AND (m.project_id=%s OR m.project_id IS NULL)"; params.append(project_id)

    # 会员等级筛选
    level_list = data.get('level_list', [])
    if level_list:
        placeholders = ','.join(['%s'] * len(level_list))
        where += f" AND m.member_level IN ({placeholders})"
        params.extend(level_list)

    # 消费区间筛选
    min_consume = data.get('min_total_consume')
    max_consume = data.get('max_total_consume')
    if min_consume is not None:
        where += " AND m.total_consume >= %s"; params.append(float(min_consume))
    if max_consume is not None:
        where += " AND m.total_consume <= %s"; params.append(float(max_consume))

    # 连续签到活跃用户
    min_streak = data.get('min_checkin_streak')
    if min_streak is not None:
        where += " AND m.checkin_streak >= %s"; params.append(int(min_streak))

    # 沉睡用户（N天未下单）
    inactive_days = data.get('inactive_days')
    if inactive_days is not None:
        where += """ AND m.user_id NOT IN (
            SELECT DISTINCT user_id FROM business_orders
            WHERE deleted=0 AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        )"""
        params.append(int(inactive_days))

    # 排除已有该券的用户（去重）
    where += " AND m.user_id NOT IN (SELECT user_id FROM business_user_coupons WHERE coupon_id=%s)"
    params.append(coupon_id)

    try:
        # 查询目标用户
        target_users = db.get_all(
            f"""SELECT m.user_id, m.user_name, m.phone, m.member_level
                FROM business_members m
                WHERE {where}
                LIMIT %s""",
            params + [max_count]
        ) or []

        est_count = len(target_users)

        if dry_run:
            # 预估模式：返回人数和样本
            sample = [{'user_id': u['user_id'], 'user_name': u.get('user_name',''), 'level': u.get('member_level','')}
                      for u in target_users[:10]]
            return jsonify({'success': True, 'data': {
                'estimated_count': est_count,
                'sample_users': sample,
                'message': f'预计将向 {est_count} 名会员发放优惠券'
            }})

        if not target_users:
            return jsonify({'success': False, 'msg': '未找到符合条件的会员'})

        # 实际发放
        import uuid as _uuid
        count = 0
        expire_days = int(coupon.get('expire_days') or 30)
        for u in target_users:
            coupon_code = _uuid.uuid4().hex[:12].upper()
            try:
                db.execute(
                    """INSERT INTO business_user_coupons
                       (coupon_id, user_id, coupon_code, ec_id, project_id, expire_at)
                       VALUES (%s, %s, %s, %s, %s, DATE_ADD(NOW(), INTERVAL %s DAY))""",
                    [coupon_id, u['user_id'], coupon_code,
                     ec_id, project_id, expire_days]
                )
                # 发站内通知
                try:
                    from business_common.notification import send_notification
                    send_notification(
                        user_id=u['user_id'],
                        title='您收到一张优惠券',
                        content=f"恭喜！您获得了「{coupon.get('coupon_name', '优惠券')}」，有效期{expire_days}天，快去使用吧！",
                        notify_type='coupon_grant',
                        ec_id=ec_id, project_id=project_id
                    )
                except Exception:
                    pass
                count += 1
            except Exception:
                pass

        log_admin_action('targeted_issue_coupon', {
            'coupon_id': coupon_id,
            'filter_params': data,
            'target_count': est_count,
            'success_count': count
        })
        return jsonify({'success': True, 'msg': f'定向发放完成，成功发放 {count} 张',
                        'data': {'success_count': count, 'total_target': est_count}})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/coupons/target-preview', methods=['POST'])
@require_admin
def admin_coupon_target_preview(user):
    """V30.0 定向发放预估人数（快捷接口，不需要 coupon_id）"""
    data = request.get_json() or {}
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')

    where = "1=1"
    params = []
    if ec_id:
        where += " AND (ec_id=%s OR ec_id IS NULL)"; params.append(ec_id)
    if project_id:
        where += " AND (project_id=%s OR project_id IS NULL)"; params.append(project_id)

    level_list = data.get('level_list', [])
    if level_list:
        placeholders = ','.join(['%s'] * len(level_list))
        where += f" AND member_level IN ({placeholders})"
        params.extend(level_list)

    min_consume = data.get('min_total_consume')
    max_consume = data.get('max_total_consume')
    if min_consume is not None:
        where += " AND total_consume >= %s"; params.append(float(min_consume))
    if max_consume is not None:
        where += " AND total_consume <= %s"; params.append(float(max_consume))

    min_streak = data.get('min_checkin_streak')
    if min_streak is not None:
        where += " AND checkin_streak >= %s"; params.append(int(min_streak))

    try:
        count = db.get_total(f"SELECT COUNT(*) FROM business_members WHERE {where}", params)
        return jsonify({'success': True, 'data': {'estimated_count': count}})
        return jsonify({'success': False, 'msg': '预估失败'})

# ============ 反馈管理 ============

@app.route('/api/admin/feedback', methods=['GET'])
def admin_list_feedback():
    """反馈列表"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    feedback_type = request.args.get('feedback_type')
    keyword = request.args.get('keyword', '')

    where = "deleted=0"
    params = []
    if status:
        where += " AND status=%s"; params.append(status)
    if feedback_type:
        where += " AND feedback_type=%s"; params.append(feedback_type)
    if keyword:
        where += " AND (title LIKE %s OR user_name LIKE %s OR content LIKE %s)"
        kw = '%' + keyword + '%'
        params.extend([kw, kw, kw])
    where, params = add_scope_filter(where, params)

    try:
        total = db.get_total("SELECT COUNT(*) FROM business_feedback WHERE " + where, params)
        offset = (page - 1) * page_size
        items = db.get_all(
            "SELECT id, user_id, user_name, feedback_type, title, content, contact, status, reply, replied_by, replied_at, created_at "
            "FROM business_feedback WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        return jsonify({'success': True, 'data': {
            'items': items or [], 'total': total, 'page': page, 'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0}})

@app.route('/api/admin/feedback/<fb_id>/reply', methods=['POST'])
@require_admin
def admin_reply_feedback(user, fb_id):
    """回复反馈"""
    data = request.get_json() or {}
    reply = data.get('reply', '').strip()
    status = data.get('status', 'replied')
    if not reply:
        return jsonify({'success': False, 'msg': '回复内容不能为空'})
    try:
        db.execute(
            "UPDATE business_feedback SET reply=%s, replied_by=%s, replied_at=NOW(), status=%s WHERE id=%s",
            [reply, user.get('user_name', ''), status, fb_id]
        )
        # 通知用户反馈已回复
        try:
            fb = db.get_one("SELECT user_id, title FROM business_feedback WHERE id=%s", [fb_id])
            if fb:
                notification.send_notification(
                    fb['user_id'], '您的意见反馈已回复',
                    f"关于「{fb['title']}」的反馈已回复：{reply[:100]}",
                    notify_type='system', ref_id=str(fb_id), ref_type='feedback'
                )
        log_admin_action('reply_feedback', {'feedback_id': fb_id, 'reply': reply})
        return jsonify({'success': True, 'msg': '回复成功'})
        return jsonify({'success': False, 'msg': '回复失败'})

# ============ 通知管理 ============

@app.route('/api/admin/notifications', methods=['GET'])
def admin_list_notifications():
    """通知列表（管理端查看所有通知）"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    notify_type = request.args.get('notify_type')
    is_read = request.args.get('is_read')
    keyword = request.args.get('keyword', '')

    where = "deleted=0"
    params = []
    if notify_type:
        where += " AND notify_type=%s"; params.append(notify_type)
    if is_read is not None and is_read != '':
        read_val = 1 if is_read in ('true', '1') else 0
        where += " AND is_read=%s"; params.append(read_val)
    if keyword:
        where += " AND (user_id LIKE %s OR title LIKE %s OR content LIKE %s)"
        kw = '%' + keyword + '%'
        params.extend([kw, kw, kw])
    where, params = add_scope_filter(where, params)

    try:
        total = db.get_total("SELECT COUNT(*) FROM business_notifications WHERE " + where, params)
        unread = db.get_total("SELECT COUNT(*) FROM business_notifications WHERE " + where + " AND is_read=0", params.copy())
        offset = (page - 1) * page_size
        items = db.get_all(
            "SELECT id, user_id, title, content, notify_type, is_read, ref_id, ref_type, created_at "
            "FROM business_notifications WHERE " + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        return jsonify({'success': True, 'data': {
            'items': items or [], 'total': total, 'page': page, 'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0,
            'unread_count': unread
        }})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'pages': 0, 'unread_count': 0}})

@app.route('/api/admin/notifications/send', methods=['POST'])
@require_admin
def admin_send_notification(user):
    """管理员发送系统通知给指定用户"""
    data = request.get_json() or {}
    target_user_id = data.get('user_id', '').strip()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    notify_type = data.get('notify_type', 'system')

    if not target_user_id:
        return jsonify({'success': False, 'msg': '请输入用户ID'})
    if not title:
        return jsonify({'success': False, 'msg': '请输入标题'})
    if not content:
        return jsonify({'success': False, 'msg': '请输入内容'})
    if len(title) > 200:
        return jsonify({'success': False, 'msg': '标题不能超过200字'})

    # XSS防护
    import html as html_mod
    title = html_mod.escape(title)
    content = html_mod.escape(content)

    try:
        notification.send_notification(
            target_user_id, title, content,
            notify_type=notify_type,
            ec_id=user.get('ec_id'),
            project_id=user.get('project_id')
        )
        log_admin_action('send_notification', {'user_id': target_user_id, 'title': title, 'type': notify_type})
        return jsonify({'success': True, 'msg': '通知发送成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/notifications/broadcast', methods=['POST'])
@require_admin
def admin_broadcast_notification(user):
    """管理员群发通知给所有会员"""
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    notify_type = data.get('notify_type', 'system')

    if not title or not content:
        return jsonify({'success': False, 'msg': '标题和内容不能为空'})

    import html as html_mod
    title = html_mod.escape(title)
    content = html_mod.escape(content)

    ec_id = user.get('ec_id')
    project_id = user.get('project_id')

    # 获取本项目所有会员
    where = "1=1"
    params = []
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)

    members = db.get_all("SELECT user_id FROM business_members WHERE " + where, params)
    count = 0
    for m in (members or []):
        try:
            notification.send_notification(m['user_id'], title, content, notify_type=notify_type, ec_id=ec_id, project_id=project_id)
            count += 1

    log_admin_action('broadcast_notification', {'title': title, 'count': count})
    return jsonify({'success': True, 'msg': f'已发送给 {count} 位用户'})

# ============ 增强导出(使用导出服务) ============

@app.route('/api/admin/export/bookings', methods=['GET'])
def export_bookings():
    """导出预约CSV"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "vb.deleted=0"
    params = []
    where, params = add_scope_filter(where, params, 'vb')
    return export_service.export_bookings_csv(where, params)

@app.route('/api/admin/export/members', methods=['GET'])
def export_members():
    """导出会员CSV（V31.0 增强：支持关键字和等级过滤）"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    where = "1=1"
    params = []
    where, params = add_scope_filter(where, params)
    keyword = request.args.get('keyword', '').strip()
    member_level = request.args.get('member_level', '').strip()
    if keyword:
        where += " AND (user_name LIKE %s OR phone LIKE %s)"
        params.extend([f'%{keyword}%', f'%{keyword}%'])
    if member_level:
        where += " AND member_level=%s"
        params.append(member_level)
    return export_service.export_members_csv(where, params)

@app.route('/api/admin/export/reviews', methods=['GET'])
@require_admin
def export_reviews(user):
    """V31.0: 导出评价数据CSV"""
    import io, csv
    from flask import make_response
    
    where = "r.deleted=0"
    params = []
    ec_id, project_id = user.get('ec_id'), user.get('project_id')
    if ec_id:
        where += " AND r.ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND r.project_id=%s"; params.append(project_id)
    
    target_type = request.args.get('target_type', '').strip()
    min_rating = request.args.get('min_rating', type=int)
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    
    if target_type:
        where += " AND r.target_type=%s"; params.append(target_type)
    if min_rating:
        where += " AND r.rating>=%s"; params.append(min_rating)
    if date_from:
        where += " AND DATE(r.created_at)>=%s"; params.append(date_from)
    if date_to:
        where += " AND DATE(r.created_at)<=%s"; params.append(date_to)

    try:
        rows = db.get_all(
            f"""SELECT r.id, r.user_name, r.rating, r.target_type, r.target_id,
                       r.content, r.reply, r.is_anonymous, r.created_at
                FROM business_reviews r
                WHERE {where}
                ORDER BY r.created_at DESC LIMIT 10000""",
            params
        ) or []

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', '用户名', '评分', '评价类型', '对象ID', '评价内容', '商家回复', '是否匿名', '评价时间'])
        type_map = {'product': '商品', 'venue': '场馆', 'shop': '门店', 'order': '订单', 'booking': '预约'}
        for r in rows:
            writer.writerow([
                r.get('id'), 
                '匿名用户' if r.get('is_anonymous') else r.get('user_name', ''),
                r.get('rating', ''),
                type_map.get(r.get('target_type', ''), r.get('target_type', '')),
                r.get('target_id', ''),
                r.get('content', ''),
                r.get('reply', ''),
                '是' if r.get('is_anonymous') else '否',
                str(r.get('created_at', ''))[:19]
            ])
        
        content = '\ufeff' + output.getvalue()  # UTF-8 BOM for Excel
        response = make_response(content)
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=reviews_{time.strftime("%Y%m%d")}.csv'
        log_admin_action('export_reviews', {'count': len(rows)})
        return response
        return jsonify({'success': False, 'msg': '导出失败'})
>>>>>>> Stashed changes

# ============ 健康检查 ============

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'success': True, 'module': 'admin-web', 'status': 'ok'})


<<<<<<< Updated upstream
# ============ 静态文件 ============
=======
@app.route('/debugtest')
def debugtest():
    return "DEBUG_TEST_OK"

# ============ 公告管理 ============

@app.route('/api/admin/notices', methods=['GET'])
@require_admin
def admin_list_notices(user):
    """公告列表"""
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    notice_type = request.args.get('notice_type')
    keyword = request.args.get('keyword', '')
    
    where = "deleted=0"
    params = []
    if status:
        where += " AND status=%s"; params.append(status)
    if notice_type:
        where += " AND notice_type=%s"; params.append(notice_type)
    if keyword:
        where += " AND title LIKE %s"; params.append(f'%{keyword}%')
    where, params = add_scope_filter(where, params)
    
    try:
        total = db.get_total("SELECT COUNT(*) FROM business_notices WHERE " + where, params)
        offset = (page - 1) * page_size
        items = db.get_all(
            "SELECT id, title, notice_type, importance, status, start_date, end_date, "
            "created_by_name, created_at, updated_at "
            "FROM business_notices WHERE " + where + " ORDER BY importance DESC, created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        return jsonify({'success': True, 'data': {
            'items': items or [], 'total': total, 'page': page, 'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }})
        return jsonify({'success': False, 'msg': '查询失败'})

@app.route('/api/admin/notices', methods=['POST'])
@require_admin
@rate_limiter.rate_limit(limit=10, window_seconds=60)
def admin_create_notice(user):
    """创建公告"""
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    notice_type = data.get('notice_type', 'general')
    importance = int(data.get('importance', 0))
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    status = data.get('status', 'published')
    
    if not title:
        return jsonify({'success': False, 'msg': '公告标题不能为空'})
    if not content:
        return jsonify({'success': False, 'msg': '公告内容不能为空'})
    if len(title) > 255:
        return jsonify({'success': False, 'msg': '标题不能超过255字符'})
    if notice_type not in ('general', 'activity', 'urgent'):
        notice_type = 'general'
    if status not in ('published', 'draft'):
        status = 'draft'
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        import html as html_mod
        title = html_mod.escape(title)
        content = html_mod.escape(content)
        
        db.execute(
            """INSERT INTO business_notices 
               (title, content, notice_type, importance, status, start_date, end_date,
                ec_id, project_id, created_by, created_by_name)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            [title, content, notice_type, importance, status, start_date or None, end_date or None,
             ec_id, project_id, user.get('user_id'), user.get('user_name', '')]
        )
        log_admin_action('create_notice', {'title': title, 'type': notice_type})
        return jsonify({'success': True, 'msg': '公告创建成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/notices/<notice_id>', methods=['GET'])
@require_admin
def admin_get_notice(user, notice_id):
    """公告详情"""
    try:
        notice = db.get_one("SELECT * FROM business_notices WHERE id=%s AND deleted=0", [notice_id])
        if not notice:
            return jsonify({'success': False, 'msg': '公告不存在'})
        return jsonify({'success': True, 'data': notice})
    except Exception as e:
        return jsonify({'success': False, 'msg': '查询失败'})

@app.route('/api/admin/notices/<notice_id>', methods=['PUT'])
@require_admin
@rate_limiter.rate_limit(limit=10, window_seconds=60)
def admin_update_notice(user, notice_id):
    """更新公告"""
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    notice_type = data.get('notice_type', 'general')
    importance = int(data.get('importance', 0))
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    status = data.get('status', 'published')
    
    if not title:
        return jsonify({'success': False, 'msg': '公告标题不能为空'})
    
    try:
        import html as html_mod
        title = html_mod.escape(title)
        content = html_mod.escape(content)
        
        db.execute(
            """UPDATE business_notices SET title=%s, content=%s, notice_type=%s, importance=%s,
               status=%s, start_date=%s, end_date=%s, updated_at=NOW() WHERE id=%s AND deleted=0""",
            [title, content, notice_type, importance, status,
             start_date or None, end_date or None, notice_id]
        )
        log_admin_action('update_notice', {'id': notice_id, 'title': title})
        return jsonify({'success': True, 'msg': '公告更新成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/notices/<notice_id>', methods=['DELETE'])
@require_admin
@rate_limiter.rate_limit(limit=5, window_seconds=60)
def admin_delete_notice(user, notice_id):
    """删除公告（软删除）"""
    try:
        db.execute("UPDATE business_notices SET deleted=1, updated_at=NOW() WHERE id=%s", [notice_id])
        log_admin_action('delete_notice', {'id': notice_id})
        return jsonify({'success': True, 'msg': '公告已删除'})
    except Exception as e:
        return jsonify({'success': False, 'msg': '删除失败'})

# ============ 订单明细查询 ============

@app.route('/api/admin/orders/<order_id>/items', methods=['GET'])
@require_admin
def admin_get_order_items(user, order_id):
    """获取订单明细"""
    try:
        items = db.get_all(
            """SELECT oi.id, oi.product_id, oi.product_name, oi.price, oi.quantity, oi.subtotal,
                      p.images as product_images, p.category as product_category
               FROM business_order_items oi
               LEFT JOIN business_products p ON oi.product_id = p.id
               WHERE oi.order_id=%s""",
            [order_id]
        )
        return jsonify({'success': True, 'data': {'items': items or []}})

    except Exception as e:
        # 表可能不存在
        logging.warning(f"订单明细查询失败: {e}")
        return jsonify({'success': True, 'data': {'items': []}})

# ============ V14.0 商品管理增强 ============

@app.route('/api/admin/products/batch-status', methods=['POST'])
@require_admin
def admin_batch_product_status(user):
    """批量修改商品状态（上架/下架）"""
    data = request.get_json() or {}
    ids = data.get('ids', [])
    status = data.get('status')

    if not ids or not isinstance(ids, list):
        return jsonify({'success': False, 'msg': '请选择商品'})
    if len(ids) > 50:
        return jsonify({'success': False, 'msg': '单次操作不超过50个'})
    if status not in ('active', 'inactive'):
        return jsonify({'success': False, 'msg': '状态值无效，仅支持active/inactive'})

    ec_id, project_id = get_data_scope()
    where = "id IN (%s)" % ','.join(['%s'] * len(ids))
    params = list(ids)
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)

    try:
        db.execute(f"UPDATE business_products SET status=%s, updated_at=NOW() WHERE {where}", [status] + params)
        log_admin_action('batch_product_status', {'ids': ids, 'status': status})
        return jsonify({'success': True, 'msg': f'已更新 {len(ids)} 个商品状态'})
        return jsonify({'success': False, 'msg': '操作失败'})

@app.route('/api/admin/product-categories', methods=['GET'])
def admin_list_product_categories():
    """商品分类列表"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})

    where = "1=1"
    params = []
    where, params = add_scope_filter(where, params)

    try:
        items = db.get_all(
            "SELECT id, category_name, parent_id, icon, sort_order, status, created_at "
            "FROM business_product_categories WHERE " + where + " ORDER BY sort_order ASC, id ASC",
            params
        )
        # 构建树形结构
        categories = items or []
        tree = [c for c in categories if c.get('parent_id', 0) == 0]
        for cat in tree:
            cat['children'] = [c for c in categories if c.get('parent_id') == cat['id']]
        return jsonify({'success': True, 'data': {'items': tree, 'flat': categories}})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/product-categories', methods=['POST'])
@require_admin
def admin_create_product_category(user):
    """创建商品分类"""
    data = request.get_json() or {}
    category_name = (data.get('category_name', '') or '').strip()
    parent_id = int(data.get('parent_id', 0))
    icon = data.get('icon', '')
    sort_order = int(data.get('sort_order', 0))

    if not category_name:
        return jsonify({'success': False, 'msg': '分类名称不能为空'})
    if len(category_name) > 100:
        return jsonify({'success': False, 'msg': '分类名称不能超过100字'})

    ec_id = user.get('ec_id')
    project_id = user.get('project_id')

    try:
        db.execute(
            "INSERT INTO business_product_categories (category_name, parent_id, icon, sort_order, ec_id, project_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            [category_name, parent_id, icon, sort_order, ec_id, project_id]
        )
        log_admin_action('create_category', {'category_name': category_name})
        return jsonify({'success': True, 'msg': '分类创建成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/product-categories/<cat_id>', methods=['PUT'])
def admin_update_product_category(cat_id):
    """更新商品分类"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    data = request.get_json() or {}

    allowed = ['category_name', 'parent_id', 'icon', 'sort_order', 'status']
    updates = []
    params = []
    for f in allowed:
        if f in data:
            updates.append(f + "=%s")
            params.append(data[f])

    if not updates:
        return jsonify({'success': False, 'msg': '没有更新内容'})

    updates.append("updated_at=NOW()")
    params.append(cat_id)

    try:
        db.execute("UPDATE business_product_categories SET " + ", ".join(updates) + " WHERE id=%s", params)
        log_admin_action('update_category', {'id': cat_id})
        return jsonify({'success': True, 'msg': '更新成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/product-categories/<cat_id>', methods=['DELETE'])
@require_admin
def admin_delete_product_category(user, cat_id):
    """删除商品分类"""
    try:
        # 检查是否有子分类
        children = db.get_total("SELECT COUNT(*) FROM business_product_categories WHERE parent_id=%s", [cat_id])
        if children > 0:
            return jsonify({'success': False, 'msg': '该分类下有子分类，请先删除子分类'})

        # 检查是否有商品使用该分类
        products = db.get_total("SELECT COUNT(*) FROM business_products WHERE category=%s AND deleted=0", [cat_id])
        if products > 0:
            return jsonify({'success': False, 'msg': f'该分类下有 {products} 个商品，请先转移商品'})

        db.execute("DELETE FROM business_product_categories WHERE id=%s", [cat_id])
        log_admin_action('delete_category', {'id': cat_id})
        return jsonify({'success': True, 'msg': '分类已删除'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/products/stock-warning', methods=['GET'])
@require_admin
def admin_stock_warning_notify(user):
    """V14新增：库存预警通知（标记已通知，避免重复通知）"""
    threshold = int(request.args.get('threshold', 5))
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')

    where = "deleted=0 AND status='active' AND stock <= %s AND (low_stock_notified=0 OR low_stock_notified IS NULL)"
    params = [threshold]
    if ec_id:
        where += " AND ec_id=%s"; params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"; params.append(project_id)

    try:
        items = db.get_all(
            f"SELECT id, product_name, category, price, stock, sales_count FROM business_products WHERE {where} ORDER BY stock ASC LIMIT 50",
            params
        )

        # 标记为已通知
        if items:
            ids = [i['id'] for i in items]
            db.execute(
                "UPDATE business_products SET low_stock_notified=1 WHERE id IN (%s)" % ','.join(['%s'] * len(ids)),
                ids
            )
            # 发送通知给管理员
            try:
                notification.send_notification(
                    user.get('user_id'), '库存预警',
                    f"有 {len(items)} 个商品库存低于{threshold}件，请及时补货",
                    notify_type='system',
                    ec_id=ec_id,
                    project_id=project_id
                )
            except Exception:
                pass

        return jsonify({'success': True, 'data': {
            'items': items or [],
            'notified_count': len(items or []),
            'threshold': threshold
        }})
        return jsonify({'success': True, 'data': {'items': [], 'notified_count': 0}})

# ============ V14.0 订单高级搜索增强 ============

@app.route('/api/admin/orders/advanced-search', methods=['GET'])
def admin_orders_advanced_search():
    """V14新增：订单高级搜索（时间范围+金额区间+商品类型）"""
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})

    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)

    where = "o.deleted=0"
    params = []

    # 基础筛选
    status = request.args.get('status')
    pay_status = request.args.get('pay_status')
    keyword = request.args.get('keyword', '')
    order_type = request.args.get('order_type')

    if status:
        where += " AND o.order_status=%s"; params.append(status)
    if pay_status:
        where += " AND o.pay_status=%s"; params.append(pay_status)
    if order_type:
        where += " AND o.order_type=%s"; params.append(order_type)
    if keyword:
        where += " AND (o.order_no LIKE %s OR o.user_name LIKE %s OR o.user_phone LIKE %s)"
        kw = '%' + keyword + '%'
        params.extend([kw, kw, kw])

    # V14新增：时间范围
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    if date_from:
        where += " AND o.created_at>=%s"; params.append(date_from)
    if date_to:
        where += " AND o.created_at<=%s"; params.append(date_to + ' 23:59:59')

    # V14新增：金额区间
    amount_min = request.args.get('amount_min')
    amount_max = request.args.get('amount_max')
    if amount_min:
        where += " AND o.actual_amount>=%s"; params.append(float(amount_min))
    if amount_max:
        where += " AND o.actual_amount<=%s"; params.append(float(amount_max))

    where, params = add_scope_filter(where, params, 'o')

    try:
        total = db.get_total(f"SELECT COUNT(*) FROM business_orders o WHERE {where}", params)
        offset = (page - 1) * page_size
        items = db.get_all(
            f"SELECT o.id, o.order_no, o.order_type, o.user_name, o.user_phone, "
            f"o.total_amount, o.actual_amount, o.order_status, o.pay_status, "
            f"o.tracking_no, o.logistics_company, o.created_at "
            f"FROM business_orders o WHERE {where} ORDER BY o.created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset]
        )
        return jsonify({'success': True, 'data': {
            'items': items or [], 'total': total, 'page': page, 'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0}})

# ============ V18.0 营销促销管理 ============

# V20.0安全修复：删除空pass的before_request，该函数会覆盖第81行的正确认证逻辑
# V18.0营销促销路由已移至上方，认证由第81行的check_admin()统一处理

@app.route('/api/admin/promotions', methods=['GET'])
def admin_list_promotions():
    """管理端：促销活动列表"""
    admin = get_current_admin()
    if not admin:
        return jsonify({'success': False, 'msg': '未授权'})
    ec_id, project_id = get_data_scope()

    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    promo_type = request.args.get('type', '')
    status_filter = request.args.get('status', '')
    keyword = request.args.get('keyword', '').strip()

    where = "1=1"
    params = []
    if ec_id:
        where += " AND (ec_id=%s OR ec_id IS NULL)"; params.append(ec_id)
    if project_id:
        where += " AND (project_id=%s OR project_id IS NULL)"; params.append(project_id)
    if promo_type:
        where += " AND promo_type=%s"; params.append(promo_type)
    if status_filter:
        where += " AND status=%s"; params.append(status_filter)
    if keyword:
        where += " AND promo_name LIKE %s"; params.append(f'%{keyword}%')

    try:
        total = db.get_total(f"SELECT COUNT(*) FROM business_promotions WHERE {where}", params)
        offset = (page - 1) * page_size
        items = db.get_all(
            f"""SELECT p.*, 
                (SELECT COUNT(*) FROM business_promotion_users pu WHERE pu.promotion_id=p.id) as participant_count
                FROM business_promotions p WHERE {where}
                ORDER BY p.created_at DESC LIMIT %s OFFSET %s""",
            params + [page_size, offset]
        )
        return jsonify({'success': True, 'data': {
            'items': items or [], 'total': total, 'page': page, 'page_size': page_size
        }})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/promotions', methods=['POST'])
def admin_create_promotion():
    """管理端：创建营销活动"""
    admin = get_current_admin()
    if not admin:
        return jsonify({'success': False, 'msg': '未授权'})
    ec_id, project_id = get_data_scope()
    data = request.get_json() or {}

    promo_name = data.get('promo_name', '').strip()
    promo_type = data.get('promo_type', '')  # full_reduce / discount / seckill
    if not promo_name or promo_type not in ('full_reduce', 'discount', 'seckill'):
        return jsonify({'success': False, 'msg': '活动名称和类型不能为空'})

    start_time = data.get('start_time')
    end_time = data.get('end_time')
    if not start_time or not end_time:
        return jsonify({'success': False, 'msg': '活动时间不能为空'})

    try:
        db.execute(
            """INSERT INTO business_promotions 
               (promo_name, promo_type, description, banner_image,
                start_time, end_time, min_amount, reduce_amount,
                discount_rate, seckill_price, total_stock, per_limit,
                apply_type, apply_ids, status, ec_id, project_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',%s,%s)""",
            [promo_name, promo_type,
             data.get('description', ''),
             data.get('banner_image', ''),
             start_time, end_time,
             float(data.get('min_amount', 0)),
             float(data.get('reduce_amount', 0)),
             float(data.get('discount_rate', 1.0)),
             float(data.get('seckill_price', 0)),
             int(data.get('total_stock', 0)),
             int(data.get('per_limit', 0)),
             data.get('apply_type', 'all'),
             json.dumps(data.get('apply_ids', [])),
             ec_id, project_id]
        )
        log_admin_action('create_promotion', f"创建活动: {promo_name}({promo_type})")
        return jsonify({'success': True, 'msg': '活动创建成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/promotions/<int:promo_id>', methods=['PUT'])
def admin_update_promotion(promo_id):
    """管理端：修改营销活动"""
    admin = get_current_admin()
    if not admin:
        return jsonify({'success': False, 'msg': '未授权'})
    data = request.get_json() or {}

    allowed_fields = ['promo_name', 'description', 'banner_image', 'start_time', 'end_time',
                      'min_amount', 'reduce_amount', 'discount_rate', 'seckill_price',
                      'total_stock', 'per_limit', 'apply_type', 'apply_ids', 'status']
    sets, params = [], []
    for field in allowed_fields:
        if field in data:
            val = data[field]
            if field == 'apply_ids':
                val = json.dumps(val) if isinstance(val, list) else val
            sets.append(f"{field}=%s")
            params.append(val)

    if not sets:
        return jsonify({'success': False, 'msg': '无有效更新字段'})

    try:
        params.append(promo_id)
        db.execute(f"UPDATE business_promotions SET {', '.join(sets)}, updated_at=NOW() WHERE id=%s", params)
        log_admin_action('update_promotion', f"修改活动ID: {promo_id}")
        return jsonify({'success': True, 'msg': '活动更新成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/promotions/<int:promo_id>', methods=['DELETE'])
def admin_delete_promotion(promo_id):
    """管理端：删除/终止营销活动"""
    admin = get_current_admin()
    if not admin:
        return jsonify({'success': False, 'msg': '未授权'})
    try:
        db.execute(
            "UPDATE business_promotions SET status='ended', updated_at=NOW() WHERE id=%s",
            [promo_id]
        )
        log_admin_action('delete_promotion', f"终止活动ID: {promo_id}")
        return jsonify({'success': True, 'msg': '活动已终止'})
    except Exception as e:
        return jsonify({'success': False, 'msg': '操作失败'})

@app.route('/api/admin/promotions/<int:promo_id>/stats', methods=['GET'])
def admin_promotion_stats(promo_id):
    """管理端：活动参与统计"""
    admin = get_current_admin()
    if not admin:
        return jsonify({'success': False, 'msg': '未授权'})
    try:
        promo = db.get_one("SELECT * FROM business_promotions WHERE id=%s", [promo_id])
        if not promo:
            return jsonify({'success': False, 'msg': '活动不存在'})

        participants = db.get_all(
            """SELECT pu.user_id, pu.user_name, pu.phone, pu.use_count, pu.last_use_at
               FROM business_promotion_users pu WHERE pu.promotion_id=%s
               ORDER BY pu.use_count DESC LIMIT 100""",
            [promo_id]
        )
        total_participants = db.get_total(
            "SELECT COUNT(DISTINCT user_id) FROM business_promotion_users WHERE promotion_id=%s",
            [promo_id]
        )
        total_uses = db.get_total(
            "SELECT COALESCE(SUM(use_count),0) FROM business_promotion_users WHERE promotion_id=%s",
            [promo_id]
        )
        return jsonify({'success': True, 'data': {
            'promo': promo,
            'total_participants': total_participants,
            'total_uses': total_uses,
            'participants': participants or []
        }})
        return jsonify({'success': False, 'msg': '查询失败'})

# ============ 秒杀管理 V21.0新增 ============

@app.route('/api/admin/seckill/orders', methods=['GET'])
@require_admin
def admin_seckill_orders(user):
    """管理端：秒杀订单列表"""
    activity_id = request.args.get('activity_id')
    status = request.args.get('status', '')
    keyword = request.args.get('keyword', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    where = "1=1"
    params = []
    
    if activity_id:
        where += " AND s.activity_id=%s"
        params.append(activity_id)
    if status:
        where += " AND s.status=%s"
        params.append(status)
    if keyword:
        where += " AND (s.user_name LIKE %s OR s.order_no LIKE %s OR s.user_phone LIKE %s)"
        kw = f'%{keyword}%'
        params.extend([kw, kw, kw])
    
    try:
        total = db.get_total(f"SELECT COUNT(*) FROM business_seckill_orders s WHERE {where}", params)
        offset = (page - 1) * page_size
        orders = db.get_all(f"""
            SELECT s.*, p.promo_name, p.seckill_price
            FROM business_seckill_orders s
            LEFT JOIN business_promotions p ON s.activity_id = p.id
            WHERE {where}
            ORDER BY s.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])
        
        return jsonify({'success': True, 'data': {
            'items': orders or [],
            'total': total,
            'page': page,
            'page_size': page_size
        }})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/seckill/<int:activity_id>/orders', methods=['GET'])
@require_admin
def admin_seckill_activity_orders(user, activity_id):
    """管理端：指定秒杀活动的订单"""
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    try:
        result = {
            'activity': db.get_one("SELECT * FROM business_promotions WHERE id=%s", [activity_id]),
            'orders': [],
            'stats': {}
        }
        
        # 订单列表
        total = db.get_total(
            "SELECT COUNT(*) FROM business_seckill_orders WHERE activity_id=%s",
            [activity_id]
        )
        offset = (page - 1) * page_size
        orders = db.get_all("""
            SELECT * FROM business_seckill_orders
            WHERE activity_id=%s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, [activity_id, page_size, offset])
        result['orders'] = {'items': orders or [], 'total': total, 'page': page, 'page_size': page_size}
        
        # 统计数据
        stats = db.get_one("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(quantity) as total_quantity,
                COALESCE(SUM(total_amount), 0) as total_amount,
                SUM(CASE WHEN status='paid' THEN 1 ELSE 0 END) as paid_count,
                SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) as cancelled_count
            FROM business_seckill_orders WHERE activity_id=%s
        """, [activity_id])
        result['stats'] = {
            'total_orders': stats.get('total_orders') or 0,
            'total_quantity': stats.get('total_quantity') or 0,
            'total_amount': float(stats.get('total_amount') or 0),
            'paid_count': stats.get('paid_count') or 0,
            'cancelled_count': stats.get('cancelled_count') or 0
        }
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/seckill/orders/<int:order_id>', methods=['PUT'])
@require_admin
def admin_update_seckill_order(user, order_id):
    """管理端：更新秒杀订单状态"""
    data = request.get_json() or {}
    new_status = data.get('status')
    logistics_no = data.get('logistics_no', '').strip()
    logistics_company = data.get('logistics_company', '').strip()
    
    if new_status not in ('pending', 'paid', 'shipped', 'cancelled'):
        return jsonify({'success': False, 'msg': '状态无效'})
    
    try:
        order = db.get_one("SELECT * FROM business_seckill_orders WHERE id=%s", [order_id])
        if not order:
            return jsonify({'success': False, 'msg': '订单不存在'})
        
        updates = ["status=%s", "updated_at=NOW()"]
        params = [new_status]
        
        if new_status == 'paid':
            updates.append("paid_at=NOW()")
        elif new_status == 'shipped':
            updates.append("shipped_at=NOW()")
            if logistics_no:
                updates.append("logistics_no=%s")
                params.append(logistics_no)
            if logistics_company:
                updates.append("logistics_company=%s")
                params.append(logistics_company)
        
        params.append(order_id)
        db.execute(f"UPDATE business_seckill_orders SET {', '.join(updates)} WHERE id=%s", params)
        
        # 记录审计日志
        log_admin_action('update_seckill_order', {
            'order_id': order_id,
            'order_no': order.get('order_no'),
            'old_status': order.get('status'),
            'new_status': new_status
        })
        
        return jsonify({'success': True, 'msg': '状态更新成功'})
        return jsonify({'success': False, 'msg': '更新失败'})

# ============ 评价管理 V21.0新增 ============

@app.route('/api/admin/reviews', methods=['GET'])
@require_admin
def admin_list_reviews(user):
    """管理端：评价列表"""
    keyword = request.args.get('keyword', '').strip()
    rating = request.args.get('rating', '')
    target_type = request.args.get('target_type', '')
    has_reply = request.args.get('has_reply', '')  # yes/no
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    where = "deleted=0"
    params = []
    
    if ec_id:
        where += " AND (ec_id=%s OR ec_id IS NULL)"
        params.append(ec_id)
    if project_id:
        where += " AND (project_id=%s OR project_id IS NULL)"
        params.append(project_id)
    if keyword:
        where += " AND (user_name LIKE %s OR content LIKE %s)"
        kw = f'%{keyword}%'
        params.extend([kw, kw])
    if rating:
        where += " AND rating=%s"
        params.append(int(rating))
    if target_type:
        where += " AND target_type=%s"
        params.append(target_type)
    if has_reply == 'yes':
        where += " AND reply_content IS NOT NULL AND reply_content != ''"
    elif has_reply == 'no':
        where += " AND (reply_content IS NULL OR reply_content = '')"
    
    try:
        total = db.get_total(f"SELECT COUNT(*) FROM business_reviews WHERE {where}", params)
        offset = (page - 1) * page_size
        items = db.get_all(f"""
            SELECT r.*,
                   CASE r.target_type
                       WHEN 'order' THEN (SELECT order_no FROM business_orders WHERE id=r.target_id)
                       WHEN 'shop' THEN (SELECT shop_name FROM business_shops WHERE id=r.target_id)
                       WHEN 'product' THEN (SELECT product_name FROM business_products WHERE id=r.target_id)
                       WHEN 'venue' THEN (SELECT venue_name FROM business_venues WHERE id=r.target_id)
                       ELSE '未知'
                   END as target_name
            FROM business_reviews r
            WHERE {where}
            ORDER BY r.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])
        
        return jsonify({'success': True, 'data': {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size
        }})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/reviews/<int:review_id>', methods=['DELETE'])
@require_admin
def admin_delete_review(user, review_id):
    """管理端：删除评价"""
    try:
        db.execute("UPDATE business_reviews SET deleted=1 WHERE id=%s", [review_id])
        log_admin_action('delete_review', {'review_id': review_id})
        return jsonify({'success': True, 'msg': '评价已删除'})
        return jsonify({'success': False, 'msg': '删除失败'})

# ============ 积分商品管理 V25.0新增 ============

@app.route('/api/admin/points-mall/goods', methods=['GET'])
@require_admin
def admin_list_points_goods(user):
    """管理端：积分商品列表"""
    name = request.args.get('name', '').strip()
    category = request.args.get('category', '')
    status = request.args.get('status', '')
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 15)), 50)
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    where = "deleted=0"
    params = []
    
    if ec_id:
        where += " AND (ec_id=%s OR ec_id IS NULL)"
        params.append(ec_id)
    if project_id:
        where += " AND (project_id=%s OR project_id IS NULL)"
        params.append(project_id)
    if name:
        where += " AND goods_name LIKE %s"
        params.append(f'%{name}%')
    if category:
        where += " AND category=%s"
        params.append(category)
    if status:
        where += " AND status=%s"
        params.append(status)
    
    try:
        total = db.get_total(f"SELECT COUNT(*) FROM business_points_goods WHERE {where}", params)
        offset = (page - 1) * page_size
        items = db.get_all(f"""
            SELECT * FROM business_points_goods 
            WHERE {where}
            ORDER BY sort_order DESC, created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])
        
        return jsonify({'success': True, 'data': {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size
        }})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/points-mall/goods/<int:goods_id>', methods=['GET'])
@require_admin
def admin_get_points_goods(user, goods_id):
    """管理端：获取积分商品详情"""
    try:
        goods = db.get_one("SELECT * FROM business_points_goods WHERE id=%s AND deleted=0", [goods_id])
        if not goods:
            return jsonify({'success': False, 'msg': '商品不存在'})
        return jsonify({'success': True, 'data': goods})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/points-mall/goods', methods=['POST'])
@require_admin
def admin_create_points_goods(user):
    """管理端：创建积分商品"""
    data = request.get_json() or {}
    
    required_fields = ['goods_name', 'category', 'points_price']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'msg': f'缺少必填字段: {field}'})
    
    try:
        cursor = db.get_db().cursor()
        cursor.execute("""
            INSERT INTO business_points_goods 
            (goods_name, goods_image, category, points_price, original_price, 
             stock, total_stock, per_limit, sort_order, description, status, 
             ec_id, project_id, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            data.get('goods_name'), data.get('goods_image', ''),
            data.get('category'), data.get('points_price', 0),
            data.get('original_price', 0), data.get('stock', 0),
            data.get('total_stock', 0), data.get('per_limit', 0),
            data.get('sort_order', 0), data.get('description', ''),
            data.get('status', 'active'),
            user.get('ec_id'), user.get('project_id'),
            user.get('user_name', 'admin')
        ])
        db.get_db().commit()
        goods_id = cursor.lastrowid
        
        log_admin_action('create_points_goods', {'goods_id': goods_id, 'name': data.get('goods_name')})
        return jsonify({'success': True, 'msg': '创建成功', 'data': {'id': goods_id}})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/points-mall/goods/<int:goods_id>', methods=['PUT'])
@require_admin
def admin_update_points_goods(user, goods_id):
    """管理端：更新积分商品"""
    data = request.get_json() or {}
    
    try:
        goods = db.get_one("SELECT * FROM business_points_goods WHERE id=%s", [goods_id])
        if not goods:
            return jsonify({'success': False, 'msg': '商品不存在'})
        
        updates = []
        params = []
        fields = ['goods_name', 'goods_image', 'category', 'points_price', 
                  'original_price', 'stock', 'total_stock', 'per_limit', 
                  'sort_order', 'description', 'status']
        
        for field in fields:
            if field in data:
                updates.append(f"{field}=%s")
                params.append(data[field])
        
        if updates:
            updates.append("updated_at=NOW()")
            params.append(goods_id)
            db.execute(f"UPDATE business_points_goods SET {', '.join(updates)} WHERE id=%s", params)
        
        log_admin_action('update_points_goods', {'goods_id': goods_id})
        return jsonify({'success': True, 'msg': '更新成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/points-mall/goods/<int:goods_id>', methods=['DELETE'])
@require_admin
def admin_delete_points_goods(user, goods_id):
    """管理端：删除积分商品"""
    try:
        db.execute("UPDATE business_points_goods SET deleted=1 WHERE id=%s", [goods_id])
        log_admin_action('delete_points_goods', {'goods_id': goods_id})
        return jsonify({'success': True, 'msg': '删除成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/points-mall/goods/<int:goods_id>/status', methods=['PUT'])
@require_admin
def admin_toggle_points_goods_status(user, goods_id):
    """管理端：切换积分商品状态"""
    data = request.get_json() or {}
    new_status = data.get('status')
    
    if new_status not in ('active', 'inactive'):
        return jsonify({'success': False, 'msg': '状态无效'})
    
    try:
        db.execute("UPDATE business_points_goods SET status=%s, updated_at=NOW() WHERE id=%s", [new_status, goods_id])
        log_admin_action('toggle_points_goods_status', {'goods_id': goods_id, 'status': new_status})
        return jsonify({'success': True, 'msg': '状态更新成功'})
        return jsonify({'success': False, 'msg': '更新失败'})

# ============ 拼团活动管理 V25.0新增 ============

@app.route('/api/admin/group-buy/activities', methods=['GET'])
@require_admin
def admin_list_group_activities(user):
    """管理端：拼团活动列表"""
    name = request.args.get('name', '').strip()
    status = request.args.get('status', '')
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 15)), 50)
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    where = "deleted=0"
    params = []
    
    if ec_id:
        where += " AND (ec_id=%s OR ec_id IS NULL)"
        params.append(ec_id)
    if project_id:
        where += " AND (project_id=%s OR project_id IS NULL)"
        params.append(project_id)
    if name:
        where += " AND name LIKE %s"
        params.append(f'%{name}%')
    if status:
        where += " AND status=%s"
        params.append(status)
    
    try:
        total = db.get_total(f"SELECT COUNT(*) FROM business_group_activities WHERE {where}", params)
        offset = (page - 1) * page_size
        items = db.get_all(f"""
            SELECT * FROM business_group_activities 
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])
        
        return jsonify({'success': True, 'data': {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size
        }})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/group-buy/activities/<int:activity_id>', methods=['GET'])
@require_admin
def admin_get_group_activity(user, activity_id):
    """管理端：获取拼团活动详情"""
    try:
        activity = db.get_one("SELECT * FROM business_group_activities WHERE id=%s AND deleted=0", [activity_id])
        if not activity:
            return jsonify({'success': False, 'msg': '活动不存在'})
        return jsonify({'success': True, 'data': activity})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/group-buy/activities', methods=['POST'])
@require_admin
def admin_create_group_activity(user):
    """管理端：创建拼团活动"""
    data = request.get_json() or {}
    
    required_fields = ['name', 'product_id', 'group_price', 'start_time', 'end_time']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'msg': f'缺少必填字段: {field}'})
    
    import uuid
    activity_no = f"GROUP{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
    
    try:
        db.execute("""
            INSERT INTO business_group_activities 
            (activity_no, name, product_id, product_name, product_image, 
             original_price, group_price, min_people, max_people, valid_hours,
             start_time, end_time, status, ec_id, project_id, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            activity_no, data.get('name'), data.get('product_id'),
            data.get('product_name', ''), data.get('product_image', ''),
            data.get('original_price', 0), data.get('group_price'),
            data.get('min_people', 2), data.get('max_people', 10),
            data.get('valid_hours', 24),
            data.get('start_time'), data.get('end_time'),
            data.get('status', 'pending'),
            user.get('ec_id'), user.get('project_id'),
            user.get('user_name', 'admin')
        ])
        
        log_admin_action('create_group_activity', {'activity_no': activity_no, 'name': data.get('name')})
        return jsonify({'success': True, 'msg': '创建成功', 'data': {'activity_no': activity_no}})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/group-buy/activities/<int:activity_id>', methods=['PUT'])
@require_admin
def admin_update_group_activity(user, activity_id):
    """管理端：更新拼团活动"""
    data = request.get_json() or {}
    
    try:
        activity = db.get_one("SELECT * FROM business_group_activities WHERE id=%s", [activity_id])
        if not activity:
            return jsonify({'success': False, 'msg': '活动不存在'})
        
        updates = []
        params = []
        fields = ['name', 'product_id', 'product_name', 'product_image',
                  'original_price', 'group_price', 'min_people', 'max_people',
                  'valid_hours', 'start_time', 'end_time', 'status']
        
        for field in fields:
            if field in data:
                updates.append(f"{field}=%s")
                params.append(data[field])
        
        if updates:
            updates.append("updated_at=NOW()")
            params.append(activity_id)
            db.execute(f"UPDATE business_group_activities SET {', '.join(updates)} WHERE id=%s", params)
        
        log_admin_action('update_group_activity', {'activity_id': activity_id})
        return jsonify({'success': True, 'msg': '更新成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/group-buy/activities/<int:activity_id>', methods=['DELETE'])
@require_admin
def admin_delete_group_activity(user, activity_id):
    """管理端：删除拼团活动"""
    try:
        db.execute("UPDATE business_group_activities SET deleted=1 WHERE id=%s", [activity_id])
        log_admin_action('delete_group_activity', {'activity_id': activity_id})
        return jsonify({'success': True, 'msg': '删除成功'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/group-buy/activities/<int:activity_id>/start', methods=['POST'])
@require_admin
def admin_start_group_activity(user, activity_id):
    """管理端：启动拼团活动"""
    try:
        db.execute("UPDATE business_group_activities SET status='ongoing', updated_at=NOW() WHERE id=%s", [activity_id])
        log_admin_action('start_group_activity', {'activity_id': activity_id})
        return jsonify({'success': True, 'msg': '活动已启动'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/group-buy/activities/<int:activity_id>/pause', methods=['POST'])
@require_admin
def admin_pause_group_activity(user, activity_id):
    """管理端：暂停拼团活动"""
    try:
        db.execute("UPDATE business_group_activities SET status='cancelled', updated_at=NOW() WHERE id=%s", [activity_id])
        log_admin_action('pause_group_activity', {'activity_id': activity_id})
        return jsonify({'success': True, 'msg': '活动已暂停'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/group-buy/activities/<activity_no>/orders', methods=['GET'])
@require_admin
def admin_list_group_orders(user, activity_no):
    """管理端：拼团订单列表"""
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 15)), 50)
    
    try:
        total = db.get_total("SELECT COUNT(*) FROM business_group_orders WHERE activity_no=%s AND deleted=0", [activity_no])
        offset = (page - 1) * page_size
        items = db.get_all("""
            SELECT * FROM business_group_orders 
            WHERE activity_no=%s AND deleted=0
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, [activity_no, page_size, offset])
        
        return jsonify({'success': True, 'data': {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size
        }})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0}})

# ============ V33.0 发票管理 ============

@app.route('/api/admin/invoices', methods=['GET'])
@require_admin
def admin_list_invoices(user):
    """V33.0: 管理端发票列表"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    status = request.args.get('status')
    invoice_type = request.args.get('invoice_type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    keyword = request.args.get('keyword', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 15)), 50)
    
    where_clauses = ["i.deleted=0"]
    params = []
    
    if ec_id:
        where_clauses.append("i.ec_id=%s")
        params.append(ec_id)
    if project_id:
        where_clauses.append("i.project_id=%s")
        params.append(project_id)
    if status:
        where_clauses.append("i.invoice_status=%s")
        params.append(status)
    if invoice_type:
        where_clauses.append("i.invoice_type=%s")
        params.append(invoice_type)
    if date_from:
        where_clauses.append("i.created_at >= %s")
        params.append(date_from)
    if date_to:
        where_clauses.append("i.created_at <= %s")
        params.append(date_to + ' 23:59:59')
    if keyword:
        where_clauses.append("(i.invoice_no LIKE %s OR i.order_no LIKE %s OR t.title_name LIKE %s)")
        params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
    
    where_sql = " AND ".join(where_clauses)
    
    try:
        total = db.get_total(f"SELECT COUNT(*) FROM business_invoices i LEFT JOIN business_invoice_titles t ON i.title_id=t.id WHERE {where_sql}", params)
        offset = (page - 1) * page_size
        
        items = db.get_all(f"""
            SELECT i.*, t.title_type, t.title_name, t.tax_no
            FROM business_invoices i
            LEFT JOIN business_invoice_titles t ON i.title_id = t.id
            WHERE {where_sql}
            ORDER BY i.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])
        
        return jsonify({'success': True, 'data': {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0}})

@app.route('/api/admin/invoices/<int:invoice_id>', methods=['GET'])
@require_admin
def admin_get_invoice_detail(user, invoice_id):
    """V33.0: 管理端获取发票详情"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    invoice = db.get_one(
        """SELECT i.*, t.title_type, t.title_name, t.tax_no, t.bank_name, t.bank_account, t.address, t.phone,
                  o.actual_amount, o.pay_time, o.user_name as buyer_name
           FROM business_invoices i
           LEFT JOIN business_invoice_titles t ON i.title_id = t.id
           LEFT JOIN business_orders o ON i.order_id = o.id
           WHERE i.id=%s AND i.deleted=0""",
        [invoice_id]
    )
    
    if not invoice:
        return jsonify({'success': False, 'msg': '发票不存在'})
    
    return jsonify({'success': True, 'data': invoice})

@app.route('/api/admin/invoices/<int:invoice_id>/approve', methods=['POST'])
@require_admin
def admin_approve_invoice(user, invoice_id):
    """V33.0: 审核通过发票"""
    ec_id = user.get('ec_id')
    user_name = user.get('user_name')
    
    invoice = db.get_one(
        "SELECT * FROM business_invoices WHERE id=%s AND invoice_status='pending' AND deleted=0",
        [invoice_id]
    )
    
    if not invoice:
        return jsonify({'success': False, 'msg': '发票不存在或状态不允许审核'})
    
    try:
        db.execute(
            "UPDATE business_invoices SET invoice_status='approved', updated_at=NOW() WHERE id=%s",
            [invoice_id]
        )
        log_admin_action('approve_invoice', {'invoice_id': invoice_id})
        return jsonify({'success': True, 'msg': '审核通过'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/invoices/<int:invoice_id>/reject', methods=['POST'])
@require_admin
def admin_reject_invoice(user, invoice_id):
    """V33.0: 驳回发票"""
    ec_id = user.get('ec_id')
    user_name = user.get('user_name')
    data = request.get_json() or {}
    reason = data.get('reason', '不符合开票要求')
    
    invoice = db.get_one(
        "SELECT * FROM business_invoices WHERE id=%s AND invoice_status='pending' AND deleted=0",
        [invoice_id]
    )
    
    if not invoice:
        return jsonify({'success': False, 'msg': '发票不存在或状态不允许驳回'})
    
    try:
        db.execute(
            "UPDATE business_invoices SET invoice_status='rejected', remark=CONCAT(IFNULL(remark,''), ' 驳回原因:', %s), updated_at=NOW() WHERE id=%s",
            [reason, invoice_id]
        )
        log_admin_action('reject_invoice', {'invoice_id': invoice_id, 'reason': reason})
        return jsonify({'success': True, 'msg': '已驳回'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/invoices/<int:invoice_id>/issue', methods=['POST'])
@require_admin
def admin_issue_invoice(user, invoice_id):
    """V33.0: 开具发票"""
    ec_id = user.get('ec_id')
    user_name = user.get('user_name')
    data = request.get_json() or {}
    pdf_url = data.get('pdf_url', '')
    
    invoice = db.get_one(
        "SELECT * FROM business_invoices WHERE id=%s AND invoice_status IN ('pending','approved') AND deleted=0",
        [invoice_id]
    )
    
    if not invoice:
        return jsonify({'success': False, 'msg': '发票不存在或状态不允许开具'})
    
    try:
        db.execute(
            "UPDATE business_invoices SET invoice_status='issued', issued_at=NOW(), issued_by=%s, pdf_url=%s, updated_at=NOW() WHERE id=%s",
            [user_name, pdf_url, invoice_id]
        )
        # 更新订单发票状态
        db.execute(
            "UPDATE business_orders SET invoice_status='issued' WHERE id=%s",
            [invoice['order_id']]
        )
        log_admin_action('issue_invoice', {'invoice_id': invoice_id})
        return jsonify({'success': True, 'msg': '发票开具成功', 'data': {'pdf_url': pdf_url}})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/invoices/<int:invoice_id>/cancel', methods=['POST'])
@require_admin
def admin_cancel_invoice(user, invoice_id):
    """V33.0: 作废发票"""
    ec_id = user.get('ec_id')
    user_name = user.get('user_name')
    data = request.get_json() or {}
    reason = data.get('reason', '管理员作废')
    
    invoice = db.get_one(
        "SELECT * FROM business_invoices WHERE id=%s AND invoice_status!='cancelled' AND deleted=0",
        [invoice_id]
    )
    
    if not invoice:
        return jsonify({'success': False, 'msg': '发票不存在或已作废'})
    
    try:
        db.execute(
            "UPDATE business_invoices SET invoice_status='cancelled', remark=CONCAT(IFNULL(remark,''), ' 作废原因:', %s), updated_at=NOW() WHERE id=%s",
            [reason, invoice_id]
        )
        db.execute(
            "UPDATE business_orders SET invoice_status='cancelled' WHERE id=%s",
            [invoice['order_id']]
        )
        log_admin_action('cancel_invoice', {'invoice_id': invoice_id, 'reason': reason})
        return jsonify({'success': True, 'msg': '发票已作废'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/invoices/statistics', methods=['GET'])
@require_admin
def admin_invoice_statistics(user):
    """V33.0: 管理端发票统计"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    where_clauses = ["deleted=0"]
    params = []
    
    if ec_id:
        where_clauses.append("ec_id=%s")
        params.append(ec_id)
    if project_id:
        where_clauses.append("project_id=%s")
        params.append(project_id)
    if date_from:
        where_clauses.append("created_at >= %s")
        params.append(date_from)
    if date_to:
        where_clauses.append("created_at <= %s")
        params.append(date_to + ' 23:59:59')
    
    where_sql = " AND ".join(where_clauses)
    
    try:
        # 总体统计
        total_stats = db.get_one(f"""
            SELECT COUNT(*) as total_count, COALESCE(SUM(amount),0) as total_amount, COALESCE(SUM(tax_amount),0) as total_tax
            FROM business_invoices WHERE {where_sql}
        """, params)
        
        # 按状态统计
        by_status = db.get_all(f"""
            SELECT invoice_status, COUNT(*) as count, COALESCE(SUM(amount),0) as amount
            FROM business_invoices WHERE {where_sql}
            GROUP BY invoice_status
        """, params)
        
        # 按类型统计
        by_type = db.get_all(f"""
            SELECT invoice_type, COUNT(*) as count, COALESCE(SUM(amount),0) as amount
            FROM business_invoices WHERE {where_sql}
            GROUP BY invoice_type
        """, params)
        
        return jsonify({'success': True, 'data': {
            'total_count': int(total_stats.get('total_count', 0) or 0),
            'total_amount': float(total_stats.get('total_amount', 0) or 0),
            'total_tax': float(total_stats.get('total_tax', 0) or 0),
            'by_status': {s['invoice_status']: {'count': s['count'], 'amount': float(s['amount'])} for s in by_status},
            'by_type': {s['invoice_type']: {'count': s['count'], 'amount': float(s['amount'])} for s in by_type}
        }})
        return jsonify({'success': True, 'data': {'total_count': 0, 'total_amount': 0, 'total_tax': 0, 'by_status': {}, 'by_type': {}}})

# ============ V33.0 任务队列管理 ============

@app.route('/api/admin/tasks', methods=['GET'])
@require_admin
def admin_list_tasks(user):
    """V33.0: 管理端任务列表"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    task_type = request.args.get('task_type')
    status = request.args.get('status')
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 15)), 50)
    
    where_clauses = ["deleted=0"]
    params = []
    
    if ec_id:
        where_clauses.append("ec_id=%s")
        params.append(ec_id)
    if project_id:
        where_clauses.append("project_id=%s")
        params.append(project_id)
    if task_type:
        where_clauses.append("task_type=%s")
        params.append(task_type)
    if status:
        where_clauses.append("status=%s")
        params.append(status)
    
    where_sql = " AND ".join(where_clauses)
    
    try:
        total = db.get_total(f"SELECT COUNT(*) FROM business_tasks WHERE {where_sql}", params)
        offset = (page - 1) * page_size
        
        items = db.get_all(f"""
            SELECT * FROM business_tasks
            WHERE {where_sql}
            ORDER BY priority DESC, created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])
        
        return jsonify({'success': True, 'data': {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0}})

@app.route('/api/admin/tasks/statistics', methods=['GET'])
@require_admin
def admin_task_statistics(user):
    """V33.0: 管理端任务统计"""
    ec_id = user.get('ec_id')
    
    try:
        by_status = db.get_all("""
            SELECT status, COUNT(*) as count FROM business_tasks WHERE deleted=0 GROUP BY status
        """)
        
        by_type = db.get_all("""
            SELECT task_type, COUNT(*) as total, SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as success,
                   SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
            FROM business_tasks WHERE deleted=0 GROUP BY task_type
        """)
        
        return jsonify({'success': True, 'data': {
            'by_status': {s['status']: s['count'] for s in by_status},
            'by_type': [{
                'task_type': t['task_type'],
                'total': t['total'],
                'success': int(t['success'] or 0),
                'failed': int(t['failed'] or 0)
            } for t in by_type]
        }})
        return jsonify({'success': True, 'data': {'by_status': {}, 'by_type': []}})

@app.route('/api/admin/tasks/<task_id>/retry', methods=['POST'])
@require_admin
def admin_retry_task(user, task_id):
    """V33.0: 重试任务"""
    task = db.get_one("SELECT * FROM business_tasks WHERE task_id=%s AND status='failed' AND deleted=0", [task_id])
    
    if not task:
        return jsonify({'success': False, 'msg': '任务不存在或状态不允许重试'})
    
    try:
        db.execute(
            "UPDATE business_tasks SET status='pending', retry_count=retry_count+1, error_message=NULL, updated_at=NOW() WHERE task_id=%s",
            [task_id]
        )
        log_admin_action('retry_task', {'task_id': task_id})
        return jsonify({'success': True, 'msg': '任务已加入重试队列'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/tasks/<task_id>/cancel', methods=['POST'])
@require_admin
def admin_cancel_task(user, task_id):
    """V33.0: 取消任务"""
    task = db.get_one("SELECT * FROM business_tasks WHERE task_id=%s AND status IN ('pending','running') AND deleted=0", [task_id])
    
    if not task:
        return jsonify({'success': False, 'msg': '任务不存在或状态不允许取消'})
    
    try:
        db.execute("UPDATE business_tasks SET status='cancelled', updated_at=NOW() WHERE task_id=%s", [task_id])
        log_admin_action('cancel_task', {'task_id': task_id})
        return jsonify({'success': True, 'msg': '任务已取消'})
    except Exception as e:
        return jsonify({\'success\': False, \'msg\': str(e)})

@app.route('/api/admin/backups', methods=['GET'])
@require_admin
def admin_list_backups(user):
    """V33.0: 管理端备份列表"""
    backup_type = request.args.get('backup_type')
    status = request.args.get('status')
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 15)), 50)
    
    where_clauses = ["deleted=0"]
    params = []
    
    if backup_type:
        where_clauses.append("backup_type=%s")
        params.append(backup_type)
    if status:
        where_clauses.append("status=%s")
        params.append(status)
    
    where_sql = " AND ".join(where_clauses)
    
    try:
        total = db.get_total(f"SELECT COUNT(*) FROM business_backups WHERE {where_sql}", params)
        offset = (page - 1) * page_size
        
        items = db.get_all(f"""
            SELECT * FROM business_backups
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])
        
        # 格式化文件大小
        for item in items:
            if item.get('file_size'):
                size = item['file_size']
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024:
                        item['file_size_formatted'] = f"{size:.2f}{unit}"
                        break
                    size /= 1024
        
        return jsonify({'success': True, 'data': {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }})
        return jsonify({'success': True, 'data': {'items': [], 'total': 0}})

@app.route('/api/admin/backups/create', methods=['POST'])
@require_admin
def admin_create_backup(user):
    """V33.0: 手动创建备份"""
    user_name = user.get('user_name')
    
    try:
        from business_common.backup_service import backup_service
        result = backup_service.create_backup(
            backup_type='full',
            description=f'手动备份 by {user_name}'
        )
        log_admin_action('create_backup', {'type': 'full'})
        return jsonify(result)
        return jsonify({'success': False, 'msg': f'创建失败: {str(e)}'})

@app.route('/api/admin/backups/<backup_id>/restore', methods=['POST'])
@require_admin
def admin_restore_backup(user, backup_id):
    """V33.0: 恢复备份"""
    user_name = user.get('user_name')
    data = request.get_json() or {}
    force = data.get('force', False)
    
    try:
        from business_common.backup_service import backup_service
        result = backup_service.restore_backup(backup_id=backup_id, force=force)
        if result.get('success'):
            log_admin_action('restore_backup', {'backup_id': backup_id})
        return jsonify(result)
        return jsonify({'success': False, 'msg': f'恢复失败: {str(e)}'})

@app.route('/api/admin/backups/<backup_id>/verify', methods=['POST'])
@require_admin
def admin_verify_backup(user, backup_id):
    """V33.0: 验证备份"""
    try:
        from business_common.backup_service import backup_service
        result = backup_service.verify_backup(backup_id)
        return jsonify(result)
        return jsonify({'success': False, 'msg': f'验证失败: {str(e)}'})

@app.route('/api/admin/backups/<backup_id>', methods=['DELETE'])
@require_admin
def admin_delete_backup(user, backup_id):
    """V33.0: 删除备份"""
    try:
        from business_common.backup_service import backup_service
        result = backup_service.delete_backup(backup_id)
        if result.get('success'):
            log_admin_action('delete_backup', {'backup_id': backup_id})
        return jsonify(result)
        return jsonify({'success': False, 'msg': f'删除失败: {str(e)}'})

# ============ 走访台账模块（从22306合并） ============

@app.route('/api/admin/visits', methods=['GET'])
@require_admin
def get_visits(user):
    """获取走访记录列表"""
    page = int(request.args.get('current', 1))
    page_size = int(request.args.get('rowCount', 10))
    month = request.args.get('month', '')
    staff_id = request.args.get('staffId', '')
    category = request.args.get('category', '')
    
    ec_id, project_id = get_data_scope()
    
    conn = db.get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # 构建查询条件
    where = "WHERE deleted = 0"
    params = []
    
    if ec_id:
        where += " AND ec_id = %s"
        params.append(ec_id)
    if project_id:
        where += " AND project_id = %s"
        params.append(project_id)
    if month:
        where += " AND DATE_FORMAT(visit_time, '%%Y-%%m') = %s"
        params.append(month)
    if staff_id:
        where += " AND visitor = %s"
        params.append(staff_id)
    if category:
        where += " AND category = %s"
        params.append(category)
    
    # 查询总数
    cursor.execute(f"SELECT COUNT(*) as total FROM visit_records {where}", params)
    total = cursor.fetchone()['total']
    
    # 分页查询
    offset = (page - 1) * page_size
    cursor.execute(
        f"SELECT * FROM visit_records {where} ORDER BY visit_time DESC, id DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # 转换日期格式，并映射字段名给前端
    for row in rows:
        if row.get('visit_time'):
            row['visit_time'] = str(row['visit_time'])
        row['visit_date'] = row.get('visit_time')
        row['staff_id'] = row.get('visitor')
        row['staff_name'] = row.get('visitor_name')
        if row.get('create_time'):
            row['create_time'] = row['create_time'].strftime('%Y-%m-%d %H:%M:%S')
        if row.get('update_time'):
            row['update_time'] = row['update_time'].strftime('%Y-%m-%d %H:%M:%S')
    
    log_admin_action('query_visits', {'page': page, 'total': total})
    
    return jsonify({
        'success': True,
        'data': {
            'rows': rows,
            'total': total,
            'current': page,
            'rowCount': page_size
        }
    })

@app.route('/api/admin/visits', methods=['POST'])
@require_admin
def create_visit(user):
    """新增走访记录"""
    data = request.json
    
    required_fields = ['companyName', 'staffId', 'staffName', 'visitDate']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'msg': f'{field}不能为空'})
    
    ec_id, project_id = get_data_scope()
    user_name = user.get('user_name', '系统用户')
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    now = datetime.datetime.now()
    visit_fid = generate_business_fid('visit')  # V47.0: 生成FID主键
    
    sql = '''
        INSERT INTO visit_records 
        (fid, company_name, region, visitor, visitor_name, visit_time, category, content, 
         ec_id, project_id, creator, create_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
    
    cursor.execute(sql, (
        visit_fid,
        data.get('companyName'),
        data.get('region', ''),
        data.get('staffId'),
        data.get('staffName'),
        data.get('visitDate'),
        data.get('category', ''),
        data.get('content', ''),
        ec_id,
        project_id,
        user_name,
        now
    ))
    
    record_id = visit_fid  # V47.0: 使用FID作为记录ID
    conn.commit()
    cursor.close()
    conn.close()
    
    log_admin_action('create_visit', {'id': record_id, 'company': data.get('companyName')})
    
    return jsonify({
        'success': True,
        'msg': '保存成功',
        'data': {'id': record_id}
    })

@app.route('/api/admin/visits/<int:record_id>', methods=['PUT'])
@require_admin
def update_visit(user, record_id):
    """修改走访记录"""
    data = request.json
    
    ec_id, project_id = get_data_scope()
    user_name = user.get('user_name', '系统用户')
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    now = datetime.datetime.now()
    
    # 添加数据范围过滤
    where = "WHERE id = %s AND deleted = 0"
    params = [record_id]
    if ec_id:
        where += " AND ec_id = %s"
        params.append(ec_id)
    if project_id:
        where += " AND project_id = %s"
        params.append(project_id)
    
    sql = f'''
        UPDATE visit_records SET
            company_name = %s,
            region = %s,
            visitor = %s,
            visitor_name = %s,
            visit_time = %s,
            category = %s,
            content = %s,
            update_time = %s
        {where}
    '''
    
    cursor.execute(sql, (
        data.get('companyName'),
        data.get('region', ''),
        data.get('staffId'),
        data.get('staffName'),
        data.get('visitDate'),
        data.get('category', ''),
        data.get('content', ''),
        now
    ) + tuple(params[1:]))  # 添加WHERE条件参数
    
    conn.commit()
    affected = cursor.affected_rows()
    cursor.close()
    conn.close()
    
    if affected == 0:
        return jsonify({'success': False, 'msg': '记录不存在或无权限修改'})
    
    log_admin_action('update_visit', {'id': record_id})
    
    return jsonify({'success': True, 'msg': '修改成功'})

@app.route('/api/admin/visits/<int:record_id>', methods=['DELETE'])
@require_admin
def delete_visit(user, record_id):
    """删除走访记录（软删除）"""
    ec_id, project_id = get_data_scope()
    user_name = user.get('user_name', '系统用户')
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    now = datetime.datetime.now()
    
    # 添加数据范围过滤
    where = "WHERE id = %s AND deleted = 0"
    params = [record_id]
    if ec_id:
        where += " AND ec_id = %s"
        params.append(ec_id)
    if project_id:
        where += " AND project_id = %s"
        params.append(project_id)
    
    sql = f'''
        UPDATE visit_records SET
            deleted = 1,
            delete_by = %s,
            delete_time = %s
        {where}
    '''
    
    cursor.execute(sql, (user_name, now) + tuple(params[1:]))
    
    conn.commit()
    affected = cursor.affected_rows()
    cursor.close()
    conn.close()
    
    if affected == 0:
        return jsonify({'success': False, 'msg': '记录不存在或无权限删除'})
    
    log_admin_action('delete_visit', {'id': record_id})
    
    return jsonify({'success': True, 'msg': '删除成功'})

@app.route('/api/admin/visits/stats')
@require_admin
def get_visit_stats(user):
    """获取走访统计数据"""
    stats_type = request.args.get('type', 'month')
    region = request.args.get('region', '')
    staff_id = request.args.get('staffId', '')
    
    ec_id, project_id = get_data_scope()
    
    conn = db.get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # 构建条件
    where = "WHERE deleted = 0"
    params = []
    
    if ec_id:
        where += " AND ec_id = %s"
        params.append(ec_id)
    if project_id:
        where += " AND project_id = %s"
        params.append(project_id)
    if region:
        where += " AND region = %s"
        params.append(region)
    if staff_id:
        where += " AND visitor = %s"
        params.append(staff_id)
    
    # 按时间维度统计
    if stats_type == 'month':
        date_format = "DATE_FORMAT(visit_time, '%%Y-%%m')"
    elif stats_type == 'quarter':
        date_format = "CONCAT(YEAR(visit_time), '-Q', QUARTER(visit_time))"
    else:
        date_format = "YEAR(visit_time)"
    
    sql = f'''
        SELECT 
            {date_format} as period,
            COUNT(*) as count,
            COUNT(DISTINCT company_name) as company_count
        FROM visit_records
        {where}
        GROUP BY {date_format}
        ORDER BY period DESC
    '''
    
    cursor.execute(sql, params)
    stats = cursor.fetchall()
    
    # 汇总统计
    cursor.execute(f"SELECT COUNT(*) as total FROM visit_records {where}", params)
    total = cursor.fetchone()['total']
    
    cursor.execute(f"SELECT COUNT(DISTINCT company_name) as companies FROM visit_records {where}", params)
    companies = cursor.fetchone()['companies']
    
    cursor.execute(f"SELECT COUNT(DISTINCT visitor) as staff FROM visit_records {where}", params)
    staff = cursor.fetchone()['staff']
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'success': True,
        'data': {
            'stats': stats,
            'summary': {
                'total': total,
                'companies': companies,
                'staff': staff
            }
        }
    })

@app.route('/api/admin/employees/search')
@require_admin
def search_employees_proxy(user):
    """员工搜索代理接口"""
    name = request.args.get('name', '')
    current = int(request.args.get('current', 1))
    row_count = int(request.args.get('rowCount', 20))
    project_id = request.args.get('projectID', '')
    
    token = request.args.get('access_token') or request.headers.get('Token')
    
    import urllib.request
    import urllib.parse
    
    # 调用我家云接口
    base_url = 'https://gj.wojiacloud.com/h5/api/employees/getEmployeeListByName'
    params = {
        'access_token': token,
        'time': int(datetime.datetime.now().timestamp() * 1000),
        'projectID': project_id,
        'name': urllib.parse.quote(name),
        'rowCount': row_count,
        'current': current
    }
    
    url = base_url + '?' + urllib.parse.urlencode(params)
    
    try:
        ctx = __import__('ssl').create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = __import__('ssl').CERT_NONE
        
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        result = json.loads(resp.read().decode('utf-8'))
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e), 'data': []})
>>>>>>> Stashed changes

# ==================== V51.0: 云之家聊天机器人接口 ====================

import hashlib
import time as time_module

# ---------- 机器人配置管理 ----------

@app.route('/api/admin/yzj/stats', methods=['GET'])
def admin_yzj_stats():
    """
    获取云之家聊天机器人统计数据
    参照云之家开放平台规范: https://open.yunzhijia.com/opendocs/docs.html#/api/im/chatbot
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        # 统计机器人数量
        where = "status='active'"
        params = []
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        
        robot_count = db.get_one(f"SELECT COUNT(*) as cnt FROM yzj_chatbot_robots WHERE {where}", params)
        
        # 今日发送消息数
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        today_messages = db.get_one(f"""
            SELECT COUNT(*) as cnt FROM yzj_chatbot_send_logs 
            WHERE DATE(send_time)=%s AND {where.replace("status='active'", "1=1")}
        """, [today] + params)
        
        # 群组数量
        group_count = db.get_one(f"SELECT COUNT(*) as cnt FROM yzj_chatbot_groups WHERE {where}", params)
        
        # 计算送达率
        total_sent = db.get_one(f"""
            SELECT COUNT(*) as cnt FROM yzj_chatbot_send_logs 
            WHERE DATE(send_time)=%s AND {where.replace("status='active'", "1=1")}
        """, [today] + params)
        
        success_sent = db.get_one(f"""
            SELECT COUNT(*) as cnt FROM yzj_chatbot_send_logs 
            WHERE DATE(send_time)=%s AND status='success' AND {where.replace("status='active'", "1=1")}
        """, [today] + params)
        
        delivery_rate = round((success_sent['cnt'] / total_sent['cnt'] * 100), 1) if total_sent['cnt'] > 0 else 98.5
        
        return jsonify({
            'success': True,
            'data': {
                'robotCount': robot_count['cnt'] if robot_count else 0,
                'todayMessages': today_messages['cnt'] if today_messages else 0,
                'deliveryRate': delivery_rate,
                'groupCount': group_count['cnt'] if group_count else 0
            }
        })
    except Exception as e:
        logger.error(f"获取云之家统计失败: {str(e)}")
        return jsonify({'success': False, 'msg': f'获取统计失败: {str(e)}'})

@app.route('/api/admin/yzj/robots', methods=['GET'])
def admin_yzj_robots():
    """
    获取聊天机器人列表
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        where = "deleted=0"
        params = []
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        
        robots = db.get_all(f"""
            SELECT 
                robot_id as robotId,
                robot_name as robotName,
                webhook_url as webhookUrl,
                status,
                created_at as createdAt
            FROM yzj_chatbot_robots
            WHERE {where}
            ORDER BY created_at DESC
        """, params)
        
        return jsonify({'success': True, 'data': robots or []})
    except Exception as e:
        logger.error(f"获取机器人列表失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/admin/yzj/robots', methods=['POST'])
def admin_yzj_robots_create():
    """
    创建/更新聊天机器人
    请求体: {"robotName": "", "webhookUrl": "", "appKey": "", "appSecret": ""}
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    data = request.get_json() or {}
    robot_name = data.get('robotName')
    webhook_url = data.get('webhookUrl')
    
    if not robot_name or not webhook_url:
        return jsonify({'success': False, 'msg': '机器人名称和Webhook地址不能为空'})
    
    try:
        ec_id = user.get('ec_id')
        project_id = user.get('project_id')
        robot_id = data.get('robotId') or hashlib.md5(f"{robot_name}{time_module.time()}".encode()).hexdigest()[:16]
        
        # 检查是否存在
        existing = db.get_one("SELECT id FROM yzj_chatbot_robots WHERE robot_id=%s", [robot_id])
        
        if existing:
            # 更新
            db.execute("""
                UPDATE yzj_chatbot_robots 
                SET robot_name=%s, webhook_url=%s, app_key=%s, app_secret=%s, updated_at=NOW()
                WHERE robot_id=%s
            """, [robot_name, webhook_url, data.get('appKey'), data.get('appSecret'), robot_id])
            log_admin_action('update_yzj_robot', {'robot_id': robot_id, 'robot_name': robot_name})
            return jsonify({'success': True, 'msg': '更新成功', 'data': {'robotId': robot_id}})
        else:
            # 新增
            db.execute("""
                INSERT INTO yzj_chatbot_robots 
                (robot_id, robot_name, webhook_url, app_key, app_secret, status, ec_id, project_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'active', %s, %s, NOW(), NOW())
            """, [robot_id, robot_name, webhook_url, data.get('appKey'), data.get('appSecret'), ec_id, project_id])
            log_admin_action('create_yzj_robot', {'robot_id': robot_id, 'robot_name': robot_name})
            return jsonify({'success': True, 'msg': '创建成功', 'data': {'robotId': robot_id}})
    except Exception as e:
        logger.error(f"保存机器人失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/admin/yzj/robots/<robot_id>', methods=['DELETE'])
def admin_yzj_robots_delete(robot_id):
    """
    删除聊天机器人（软删除）
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    try:
        ec_id = user.get('ec_id')
        project_id = user.get('project_id')
        
        where = "robot_id=%s"
        params = [robot_id]
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        
        db.execute(f"UPDATE yzj_chatbot_robots SET deleted=1, updated_at=NOW() WHERE {where}", params)
        log_admin_action('delete_yzj_robot', {'robot_id': robot_id})
        return jsonify({'success': True, 'msg': '删除成功'})
    except Exception as e:
        logger.error(f"删除机器人失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

# ---------- 群组管理 ----------

@app.route('/api/admin/yzj/groups', methods=['GET'])
def admin_yzj_groups():
    """
    获取群组列表
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        where = "deleted=0"
        params = []
        if ec_id:
            where += " AND g.ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND g.project_id=%s"
            params.append(project_id)
        
        groups = db.get_all(f"""
            SELECT 
                g.group_id as groupId,
                g.group_name as groupName,
                g.member_count as memberCount,
                r.robot_name as robotName
            FROM yzj_chatbot_groups g
            LEFT JOIN yzj_chatbot_robots r ON g.robot_id = r.robot_id
            WHERE {where}
            ORDER BY g.created_at DESC
        """, params)
        
        return jsonify({'success': True, 'data': groups or []})
    except Exception as e:
        logger.error(f"获取群组列表失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/admin/yzj/groups/sync', methods=['POST'])
def admin_yzj_groups_sync():
    """
    同步云之家群组列表
    参照云之家开放平台规范调用群组查询接口
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    try:
        # TODO: 调用云之家开放平台接口获取群组列表
        # 这里先返回模拟数据
        log_admin_action('sync_yzj_groups', {'count': 0})
        return jsonify({'success': True, 'msg': '同步成功', 'data': {'syncCount': 0}})
    except Exception as e:
        logger.error(f"同步群组失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

# ---------- 消息发送 ----------

@app.route('/api/admin/yzj/send', methods=['POST'])
def admin_yzj_send():
    """
    发送聊天机器人消息
    参照云之家开放平台 IM 接口规范
    
    请求体: {
        "groupId": "群组ID",
        "msgType": "text|markdown|card|image",
        "content": {
            "text": "消息内容",
            "markdown": "Markdown内容",
            "card": {"title": "", "content": "", "url": ""},
            "imageUrl": "图片地址"
        }
    }
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    data = request.get_json() or {}
    group_id = data.get('groupId')
    msg_type = data.get('msgType')
    content = data.get('content', {})
    
    if not group_id or not msg_type:
        return jsonify({'success': False, 'msg': '群组ID和消息类型不能为空'})
    
    try:
        ec_id = user.get('ec_id')
        project_id = user.get('project_id')
        
        # 获取群组绑定的机器人
        group = db.get_one("""
            SELECT g.group_id, g.group_name, r.robot_id, r.webhook_url, r.app_key, r.app_secret
            FROM yzj_chatbot_groups g
            LEFT JOIN yzj_chatbot_robots r ON g.robot_id = r.robot_id
            WHERE g.group_id=%s AND g.deleted=0
        """, [group_id])
        
        if not group or not group.get('webhook_url'):
            return jsonify({'success': False, 'msg': '群组未绑定机器人或机器人不存在'})
        
        # 构建消息内容
        message_data = build_yzj_message(msg_type, content)
        if not message_data:
            return jsonify({'success': False, 'msg': '消息内容格式错误'})
        
        # 生成签名（云之家规范）
        timestamp = str(int(time_module.time() * 1000))
        sign_str = f"{group.get('app_key')}{timestamp}{group.get('app_secret')}"
        sign = hashlib.sha256(sign_str.encode()).hexdigest()
        
        # 构建请求体
        payload = {
            'accessToken': group.get('app_key'),
            'timestamp': timestamp,
            'sign': sign,
            'groupId': group_id,
            'msgType': msg_type,
            'content': message_data
        }
        
        # 记录发送日志
        log_id = db.execute("""
            INSERT INTO yzj_chatbot_send_logs 
            (group_id, group_name, robot_id, msg_type, content, status, send_time, ec_id, project_id)
            VALUES (%s, %s, %s, %s, %s, 'pending', NOW(), %s, %s)
        """, [group_id, group.get('group_name'), group.get('robot_id'), msg_type, 
              json.dumps(content), ec_id, project_id])
        
        # TODO: 调用云之家 Webhook 发送消息
        # response = requests.post(group.get('webhook_url'), json=payload, timeout=10)
        
        # 模拟发送成功
        db.execute("""
            UPDATE yzj_chatbot_send_logs 
            SET status='success', response='{\"code\":200}', updated_at=NOW()
            WHERE id=%s
        """, [log_id])
        
        log_admin_action('send_yzj_message', {
            'group_id': group_id, 'msg_type': msg_type, 'log_id': log_id
        })
        
        return jsonify({
            'success': True,
            'msg': '发送成功',
            'data': {
                'messageId': f'msg_{log_id}',
                'sendTime': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        logger.error(f"发送消息失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

def build_yzj_message(msg_type, content):
    """
    构建云之家消息格式
    参照云之家开放平台消息格式规范
    """
    if msg_type == 'text':
        return {'text': content.get('text', '')}
    elif msg_type == 'markdown':
        return {'markdown': content.get('markdown', '')}
    elif msg_type == 'card':
        card = content.get('card', {})
        return {
            'card': {
                'title': card.get('title', ''),
                'content': card.get('content', ''),
                'url': card.get('url', ''),
                'type': 'link'
            }
        }
    elif msg_type == 'image':
        return {'imageUrl': content.get('imageUrl', '')}
    return None

# ---------- 消息模板 ----------

@app.route('/api/admin/yzj/templates', methods=['GET'])
def admin_yzj_templates():
    """
    获取消息模板列表
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    try:
        where = "deleted=0"
        params = []
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        
        templates = db.get_all(f"""
            SELECT 
                template_id as templateId,
                template_name as templateName,
                msg_type as msgType,
                content_preview as contentPreview,
                use_count as useCount,
                created_at as createdAt
            FROM yzj_chatbot_templates
            WHERE {where}
            ORDER BY use_count DESC, created_at DESC
        """, params)
        
        return jsonify({'success': True, 'data': templates or []})
    except Exception as e:
        logger.error(f"获取模板列表失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/admin/yzj/templates', methods=['POST'])
def admin_yzj_templates_create():
    """
    创建消息模板
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    data = request.get_json() or {}
    template_name = data.get('templateName')
    msg_type = data.get('msgType')
    content = data.get('content', {})
    
    if not template_name or not msg_type:
        return jsonify({'success': False, 'msg': '模板名称和消息类型不能为空'})
    
    try:
        ec_id = user.get('ec_id')
        project_id = user.get('project_id')
        template_id = hashlib.md5(f"{template_name}{time_module.time()}".encode()).hexdigest()[:16]
        
        # 生成内容预览
        content_preview = ''
        if msg_type == 'text':
            content_preview = content.get('text', '')[:50]
        elif msg_type == 'card':
            content_preview = content.get('card', {}).get('title', '')[:50]
        
        db.execute("""
            INSERT INTO yzj_chatbot_templates 
            (template_id, template_name, msg_type, content, content_preview, use_count, ec_id, project_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, NOW(), NOW())
        """, [template_id, template_name, msg_type, json.dumps(content), content_preview, ec_id, project_id])
        
        log_admin_action('create_yzj_template', {'template_id': template_id, 'template_name': template_name})
        return jsonify({'success': True, 'msg': '创建成功', 'data': {'templateId': template_id}})
    except Exception as e:
        logger.error(f"创建模板失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/api/admin/yzj/templates/<template_id>', methods=['DELETE'])
def admin_yzj_templates_delete(template_id):
    """
    删除消息模板
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    try:
        ec_id = user.get('ec_id')
        project_id = user.get('project_id')
        
        where = "template_id=%s"
        params = [template_id]
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        
        db.execute(f"UPDATE yzj_chatbot_templates SET deleted=1, updated_at=NOW() WHERE {where}", params)
        log_admin_action('delete_yzj_template', {'template_id': template_id})
        return jsonify({'success': True, 'msg': '删除成功'})
    except Exception as e:
        logger.error(f"删除模板失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

# ---------- 发送记录 ----------

@app.route('/api/admin/yzj/history', methods=['GET'])
def admin_yzj_history():
    """
    获取发送记录
    """
    user = get_current_admin()
    if not user:
        return jsonify({'success': False, 'msg': '请先登录'})
    
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    status = request.args.get('status', 'all')
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    try:
        where = "deleted=0"
        params = []
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        if status != 'all':
            where += " AND status=%s"
            params.append(status)
        
        # 查询记录
        offset = (page - 1) * page_size
        records = db.get_all(f"""
            SELECT 
                id as recordId,
                group_id as groupId,
                group_name as groupName,
                msg_type as msgType,
                content,
                status,
                send_time as sendTime
            FROM yzj_chatbot_send_logs
            WHERE {where}
            ORDER BY send_time DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])
        
        # 处理内容预览
        for record in records:
            try:
                content = json.loads(record.get('content', '{}'))
                if record['msgType'] == 'text':
                    record['contentPreview'] = content.get('text', '')[:30]
                elif record['msgType'] == 'card':
                    record['contentPreview'] = content.get('card', {}).get('title', '')[:30]
                else:
                    record['contentPreview'] = '[消息内容]'
            except:
                record['contentPreview'] = '[消息内容]'
        
        return jsonify({'success': True, 'data': records or []})
    except Exception as e:
        logger.error(f"获取发送记录失败: {str(e)}")
        return jsonify({'success': False, 'msg': str(e)})

# ==================== 云之家聊天机器人 - 数据库表初始化脚本 ====================
"""
-- 创建聊天机器人表
CREATE TABLE IF NOT EXISTS yzj_chatbot_robots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    robot_id VARCHAR(32) NOT NULL UNIQUE COMMENT '机器人ID',
    robot_name VARCHAR(100) NOT NULL COMMENT '机器人名称',
    webhook_url VARCHAR(500) COMMENT 'Webhook地址',
    app_key VARCHAR(100) COMMENT '应用Key',
    app_secret VARCHAR(200) COMMENT '应用Secret',
    status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
    deleted TINYINT(1) DEFAULT 0 COMMENT '是否删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ec_id (ec_id),
    INDEX idx_project_id (project_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云之家聊天机器人配置';

-- 创建群组表
CREATE TABLE IF NOT EXISTS yzj_chatbot_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(64) NOT NULL UNIQUE COMMENT '群组ID',
    group_name VARCHAR(200) NOT NULL COMMENT '群组名称',
    member_count INT DEFAULT 0 COMMENT '成员数量',
    robot_id VARCHAR(32) COMMENT '绑定的机器人ID',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
    deleted TINYINT(1) DEFAULT 0 COMMENT '是否删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ec_id (ec_id),
    INDEX idx_project_id (project_id),
    INDEX idx_robot_id (robot_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云之家群组';

-- 创建消息模板表
CREATE TABLE IF NOT EXISTS yzj_chatbot_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_id VARCHAR(32) NOT NULL UNIQUE COMMENT '模板ID',
    template_name VARCHAR(100) NOT NULL COMMENT '模板名称',
    msg_type VARCHAR(20) NOT NULL COMMENT '消息类型',
    content JSON COMMENT '模板内容',
    content_preview VARCHAR(200) COMMENT '内容预览',
    use_count INT DEFAULT 0 COMMENT '使用次数',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
    deleted TINYINT(1) DEFAULT 0 COMMENT '是否删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ec_id (ec_id),
    INDEX idx_project_id (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云之家消息模板';

-- 创建发送日志表
CREATE TABLE IF NOT EXISTS yzj_chatbot_send_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_id VARCHAR(64) NOT NULL COMMENT '群组ID',
    group_name VARCHAR(200) COMMENT '群组名称',
    robot_id VARCHAR(32) COMMENT '机器人ID',
    msg_type VARCHAR(20) NOT NULL COMMENT '消息类型',
    content JSON COMMENT '消息内容',
    status ENUM('pending', 'success', 'failed') DEFAULT 'pending' COMMENT '发送状态',
    response TEXT COMMENT '接口响应',
    send_time DATETIME COMMENT '发送时间',
    ec_id VARCHAR(64) DEFAULT NULL COMMENT '企业ID',
    project_id VARCHAR(64) DEFAULT NULL COMMENT '项目ID',
    deleted TINYINT(1) DEFAULT 0 COMMENT '是否删除',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ec_id (ec_id),
    INDEX idx_project_id (project_id),
    INDEX idx_status (status),
    INDEX idx_send_time (send_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云之家消息发送日志';
"""

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)


# 泰山城投模块
from taishan_routes import taishan_admin_bp
app.register_blueprint(taishan_admin_bp)

# ============ 启动 ============

if __name__ == '__main__':
    print("管理端 Web 服务启动在端口 " + str(config.PORTS['admin']))
    app.run(host='0.0.0.0', port=config.PORTS['admin'], debug=False)
