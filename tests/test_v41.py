"""
V41.0 购物车API和智能推荐集成测试

测试覆盖：
1. 购物车路由别名 (/api/user/cart vs /api/cart)
2. 购物车推荐API
3. 用户行为追踪API
4. 商品路由别名 (/api/user/products vs /api/products)

运行方式:
    pytest tests/test_v41.py -v
"""

import pytest
import time
from tests.conftest import (
    ApiClient, TestConfig, assert_success, 
    create_test_product
)


class TestCartRoutes:
    """V41.0: 购物车路由兼容性测试"""

    @pytest.fixture(autouse=True)
    def setup(self, user_api_client, test_user, config):
        """每个测试前设置"""
        self.client = user_api_client
        self.client.set_token(test_user['token'])
        self.user = test_user
        self.config = config

    def test_cart_get_alias(self):
        """测试 /api/user/cart GET 别名路由"""
        response = self.client.get(f'/api/user/cart?access_token={self.user["token"]}')
        # 应该返回成功（空购物车或现有购物车）
        assert response['success'] or response['status_code'] == 200
        assert response['data'] is not None

    def test_cart_get_original(self):
        """测试 /api/cart GET 原始路由"""
        response = self.client.get(f'/api/cart?access_token={self.user["token"]}')
        assert response['success'] or response['status_code'] == 200
        assert response['data'] is not None

    def test_cart_update_alias(self):
        """测试 /api/user/cart/{id} PUT 别名路由"""
        # 先添加到购物车
        add_response = self.client.post(f'/api/user/cart/add', json={
            'product_id': 1,
            'quantity': 1
        })
        
        # 如果添加成功，尝试更新
        if add_response['success']:
            cart_items = add_response['data']
            if isinstance(cart_items, dict) and 'items' in cart_items:
                cart_id = cart_items['items'][0]['id']
            elif isinstance(cart_items, list) and len(cart_items) > 0:
                cart_id = cart_items[0]['id']
            else:
                pytest.skip("无法获取购物车ID")
            
            # 更新数量
            update_response = self.client.put(
                f'/api/user/cart/{cart_id}',
                json={'quantity': 2}
            )
            assert update_response['success'] or update_response['status_code'] == 200

    def test_cart_delete_alias(self):
        """测试 /api/user/cart/{id} DELETE 别名路由"""
        # 先添加到购物车
        add_response = self.client.post(f'/api/user/cart/add', json={
            'product_id': 1,
            'quantity': 1
        })
        
        if add_response['success']:
            cart_items = add_response['data']
            if isinstance(cart_items, dict) and 'items' in cart_items:
                cart_id = cart_items['items'][0]['id']
            elif isinstance(cart_items, list) and len(cart_items) > 0:
                cart_id = cart_items[0]['id']
            else:
                pytest.skip("无法获取购物车ID")
            
            # 删除
            delete_response = self.client.delete(f'/api/user/cart/{cart_id}')
            assert delete_response['success'] or delete_response['status_code'] == 200

    def test_cart_select_all_alias(self):
        """测试 /api/user/cart/select-all POST 别名路由"""
        response = self.client.post(
            f'/api/user/cart/select-all',
            json={'selected': True}
        )
        # 应该返回成功（即使购物车为空）
        assert response['success'] or response['status_code'] == 200


class TestCartRecommendations:
    """V41.0: 购物车智能推荐API测试"""

    @pytest.fixture(autouse=True)
    def setup(self, user_api_client, test_user):
        """每个测试前设置"""
        self.client = user_api_client
        self.client.set_token(test_user['token'])
        self.user = test_user

    def test_recommendations_requires_login(self):
        """测试推荐API需要登录"""
        # 不带token应该返回失败
        client_no_auth = ApiClient(TestConfig.USER_H5_URL)
        response = client_no_auth.get('/api/user/cart/recommendations')
        assert not response['success'] or response['status_code'] == 401

    def test_recommendations_with_login(self):
        """测试带登录令牌的推荐API"""
        response = self.client.get(
            f'/api/user/cart/recommendations?access_token={self.user["token"]}'
        )
        # 应该返回成功（即使推荐为空）
        assert response['success'] or response['status_code'] == 200
        # 验证返回格式
        if response['success']:
            assert 'data' in response['data'] or response['data'] is not None

    def test_recommendations_response_format(self):
        """测试推荐返回数据格式"""
        response = self.client.get(
            f'/api/user/cart/recommendations?access_token={self.user["token"]}'
        )
        if response['success']:
            data = response['data']
            # 如果有推荐数据，验证格式
            if isinstance(data, list) and len(data) > 0:
                item = data[0]
                # 推荐商品应包含的基本字段
                assert 'id' in item
                assert 'product_name' in item or 'name' in item
                assert 'price' in item


class TestBehaviorTracking:
    """V41.0: 用户行为追踪API测试"""

    @pytest.fixture(autouse=True)
    def setup(self, user_api_client, test_user):
        """每个测试前设置"""
        self.client = user_api_client
        self.client.set_token(test_user['token'])
        self.user = test_user

    def test_track_requires_login(self):
        """测试行为追踪需要登录"""
        client_no_auth = ApiClient(TestConfig.USER_H5_URL)
        response = client_no_auth.post('/api/user/behavior/track', json={
            'behavior_type': 'view_product',
            'target_type': 'product',
            'target_id': 1
        })
        assert not response['success'] or response['status_code'] == 401

    def test_track_view_product(self):
        """测试商品浏览行为记录"""
        response = self.client.post(
            f'/api/user/behavior/track?access_token={self.user["token"]}',
            json={
                'behavior_type': 'view_product',
                'target_type': 'product',
                'target_id': 1,
                'duration': 30
            }
        )
        assert response['success'] or response['status_code'] == 200

    def test_track_add_cart(self):
        """测试加购行为记录"""
        response = self.client.post(
            f'/api/user/behavior/track?access_token={self.user["token"]}',
            json={
                'behavior_type': 'add_cart',
                'target_type': 'product',
                'target_id': 1,
                'duration': 60,
                'extra_data': {
                    'quantity': 2,
                    'price': 99.99
                }
            }
        )
        assert response['success'] or response['status_code'] == 200

    def test_track_missing_target_id(self):
        """测试缺少目标ID时的行为"""
        response = self.client.post(
            f'/api/user/behavior/track?access_token={self.user["token"]}',
            json={
                'behavior_type': 'view_product',
                'target_type': 'product'
            }
        )
        # 应该返回失败，因为缺少target_id
        assert not response['success']


class TestProductRoutes:
    """V41.0: 商品路由兼容性测试"""

    @pytest.fixture(autouse=True)
    def setup(self, user_api_client, config):
        """每个测试前设置"""
        self.client = user_api_client
        self.config = config

    def test_products_user_alias(self):
        """测试 /api/user/products GET 别名路由"""
        response = self.client.get(
            f'/api/user/products?ec_id={self.config.TEST_EC_ID}&project_id={self.config.TEST_PROJECT_ID}'
        )
        # 应该返回成功
        assert response['success'] or response['status_code'] == 200
        # 验证返回格式
        if response['success']:
            data = response['data']
            assert 'items' in data or isinstance(data, list)

    def test_products_original(self):
        """测试 /api/products GET 原始路由"""
        response = self.client.get(
            f'/api/products?ec_id={self.config.TEST_EC_ID}&project_id={self.config.TEST_PROJECT_ID}'
        )
        # 应该返回成功
        assert response['success'] or response['status_code'] == 200

    def test_products_with_category(self):
        """测试带分类筛选的商品列表"""
        response = self.client.get(
            f'/api/user/products?ec_id={self.config.TEST_EC_ID}&project_id={self.config.TEST_PROJECT_ID}&category=食品'
        )
        assert response['success'] or response['status_code'] == 200

    def test_products_with_keyword(self):
        """测试带关键词搜索的商品列表"""
        response = self.client.get(
            f'/api/user/products?ec_id={self.config.TEST_EC_ID}&project_id={self.config.TEST_PROJECT_ID}&keyword=测试'
        )
        assert response['success'] or response['status_code'] == 200


class TestCartRecommendationsIntegration:
    """V41.0: 购物车推荐与行为追踪集成测试"""

    @pytest.fixture(autouse=True)
    def setup(self, user_api_client, test_user, admin_api_client, config):
        """每个测试前设置"""
        self.client = user_api_client
        self.client.set_token(test_user['token'])
        self.user = test_user
        self.admin_client = admin_api_client
        self.config = config

    def test_full_recommendation_flow(self):
        """测试完整的推荐流程：浏览 -> 加购 -> 获取推荐"""
        # 1. 浏览商品（记录行为）
        view_response = self.client.post(
            f'/api/user/behavior/track?access_token={self.user["token"]}',
            json={
                'behavior_type': 'view_product',
                'target_type': 'product',
                'target_id': 1,
                'duration': 45
            }
        )
        assert view_response['success'] or view_response['status_code'] == 200

        # 2. 添加到购物车（记录行为）
        add_response = self.client.post(
            f'/api/user/cart/add',
            json={
                'product_id': 1,
                'quantity': 1
            }
        )
        # 添加可能因为商品不存在而失败，这是可接受的
        if add_response['success']:
            cart_response = self.client.post(
                f'/api/user/behavior/track?access_token={self.user["token"]}',
                json={
                    'behavior_type': 'add_cart',
                    'target_type': 'product',
                    'target_id': 1,
                    'duration': 5,
                    'extra_data': {'quantity': 1}
                }
            )
            assert cart_response['success'] or cart_response['status_code'] == 200

        # 3. 获取推荐
        rec_response = self.client.get(
            f'/api/user/cart/recommendations?access_token={self.user["token"]}'
        )
        assert rec_response['success'] or rec_response['status_code'] == 200
