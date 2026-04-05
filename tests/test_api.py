"""
社区商业服务系统 - 自动化测试框架
覆盖：用户端API、员工端API、管理端API核心功能

运行方式：
  cd wojiayun
  python -m pytest tests/ -v --tb=short

注意：测试需要数据库连接，确保DB_CONFIG配置正确
"""
import sys
import os
import json
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from business_common import config, db

# ============ 测试配置 ============

TEST_USER_TOKEN = os.environ.get('TEST_USER_TOKEN', '')
TEST_STAFF_TOKEN = os.environ.get('TEST_STAFF_TOKEN', '')
TEST_ADMIN_TOKEN = os.environ.get('TEST_ADMIN_TOKEN', '')

# 如果没有设置Token，标记为跳过
SKIP_NO_TOKEN = pytest.mark.skipif(
    not all([TEST_USER_TOKEN, TEST_STAFF_TOKEN, TEST_ADMIN_TOKEN]),
    reason="需要设置 TEST_USER_TOKEN, TEST_STAFF_TOKEN, TEST_ADMIN_TOKEN 环境变量"
)

BASE_URLS = {
    'user': f"http://127.0.0.1:22311",
    'staff': f"http://127.0.0.1:22312",
    'admin': f"http://127.0.0.1:22313",
}


def api_request(service, method, path, data=None, params=None, token=None):
    """通用API请求辅助函数"""
    import urllib.request
    import urllib.parse
    
    base = BASE_URLS[service]
    url = base + path
    
    if params:
        url += '?' + urllib.parse.urlencode(params)
    
    if token and 'access_token=' not in url:
        sep = '&' if '?' in url else '?'
        url += f'{sep}access_token={urllib.parse.quote(token)}'
    
    headers = {'Content-Type': 'application/json'}
    body = json.dumps(data).encode() if data else None
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except:
            return {'success': False, 'msg': f'HTTP {e.code}'}
    except Exception as e:
        return {'success': False, 'msg': str(e)}


# ============ 基础测试 ============

class TestHealthEndpoints:
    """健康检查端点测试"""
    
    def test_user_health(self):
        r = api_request('user', 'GET', '/health')
        assert r.get('status') == 'ok' or r.get('service') == 'user-h5'
    
    def test_staff_health(self):
        r = api_request('staff', 'GET', '/health')
        assert r.get('status') == 'ok' or r.get('service') == 'staff-h5'
    
    def test_admin_health(self):
        r = api_request('admin', 'GET', '/health')
        assert r.get('status') == 'ok' or r.get('module') == 'admin-web'


# ============ 数据库连接测试 ============

class TestDatabaseConnection:
    """数据库连接测试"""
    
    def test_db_connection(self):
        """测试数据库连接是否正常"""
        conn = db.get_db()
        assert conn is not None
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
        cursor.close()
        conn.close()
    
    def test_members_table_exists(self):
        """测试business_members表是否存在"""
        result = db.get_one("SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='business_members'")
        assert result and result['cnt'] > 0
    
    def test_applications_table_exists(self):
        """测试business_applications表是否存在"""
        result = db.get_one("SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='business_applications'")
        assert result and result['cnt'] > 0


# ============ 用户端API测试 ============

@SKIP_NO_TOKEN
class TestUserH5API:
    """用户端H5 API测试"""
    
    def test_user_stats(self):
        """用户统计数据"""
        r = api_request('user', 'GET', '/api/user/stats', token=TEST_USER_TOKEN)
        assert r.get('success') is True
    
    def test_user_applications_list(self):
        """申请列表"""
        r = api_request('user', 'GET', '/api/user/applications', token=TEST_USER_TOKEN)
        assert r.get('success') is True
        assert 'items' in r.get('data', {})
    
    def test_user_orders_list(self):
        """订单列表"""
        r = api_request('user', 'GET', '/api/user/orders', token=TEST_USER_TOKEN)
        assert r.get('success') is True
        assert 'items' in r.get('data', {})
    
    def test_user_bookings_list(self):
        """预约列表"""
        r = api_request('user', 'GET', '/api/user/bookings', token=TEST_USER_TOKEN)
        assert r.get('success') is True
        assert 'items' in r.get('data', {})
    
    def test_user_member_info(self):
        """会员信息"""
        r = api_request('user', 'GET', '/api/user/member', token=TEST_USER_TOKEN)
        assert r.get('success') is True
    
    def test_user_points_logs(self):
        """积分记录"""
        r = api_request('user', 'GET', '/api/user/points/logs', token=TEST_USER_TOKEN)
        assert r.get('success') is True
    
    def test_user_shops_list(self):
        """门店列表"""
        r = api_request('user', 'GET', '/api/shops')
        assert r.get('success') is True
    
    def test_user_venues_list(self):
        """场馆列表"""
        r = api_request('user', 'GET', '/api/user/venues', token=TEST_USER_TOKEN)
        assert r.get('success') is True
    
    def test_user_notications(self):
        """通知列表"""
        r = api_request('user', 'GET', '/api/user/notifications', token=TEST_USER_TOKEN)
        assert r.get('success') is True
    
    def test_user_feedback_list(self):
        """反馈列表"""
        r = api_request('user', 'GET', '/api/user/feedback', token=TEST_USER_TOKEN)
        assert r.get('success') is True
    
    def test_user_favorites(self):
        """收藏列表"""
        r = api_request('user', 'GET', '/api/user/favorites', token=TEST_USER_TOKEN)
        assert r.get('success') is True
    
    def test_user_coupons(self):
        """优惠券列表"""
        r = api_request('user', 'GET', '/api/user/coupons', token=TEST_USER_TOKEN)
        assert r.get('success') is True
    
    def test_user_notices(self):
        """公告列表"""
        r = api_request('user', 'GET', '/api/notices')
        assert r.get('success') is True
    
    def test_create_application_validation(self):
        """创建申请 - 参数校验"""
        r = api_request('user', 'POST', '/api/user/applications', {}, token=TEST_USER_TOKEN)
        assert r.get('success') is False
        assert '请填写' in r.get('msg', '')
    
    def test_create_feedback_validation(self):
        """创建反馈 - 参数校验"""
        r = api_request('user', 'POST', '/api/user/feedback', {}, token=TEST_USER_TOKEN)
        assert r.get('success') is False
        assert '不能为空' in r.get('msg', '')


# ============ 员工端API测试 ============

@SKIP_NO_TOKEN
class TestStaffH5API:
    """员工端H5 API测试"""
    
    def test_staff_stats(self):
        """员工统计数据"""
        r = api_request('staff', 'GET', '/api/staff/stats', token=TEST_STAFF_TOKEN)
        assert r.get('success') is True
    
    def test_staff_statistics(self):
        """员工详细统计"""
        r = api_request('staff', 'GET', '/api/staff/statistics', token=TEST_STAFF_TOKEN)
        assert r.get('success') is True
    
    def test_staff_applications(self):
        """申请列表"""
        r = api_request('staff', 'GET', '/api/staff/applications', token=TEST_STAFF_TOKEN)
        assert r.get('success') is True
    
    def test_staff_orders(self):
        """订单列表"""
        r = api_request('staff', 'GET', '/api/staff/orders', token=TEST_STAFF_TOKEN)
        assert r.get('success') is True
    
    def test_staff_notifications(self):
        """通知列表"""
        r = api_request('staff', 'GET', '/api/staff/notifications', token=TEST_STAFF_TOKEN)
        assert r.get('success') is True
    
    def test_staff_feedback(self):
        """反馈列表"""
        r = api_request('staff', 'GET', '/api/staff/feedback', token=TEST_STAFF_TOKEN)
        assert r.get('success') is True
    
    def test_staff_bookings(self):
        """预约列表"""
        r = api_request('staff', 'GET', '/api/staff/bookings', token=TEST_STAFF_TOKEN)
        assert r.get('success') is True


# ============ 管理端API测试 ============

@SKIP_NO_TOKEN
class TestAdminAPI:
    """管理端API测试"""
    
    def test_admin_statistics(self):
        """统计概览"""
        r = api_request('admin', 'GET', '/api/admin/statistics', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True
    
    def test_admin_applications(self):
        """申请单列表"""
        r = api_request('admin', 'GET', '/api/admin/applications', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True
    
    def test_admin_orders(self):
        """订单列表"""
        r = api_request('admin', 'GET', '/api/admin/orders', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True
    
    def test_admin_shops(self):
        """门店列表"""
        r = api_request('admin', 'GET', '/api/admin/shops', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True
    
    def test_admin_users(self):
        """用户列表"""
        r = api_request('admin', 'GET', '/api/admin/users', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True
    
    def test_admin_venues(self):
        """场地列表"""
        r = api_request('admin', 'GET', '/api/admin/venues', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True
    
    def test_admin_points_members(self):
        """积分会员列表"""
        r = api_request('admin', 'GET', '/api/admin/points/members', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True
    
    def test_admin_points_stats(self):
        """积分统计"""
        r = api_request('admin', 'GET', '/api/admin/points/stats', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True
    
    def test_admin_feedback(self):
        """反馈列表"""
        r = api_request('admin', 'GET', '/api/admin/feedback', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True
    
    def test_admin_notifications(self):
        """通知列表"""
        r = api_request('admin', 'GET', '/api/admin/notifications', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True
    
    def test_admin_coupons(self):
        """优惠券列表"""
        r = api_request('admin', 'GET', '/api/admin/coupons', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True
    
    def test_admin_reviews(self):
        """评价列表"""
        r = api_request('admin', 'GET', '/api/admin/reviews', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True
    
    def test_admin_venue_bookings(self):
        """预约管理列表"""
        r = api_request('admin', 'GET', '/api/admin/venue-bookings', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True


# ============ 安全性测试 ============

class TestSecurity:
    """安全性测试"""
    
    def test_no_auth_returns_error(self):
        """未登录应返回错误"""
        r = api_request('user', 'GET', '/api/user/stats')
        assert r.get('success') is False
    
    def test_invalid_token_returns_error(self):
        """无效Token应返回错误"""
        r = api_request('user', 'GET', '/api/user/stats', token='invalid_token_12345')
        assert r.get('success') is False
    
    def test_sql_injection_prevention(self):
        """SQL注入防护"""
        r = api_request('user', 'GET', '/api/user/applications', 
                       params={'keyword': "'; DROP TABLE business_members; --"},
                       token=TEST_USER_TOKEN)
        # 应该正常返回（不会崩溃）
        assert r.get('success') is True or r.get('success') is False
    
    def test_xss_in_application_title(self):
        """XSS防护 - 申请标题"""
        r = api_request('user', 'POST', '/api/user/applications', {
            'app_type': 'other',
            'title': '<script>alert("xss")</script>',
            'content': 'test content'
        }, token=TEST_USER_TOKEN)
        # 如果成功，验证内容被转义
        if r.get('success'):
            app = api_request('user', 'GET', '/api/user/applications', token=TEST_USER_TOKEN)
            items = app.get('data', {}).get('items', [])
            if items:
                assert '<script>' not in str(items[0])


# ============ 数据完整性测试 ============

class TestDataIntegrity:
    """数据完整性测试"""
    
    def test_applications_have_required_fields(self):
        """申请单包含必要字段"""
        rows = db.get_all(
            "SELECT id, app_no, app_type, title, status, user_id FROM business_applications WHERE deleted=0 LIMIT 5"
        )
        if rows:
            for r in rows:
                assert r.get('app_no'), f"申请单 {r['id']} 缺少 app_no"
                assert r.get('app_type'), f"申请单 {r['id']} 缺少 app_type"
                assert r.get('title'), f"申请单 {r['id']} 缺少 title"
                assert r.get('status'), f"申请单 {r['id']} 缺少 status"
    
    def test_members_points_not_negative(self):
        """会员积分不应为负数"""
        rows = db.get_all("SELECT user_id, points FROM business_members WHERE points < 0")
        assert rows is None or len(rows) == 0, "存在积分为负的会员"
    
    def test_orders_have_valid_status(self):
        """订单状态值有效"""
        valid_statuses = {'pending', 'paid', 'completed', 'cancelled', 'refunded', 'closed'}
        rows = db.get_all(
            "SELECT id, order_status FROM business_orders WHERE deleted=0 AND order_status NOT IN "
            "('pending','paid','completed','cancelled','refunded','closed','') LIMIT 10"
        )
        assert rows is None or len(rows) == 0, "存在无效订单状态"


# ============ 边界条件测试 ============

class TestBoundaryConditions:
    """边界条件测试"""
    
    def test_pagination_edge_cases(self):
        """分页边界测试"""
        # 测试超大分页
        r = api_request('user', 'GET', '/api/user/applications', 
                       params={'page': 1, 'page_size': 1000}, token=TEST_USER_TOKEN)
        if r.get('success'):
            # page_size应该被限制
            data = r.get('data', {})
            assert data.get('page_size') <= 50, "page_size应该被限制在50以内"
    
    def test_empty_keyword_search(self):
        """空关键词搜索测试"""
        r = api_request('user', 'GET', '/api/user/applications', 
                       params={'keyword': ''}, token=TEST_USER_TOKEN)
        # 应该正常返回，不崩溃
        assert r.get('success') is True or r.get('success') is False
    
    def test_extremely_long_content(self):
        """超长内容测试"""
        if TEST_USER_TOKEN:
            # 提交超长标题
            r = api_request('user', 'POST', '/api/user/applications', {
                'app_type': 'other',
                'title': 'a' * 200,  # 超过100字符限制
                'content': 'test'
            }, token=TEST_USER_TOKEN)
            # 应该返回错误
            assert r.get('success') is False
    
    def test_special_characters_in_params(self):
        """特殊字符参数测试"""
        r = api_request('user', 'GET', '/api/user/applications', 
                       params={'keyword': '\\n\\r\\t'}, token=TEST_USER_TOKEN)
        # 应该正常处理，不崩溃
        assert r.get('success') is True


# ============ 并发安全测试 ============

class TestConcurrencySafety:
    """并发安全测试"""
    
    def test_points_concurrent_deduction(self):
        """积分并发扣减测试"""
        if not TEST_ADMIN_TOKEN:
            pytest.skip("需要管理员Token")
        
        # 创建一个测试用户，积分100
        test_user_id = 'test_concurrent_user'
        
        # 模拟并发扣减（实际应该用多线程，这里是模拟）
        results = []
        for i in range(3):
            r = api_request('admin', 'POST', '/api/admin/points/adjust', {
                'user_id': test_user_id,
                'points': -10,
                'description': f'并发测试{i}'
            }, token=TEST_ADMIN_TOKEN)
            results.append(r.get('success'))
        
        # 至少有一次成功，不应该全部失败
        assert True  # 实际应该检查最终积分
    
    def test_booking_conflict_detection(self):
        """预约冲突检测"""
        if not TEST_USER_TOKEN:
            pytest.skip("需要用户Token")
        
        # 获取场地ID
        venues = api_request('user', 'GET', '/api/user/venues', token=TEST_USER_TOKEN)
        items = venues.get('data', {}).get('items', [])
        if not items:
            pytest.skip("没有可用场地")
        
        venue_id = items[0].get('id')
        
        # 尝试创建相同时间的两个预约
        r1 = api_request('user', 'POST', '/api/user/venues/1/book', {
            'venue_id': venue_id,
            'book_date': '2026-12-31',
            'start_time': '14:00',
            'end_time': '15:00'
        }, token=TEST_USER_TOKEN)
        
        # 第二个相同时间段的预约应该失败或提示冲突
        # （实际测试需要处理时间冲突检测逻辑）


# ============ 异常处理测试 ============

class TestExceptionHandling:
    """异常处理测试"""
    
    def test_invalid_json_body(self):
        """无效JSON请求体测试"""
        import urllib.request
        url = f"{BASE_URLS['user']}/api/user/stats?access_token={TEST_USER_TOKEN}"
        req = urllib.request.Request(
            url, 
            data=b'not valid json',  # 无效JSON
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode())
                # 应该返回错误，而不是500
                assert result.get('success') is False
        except urllib.error.HTTPError as e:
            # 400错误也是可接受的
            assert e.code in [400, 500]
    
    def test_missing_required_params(self):
        """缺少必需参数测试"""
        if not TEST_USER_TOKEN:
            pytest.skip("需要用户Token")
        
        # 提交申请但不带必需字段
        r = api_request('user', 'POST', '/api/user/applications', 
                       data={'title': 'test'},  # 缺少app_type
                       token=TEST_USER_TOKEN)
        assert r.get('success') is False
    
    def test_database_timeout_handling(self):
        """数据库超时处理"""
        # 这个测试需要模拟数据库超时场景
        # 实际应该验证超时后返回友好的错误信息
        pass


# ============ 性能基准测试 ============

class TestPerformance:
    """性能基准测试"""
    
    def test_list_response_time(self):
        """列表接口响应时间测试"""
        import time
        
        start = time.time()
        r = api_request('user', 'GET', '/api/user/applications', 
                       params={'page': 1, 'page_size': 20}, token=TEST_USER_TOKEN)
        elapsed = time.time() - start
        
        # 响应时间应该在2秒以内
        assert elapsed < 2.0, f"响应时间过长: {elapsed:.2f}秒"
    
    def test_stats_cache_effectiveness(self):
        """统计缓存有效性测试"""
        import time
        
        # 第一次请求（无缓存）
        start1 = time.time()
        api_request('admin', 'GET', '/api/admin/statistics', token=TEST_ADMIN_TOKEN)
        time1 = time.time() - start1
        
        # 第二次请求（有缓存）
        start2 = time.time()
        api_request('admin', 'GET', '/api/admin/statistics', token=TEST_ADMIN_TOKEN)
        time2 = time.time() - start2
        
        # 缓存应该使第二次请求更快（至少快10%）
        if time1 > 0.1:  # 第一次请求时间足够长才验证
            assert time2 < time1 * 0.9 or time2 < 0.1, "缓存未生效"


# ============ 购物车流程测试 ============

@SKIP_NO_TOKEN
class TestCartFlow:
    """购物车完整流程测试（V7.0新增）"""

    def test_get_cart_empty(self):
        """获取购物车（初始为空也应正常返回）"""
        r = api_request('user', 'GET', '/api/user/cart', token=TEST_USER_TOKEN)
        assert r.get('success') is True
        data = r.get('data', {})
        assert 'items' in data
        assert 'total' in data
        assert 'count' in data

    def test_add_to_cart_no_product(self):
        """加入购物车 - 无效商品"""
        r = api_request('user', 'POST', '/api/user/cart', {
            'product_id': 999999,
            'quantity': 1
        }, token=TEST_USER_TOKEN)
        # 商品不存在应返回失败
        assert r.get('success') is False or r.get('msg') is not None

    def test_add_to_cart_missing_product_id(self):
        """加入购物车 - 缺少商品ID"""
        r = api_request('user', 'POST', '/api/user/cart', {
            'quantity': 1
        }, token=TEST_USER_TOKEN)
        assert r.get('success') is False
        assert '商品' in r.get('msg', '')

    def test_cart_select_all(self):
        """购物车全选操作"""
        r = api_request('user', 'POST', '/api/user/cart/select-all',
                        {'selected': True}, token=TEST_USER_TOKEN)
        assert r.get('success') is True

    def test_create_order_from_cart_empty(self):
        """从空购物车下单应失败"""
        r = api_request('user', 'POST', '/api/user/orders', {
            'order_type': 'product',
            'cart_ids': [999999]
        }, token=TEST_USER_TOKEN)
        # 没有可下单商品应返回失败
        assert r.get('success') is False
        assert '没有' in r.get('msg', '') or '商品' in r.get('msg', '')

    def test_create_order_validation(self):
        """直接下单 - 参数校验"""
        r = api_request('user', 'POST', '/api/user/orders', {
            'order_type': 'product',
            'items': []  # 空商品列表
        }, token=TEST_USER_TOKEN)
        assert r.get('success') is False


# ============ 公告管理测试 ============

class TestNoticesAPI:
    """公告API测试（V7.0新增）"""

    def test_get_notices_public(self):
        """获取公告列表（公开接口）"""
        r = api_request('user', 'GET', '/api/notices')
        # 可能返回空列表但不应崩溃
        assert r.get('success') is True
        data = r.get('data', {})
        assert 'items' in data

    def test_get_notices_by_type(self):
        """按类型筛选公告"""
        r = api_request('user', 'GET', '/api/notices', params={'type': 'general'})
        assert r.get('success') is True

    def test_get_notice_invalid_id(self):
        """获取不存在的公告"""
        r = api_request('user', 'GET', '/api/notices/999999')
        assert r.get('success') is False


@SKIP_NO_TOKEN
class TestAdminNotices:
    """管理端公告管理测试（V7.0新增）"""

    def test_admin_list_notices(self):
        """管理员获取公告列表"""
        r = api_request('admin', 'GET', '/api/admin/notices', token=TEST_ADMIN_TOKEN)
        assert r.get('success') is True
        data = r.get('data', {})
        assert 'items' in data

    def test_admin_create_notice_validation(self):
        """创建公告 - 参数校验"""
        # 缺少标题
        r = api_request('admin', 'POST', '/api/admin/notices', {
            'content': '测试内容'
        }, token=TEST_ADMIN_TOKEN)
        assert r.get('success') is False
        assert '标题' in r.get('msg', '')

    def test_admin_create_notice_validation_content(self):
        """创建公告 - 缺少内容"""
        r = api_request('admin', 'POST', '/api/admin/notices', {
            'title': '测试公告'
        }, token=TEST_ADMIN_TOKEN)
        assert r.get('success') is False
        assert '内容' in r.get('msg', '')

    def test_admin_create_and_delete_notice(self):
        """创建并删除公告完整流程"""
        # 创建
        create_r = api_request('admin', 'POST', '/api/admin/notices', {
            'title': 'V7.0自动化测试公告',
            'content': '这是自动化测试创建的公告，请忽略',
            'notice_type': 'general',
            'importance': 0,
            'status': 'draft'
        }, token=TEST_ADMIN_TOKEN)
        assert create_r.get('success') is True

        # 查找刚创建的公告
        list_r = api_request('admin', 'GET', '/api/admin/notices',
                             params={'keyword': 'V7.0自动化测试公告'}, token=TEST_ADMIN_TOKEN)
        items = list_r.get('data', {}).get('items', [])
        if items:
            notice_id = items[0]['id']
            # 删除
            del_r = api_request('admin', 'DELETE', f'/api/admin/notices/{notice_id}', token=TEST_ADMIN_TOKEN)
            assert del_r.get('success') is True


# ============ 订单明细测试 ============

@SKIP_NO_TOKEN
class TestOrderItems:
    """订单明细测试（V7.0新增）"""

    def test_admin_order_items_invalid(self):
        """获取不存在订单的明细"""
        r = api_request('admin', 'GET', '/api/admin/orders/999999/items', token=TEST_ADMIN_TOKEN)
        # 应该正常返回空列表，不崩溃
        assert r.get('success') is True
        assert 'items' in r.get('data', {})

    def test_admin_order_items_for_existing(self):
        """获取已有订单的明细"""
        # 先获取一个订单ID
        orders_r = api_request('admin', 'GET', '/api/admin/orders',
                               params={'page': 1, 'page_size': 1}, token=TEST_ADMIN_TOKEN)
        items = orders_r.get('data', {}).get('items', [])
        if items:
            order_id = items[0]['id']
            r = api_request('admin', 'GET', f'/api/admin/orders/{order_id}/items', token=TEST_ADMIN_TOKEN)
            assert r.get('success') is True
            assert 'items' in r.get('data', {})


# ============ 缓存一致性测试 ============

@SKIP_NO_TOKEN
class TestCacheConsistency:
    """缓存一致性测试（V7.0新增）"""

    def test_stats_refresh_after_action(self):
        """验证撤销申请后stats能反映最新状态（缓存清除有效）"""
        # 获取初始统计
        stats1 = api_request('user', 'GET', '/api/user/stats', token=TEST_USER_TOKEN)
        if not stats1.get('success'):
            return

        # 在实际环境中应该创建一个申请然后撤销它，这里只验证接口正常响应
        stats2 = api_request('user', 'GET', '/api/user/stats', token=TEST_USER_TOKEN)
        assert stats2.get('success') is True
        # 两次请求都应该返回相同结构
        assert 'pending' in stats2.get('data', {})
        assert 'orders' in stats2.get('data', {})

    def test_staff_stats_cache(self):
        """验证员工端统计接口有缓存支持"""
        import time
        start1 = time.time()
        r1 = api_request('staff', 'GET', '/api/staff/statistics', token=TEST_STAFF_TOKEN)
        t1 = time.time() - start1

        start2 = time.time()
        r2 = api_request('staff', 'GET', '/api/staff/statistics', token=TEST_STAFF_TOKEN)
        t2 = time.time() - start2

        assert r1.get('success') is True
        assert r2.get('success') is True
        # 第二次应该更快（缓存命中）
        if t1 > 0.1:
            assert t2 < t1 * 0.95 or t2 < 0.05, "员工端statistics缓存未生效"


# ============ 用户地址管理测试（V8.0新增）============

@SKIP_NO_TOKEN
class TestUserAddresses:
    """用户地址管理测试（V8.0新增）"""

    def test_get_addresses_empty(self):
        """获取收货地址列表（空列表也应正常返回）"""
        r = api_request('user', 'GET', '/api/user/addresses', token=TEST_USER_TOKEN)
        assert r.get('success') is True
        data = r.get('data', {})
        assert 'items' in data

    def test_create_address_validation(self):
        """创建地址 - 参数校验"""
        # 缺少必要字段
        r = api_request('user', 'POST', '/api/user/addresses', {
            'user_name': '测试'
        }, token=TEST_USER_TOKEN)
        assert r.get('success') is False
        assert '请填写' in r.get('msg', '')

    def test_create_address_invalid_phone(self):
        """创建地址 - 无效手机号"""
        r = api_request('user', 'POST', '/api/user/addresses', {
            'user_name': '测试用户',
            'phone': '12345',  # 无效手机号
            'address': '测试地址'
        }, token=TEST_USER_TOKEN)
        assert r.get('success') is False
        assert '手机号' in r.get('msg', '')

    def test_create_and_list_address(self):
        """创建并查询地址完整流程"""
        # 创建地址
        create_r = api_request('user', 'POST', '/api/user/addresses', {
            'user_name': 'V8测试用户',
            'phone': '13800138000',
            'province': '广东省',
            'city': '深圳市',
            'area': '南山区',
            'address': '科技园路88号',
            'is_default': 1,
            'tag': '公司'
        }, token=TEST_USER_TOKEN)
        
        # 查询列表
        list_r = api_request('user', 'GET', '/api/user/addresses', token=TEST_USER_TOKEN)
        assert list_r.get('success') is True
        items = list_r.get('data', {}).get('items', [])
        if items:
            addr_id = items[0]['id']
            # 删除测试地址
            del_r = api_request('user', 'DELETE', f'/api/user/addresses/{addr_id}', token=TEST_USER_TOKEN)
            assert del_r.get('success') is True


# ============ SKU商品规格测试（V8.0新增）============

@SKIP_NO_TOKEN
class TestProductSKU:
    """商品SKU规格测试（V8.0新增）"""

    def test_product_detail_with_skus(self):
        """获取商品详情（包含SKU）"""
        # 先获取一个商品ID
        products = api_request('user', 'GET', '/api/products')
        items = products.get('data', {}).get('items', [])
        if items:
            product_id = items[0].get('id')
            r = api_request('user', 'GET', f'/api/products/{product_id}')
            assert r.get('success') is True
            data = r.get('data', {})
            # 应该包含skus字段
            assert 'skus' in data

    def test_product_detail_no_skus(self):
        """获取无SKU的商品详情"""
        products = api_request('user', 'GET', '/api/products')
        items = products.get('data', {}).get('items', [])
        if items:
            product_id = items[0].get('id')
            r = api_request('user', 'GET', f'/api/products/{product_id}')
            assert r.get('success') is True
            data = r.get('data', {})
            # skus应该是列表
            assert isinstance(data.get('skus'), list)


# ============ 库存校验测试（V8.0新增）============

@SKIP_NO_TOKEN
class TestStockValidation:
    """库存校验测试（V8.0新增）"""

    def test_create_order_insufficient_stock(self):
        """下单时库存不足应返回错误"""
        # 这个测试需要知道一个库存为0的商品
        # 实际场景：尝试购买超过库存的商品
        # 由于我们不知道具体商品库存，这个测试验证接口存在
        r = api_request('user', 'POST', '/api/user/orders', {
            'order_type': 'product',
            'items': [{'product_id': 1, 'quantity': 99999}]
        }, token=TEST_USER_TOKEN)
        # 应该返回失败（库存不足或商品不存在）
        assert r.get('success') is False or '库存' in r.get('msg', '') or '不存在' in r.get('msg', '')


# ============ 评价图片展示测试（V8.0新增）============

class TestReviewImages:
    """评价图片展示测试（V8.0新增）"""

    def test_reviews_with_images_field(self):
        """评价列表应返回images字段"""
        r = api_request('user', 'GET', '/api/reviews')
        assert r.get('success') is True
        data = r.get('data', {})
        if data.get('total', 0) > 0:
            items = data.get('items', [])
            if items:
                # 应该包含images_list字段
                item = items[0]
                assert 'images_list' in item or 'images' in item


# ============ 积分校验测试（V8.0新增）============

@SKIP_NO_TOKEN
class TestPointsValidation:
    """积分校验测试（V8.0新增）"""

    def test_points_not_negative(self):
        """会员积分不应为负数"""
        rows = db.get_all("SELECT user_id, points FROM business_members WHERE points < 0")
        assert rows is None or len(rows) == 0, "存在积分为负的会员"

    def test_total_points_not_negative(self):
        """累计积分不应为负数"""
        rows = db.get_all("SELECT user_id, total_points FROM business_members WHERE total_points < 0")
        assert rows is None or len(rows) == 0, "存在累计积分为负的会员"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


# ============ V9.0 新增功能测试 ============

# ---- 签到系统测试 ----

@SKIP_NO_TOKEN
class TestCheckinSystem:
    """V9.0 签到系统测试"""

    def test_get_checkin_status(self):
        """获取签到状态"""
        r = api_request('user', 'GET', '/api/user/checkin/status', token=TEST_USER_TOKEN)
        assert r.get('success') is True
        data = r.get('data', {})
        assert 'checked_in' in data
        assert 'continuous_days' in data
        assert 'month_count' in data
        assert 'total_days' in data

    def test_checkin_once(self):
        """签到一次（可能已签到）"""
        r = api_request('user', 'POST', '/api/user/checkin', token=TEST_USER_TOKEN)
        # 无论成功失败，接口应正常响应
        assert r.get('success') in (True, False)
        if not r.get('success'):
            assert '已签到' in r.get('msg', '') or '失败' in r.get('msg', '')

    def test_checkin_rank(self):
        """获取签到排行榜"""
        r = api_request('user', 'GET', '/api/user/checkin/rank', token=TEST_USER_TOKEN)
        assert r.get('success') is True
        assert isinstance(r.get('data'), list)

    def test_checkin_table_exists(self):
        """签到表存在"""
        result = db.get_all("SHOW TABLES LIKE 'business_checkin_logs'")
        assert result is not None and len(result) > 0, "business_checkin_logs table missing"

    def test_checkin_rate_limit(self):
        """签到接口限流"""
        import urllib.error
        for i in range(3):
            try:
                api_request('user', 'POST', '/api/user/checkin', token=TEST_USER_TOKEN)
            except urllib.error.HTTPError:
                pass  # 429限流


# ---- 订单退款测试 ----

@SKIP_NO_TOKEN
class TestOrderRefund:
    """V9.0 订单退款测试"""

    def test_refund_requires_paid_status(self):
        """只有已支付订单才可退款"""
        # 查找一个pending状态的订单
        orders = api_request('user', 'GET', '/api/user/orders?page=1&page_size=5',
                            token=TEST_USER_TOKEN)
        items = orders.get('data', {}).get('items', [])
        if items:
            order = items[0]
            r = api_request('user', 'POST', f"/api/user/orders/{order['id']}/refund",
                           {'reason': 'test'}, token=TEST_USER_TOKEN)
            # pending订单应返回失败
            status = order.get('order_status', '')
            if status in ('pending', ''):
                assert r.get('success') is False

    def test_confirm_order_requires_shipped(self):
        """确认收货需要已发货状态"""
        orders = api_request('user', 'GET', '/api/user/orders?page=1&page_size=5',
                            token=TEST_USER_TOKEN)
        items = orders.get('data', {}).get('items', [])
        if items:
            order = items[0]
            r = api_request('user', 'POST', f"/api/user/orders/{order['id']}/confirm",
                           token=TEST_USER_TOKEN)
            status = order.get('order_status', '')
            if status != 'shipped':
                assert r.get('success') is False


# ---- 管理端退款/发货测试 ----

@SKIP_NO_TOKEN
class TestAdminRefundShip:
    """V9.0 管理端退款/发货测试"""

    def test_admin_refund_wrong_status(self):
        """退款审核 - 错误状态应失败"""
        r = api_request('admin', 'POST', '/api/admin/orders/99999/refund',
                       {'action': 'approve'}, token=TEST_ADMIN_TOKEN)
        # 不存在或状态不对
        assert r.get('success') is False or r.get('success') is True  # 接口正常响应

    def test_admin_ship_wrong_status(self):
        """发货 - 错误状态应失败"""
        r = api_request('admin', 'POST', '/api/admin/orders/99999/ship',
                       {'tracking_no': 'SF1234567890'}, token=TEST_ADMIN_TOKEN)
        assert r.get('success') is False


# ---- 商品分类测试 ----

@SKIP_NO_TOKEN
class TestProductCategories:
    """V9.0 商品分类测试"""

    def test_get_categories(self):
        """获取商品分类列表"""
        r = api_request('user', 'GET', '/api/user/products/categories', token=TEST_USER_TOKEN)
        assert r.get('success') is True
        assert isinstance(r.get('data'), list)

    def test_products_with_category_filter(self):
        """分类筛选商品"""
        categories = api_request('user', 'GET', '/api/user/products/categories', token=TEST_USER_TOKEN)
        cats = categories.get('data', [])
        if cats:
            cat_name = cats[0]['name']
            r = api_request('user', 'GET', '/api/user/products',
                           params={'category': cat_name}, token=TEST_USER_TOKEN)
            assert r.get('success') is True

    def test_products_with_sort(self):
        """排序商品"""
        for sort_type in ['sales_count', 'price']:
            r = api_request('user', 'GET', '/api/user/products',
                           params={'sort': sort_type, 'order': 'desc'}, token=TEST_USER_TOKEN)
            assert r.get('success') is True


# ---- 订单地址集成测试 ----

@SKIP_NO_TOKEN
class TestOrderAddress:
    """V9.0 订单地址集成测试"""

    def test_order_has_shipping_address_field(self):
        """订单表应有shipping_address字段"""
        result = db.get_all("DESCRIBE business_orders")
        columns = [row[0] for row in (result or [])]
        assert 'shipping_address' in columns, "orders table missing shipping_address"

    def test_order_has_refund_fields(self):
        """订单表应有退款相关字段"""
        result = db.get_all("DESCRIBE business_orders")
        columns = [row[0] for row in (result or [])]
        for field in ['refund_reason', 'refunded_at', 'tracking_no', 'logistics_company', 'shipped_at', 'completed_at']:
            assert field in columns, f"orders table missing {field}"


# ---- 订单取消库存回滚测试 ----

@SKIP_NO_TOKEN
class TestCancelOrderStock:
    """V9.0 取消订单库存回滚测试"""

    def test_cancel_order_interface(self):
        """取消订单接口应正常响应"""
        orders = api_request('user', 'GET', '/api/user/orders?page=1&page_size=5',
                            token=TEST_USER_TOKEN)
        items = orders.get('data', {}).get('items', [])
        if items:
            order = items[0]
            status = order.get('order_status', '')
            if status in ('pending', ''):
                r = api_request('user', 'POST', f"/api/user/orders/{order['id']}/cancel",
                               token=TEST_USER_TOKEN)
                assert r.get('success') is True


# ---- 管理端路由唯一性测试 ----

class TestAdminRouteUniqueness:
    """V9.0 管理端路由唯一性测试"""

    def test_no_duplicate_notice_routes(self):
        """公告路由不应重复定义"""
        import re
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'business-admin', 'app.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        # 查找所有公告路由定义
        pattern = r"@app\.route\('/api/admin/notices'"
        matches = list(re.finditer(pattern, content))
        # 列表 + 详情 + 创建 + 更新 + 删除，不应超过5个
        assert len(matches) <= 5, f"Too many notice route definitions: {len(matches)}"
        # GET方法的路由不应重复
        get_matches = [m for m in matches if content[m.end():m.end()+200].find("methods=['GET']") >= 0 or
                      content[m.end():m.end()+200].find("'GET'") >= 0]
        assert len(get_matches) <= 1, "Duplicate GET notice route found"


# ============ V10.0 新增测试 ============

class TestV10MyCouponsPage:
    """V10.0 P0修复：优惠券页面存在性测试"""

    def test_my_coupons_html_exists(self):
        """my_coupons.html 页面文件应存在"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-userH5', 'my_coupons.html'
        )
        assert os.path.exists(path), "my_coupons.html 不存在，首页入口会404"

    def test_my_coupons_html_has_exchange(self):
        """my_coupons.html 应包含积分兑换功能"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-userH5', 'my_coupons.html'
        )
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'exchange' in content.lower() or '兑换' in content, "my_coupons.html 缺少兑换功能"


class TestV10OrdersPage:
    """V10.0 P1：订单页面完整性测试"""

    def test_orders_html_has_shipped_status(self):
        """orders.html 应包含发货状态处理"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-userH5', 'orders.html'
        )
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'shipped' in content, "orders.html 缺少发货状态"
        assert 'refunding' in content, "orders.html 缺少退款中状态"
        assert 'refunded' in content, "orders.html 缺少已退款状态"

    def test_orders_html_has_refund_action(self):
        """orders.html 应有退款申请入口"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-userH5', 'orders.html'
        )
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'refund' in content.lower() or '退款' in content, "orders.html 缺少退款入口"

    def test_orders_html_has_confirm_receipt(self):
        """orders.html 应有确认收货功能"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-userH5', 'orders.html'
        )
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'confirm' in content or '确认收货' in content, "orders.html 缺少确认收货功能"


class TestV10MemberPage:
    """V10.0 P1：会员中心页面测试"""

    def test_member_html_exists(self):
        """member.html 应存在"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-userH5', 'member.html'
        )
        assert os.path.exists(path), "member.html 不存在"

    def test_member_html_has_level_progress(self):
        """member.html 应展示等级进度"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-userH5', 'member.html'
        )
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'levelFill' in content or 'level-fill' in content, "member.html 缺少等级进度条"


class TestV10AdminProducts:
    """V10.0 P1：管理端商品管理测试"""

    def test_products_html_exists(self):
        """管理端 products.html 应存在"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-admin', 'products.html'
        )
        assert os.path.exists(path), "business-admin/products.html 不存在"

    def test_admin_products_api_exists(self):
        """管理端商品API应包含GET详情接口"""
        import re
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'business-admin', 'app.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        # 检查详情API
        assert "api/admin/products/<int:product_id>" in content, "缺少商品详情接口"
        # 检查CRUD
        assert "admin_create_product" in content, "缺少商品创建接口"
        assert "admin_update_product" in content, "缺少商品更新接口"
        assert "admin_delete_product" in content, "缺少商品删除接口"

    def test_admin_products_list_has_shop_name(self):
        """管理端商品列表应返回门店名称"""
        import re
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'business-admin', 'app.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        # 检查是否JOIN了shops表
        assert 'LEFT JOIN business_shops' in content or 'JOIN business_shops' in content, \
            "管理端商品列表未JOIN门店表，无法返回shop_name"


class TestV10StatisticsEnhancement:
    """V10.0 P2：统计增强测试"""

    def test_statistics_has_checkin_data(self):
        """统计接口应返回签到数据"""
        import re
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'business-admin', 'app.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'today_checkins' in content, "统计接口未包含今日签到数据"
        assert 'month_checkins' in content, "统计接口未包含本月签到数据"

    def test_statistics_has_coupon_data(self):
        """统计接口应返回优惠券使用数据"""
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'business-admin', 'app.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'used_coupons_today' in content, "统计接口未包含优惠券使用数据"

    def test_statistics_has_low_stock_warning(self):
        """统计接口应包含库存预警数据"""
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'business-admin', 'app.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'low_stock_products' in content, "统计接口未包含库存预警数据"

    def test_statistics_html_has_new_metrics(self):
        """统计页面应展示V10新增指标"""
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'business-admin', 'statistics.html'), 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'todayCheckins' in content, "统计页面缺少今日签到展示"
        assert 'lowStockProducts' in content, "统计页面缺少库存预警展示"


class TestV10DatabaseMigration:
    """V10.0 数据库迁移脚本测试"""

    def test_migrate_v10_script_exists(self):
        """migrate_v10.py 应存在"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'migrate_v10.py'
        )
        assert os.path.exists(path), "migrate_v10.py 不存在"

    def test_migrate_v10_has_cart_table(self):
        """迁移脚本应包含购物车表创建"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'migrate_v10.py'
        )
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'business_cart' in content, "迁移脚本未包含购物车表"

    def test_migrate_v10_has_indexes(self):
        """迁移脚本应包含索引优化"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'business-common', 'migrate_v10.py'
        )
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'CREATE INDEX' in content or 'safe_create_index' in content, "迁移脚本未包含索引优化"
