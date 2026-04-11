"""
V42.0 自动化测试
测试范围：
  - 商品多规格属性体系 API
  - 商品问答系统 API
  - 秒杀倒计时 API
  - 会员数字卡 API
  - 追加评价 API

依赖：pytest, requests
"""

import pytest
import json
import time
from datetime import datetime


# ============ 测试配置 ============

BASE_URL = "http://127.0.0.1:22311"
ADMIN_BASE_URL = "http://127.0.0.1:22313"
TEST_TIMEOUT = 10

# 测试账号（需要先创建）
TEST_USER = {
    "phone": "13800138001",
    "password": "Test123456",
    "user_name": "测试用户"
}

TEST_STAFF = {
    "phone": "13900139001",
    "password": "Staff123456",
    "role": "staff"
}

TEST_ADMIN = {
    "phone": "13700137001",
    "password": "Admin123456",
    "role": "admin"
}


# ============ 辅助函数 ============

def get_headers(token=None):
    """构建请求头"""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Token"] = token
    return headers


def api_get(path, token=None, params=None):
    """GET请求"""
    url = f"{BASE_URL}{path}"
    headers = get_headers(token)
    resp = pytest.client.get(url, headers=headers, query_string=params)
    return resp


def api_post(path, token=None, json_data=None):
    """POST请求"""
    url = f"{BASE_URL}{path}"
    headers = get_headers(token)
    resp = pytest.client.post(url, headers=headers, json=json_data)
    return resp


def api_put(path, token=None, json_data=None):
    """PUT请求"""
    url = f"{BASE_URL}{path}"
    headers = get_headers(token)
    resp = pytest.client.put(url, headers=headers, json=json_data)
    return resp


def api_delete(path, token=None):
    """DELETE请求"""
    url = f"{BASE_URL}{path}"
    headers = get_headers(token)
    resp = pytest.client.delete(url, headers=headers)
    return resp


def admin_api_get(path, token=None):
    """管理端GET请求"""
    url = f"{ADMIN_BASE_URL}{path}"
    headers = get_headers(token)
    resp = pytest.client.get(url, headers=headers)
    return resp


def admin_api_post(path, token=None, json_data=None):
    """管理端POST请求"""
    url = f"{ADMIN_BASE_URL}{path}"
    headers = get_headers(token)
    resp = pytest.client.post(url, headers=headers, json=json_data)
    return resp


def get_test_token(user_phone, user_password):
    """登录获取Token"""
    resp = api_post("/api/login", json_data={
        "phone": user_phone,
        "password": user_password
    })
    if resp.status_code == 200:
        data = json.loads(resp.data)
        if data.get("success"):
            return data["data"]["access_token"]
    return None


# ============ Fixtures ============

@pytest.fixture(scope="module")
def client():
    """Flask测试客户端"""
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


@pytest.fixture(scope="module")
def admin_client():
    """管理端测试客户端"""
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


@pytest.fixture(scope="module")
def user_token(client):
    """获取测试用户Token"""
    token = get_test_token(TEST_USER["phone"], TEST_USER["password"])
    if not token:
        pytest.skip(f"无法获取测试用户Token: {TEST_USER['phone']}")
    return token


@pytest.fixture(scope="module")
def staff_token(client):
    """获取员工Token"""
    token = get_test_token(TEST_STAFF["phone"], TEST_STAFF["password"])
    if not token:
        pytest.skip(f"无法获取员工Token: {TEST_STAFF['phone']}")
    return token


@pytest.fixture(scope="module")
def admin_token(admin_client):
    """获取管理员Token"""
    token = get_test_token(TEST_ADMIN["phone"], TEST_ADMIN["password"])
    if not token:
        pytest.skip(f"无法获取管理员Token: {TEST_ADMIN['phone']}")
    return token


@pytest.fixture(scope="module")
def test_product_id(client, admin_token):
    """创建测试商品"""
    resp = admin_api_post("/api/admin/products", token=admin_token, json_data={
        "product_name": f"测试商品_{int(time.time())}",
        "price": 99.99,
        "stock": 100,
        "category": "测试分类",
        "description": "自动化测试商品"
    })
    if resp.status_code == 200:
        data = json.loads(resp.data)
        if data.get("success"):
            return data["data"]["id"]
    pytest.skip("无法创建测试商品")


# ============ V42.0 商品规格属性测试 ============

class TestProductSpec:
    """商品多规格属性测试"""

    def test_get_spec_groups_empty(self, client, test_product_id):
        """获取规格组 - 空列表"""
        resp = api_get(f"/api/user/products/{test_product_id}/specs")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        assert isinstance(data["data"], list)

    def test_add_spec_group(self, client, admin_token, test_product_id):
        """添加规格组"""
        resp = admin_api_post(f"/api/admin/products/{test_product_id}/specs", token=admin_token, json_data={
            "spec_name": "颜色",
            "values": ["红色", "蓝色", "黑色"]
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        assert "spec_id" in data["data"]

    def test_add_spec_with_extra_price(self, client, admin_token, test_product_id):
        """添加规格组 - 带附加价格"""
        resp = admin_api_post(f"/api/admin/products/{test_product_id}/specs", token=admin_token, json_data={
            "spec_name": "容量",
            "values": ["64GB:+0", "128GB:+100", "256GB:+200"]
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True

    def test_get_spec_groups(self, client, test_product_id):
        """获取规格组"""
        resp = api_get(f"/api/user/products/{test_product_id}/specs")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        assert len(data["data"]) >= 2  # 至少两个规格组

    def test_generate_sku_matrix(self, client, test_product_id):
        """生成SKU矩阵"""
        resp = api_get(f"/api/user/products/{test_product_id}/sku/matrix")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        assert isinstance(data["data"], list)
        # 验证笛卡尔积：2种颜色 x 3种容量 = 6个SKU
        if len(data["data"]) > 0:
            assert len(data["data"]) == 6

    def test_create_sku(self, client, admin_token, test_product_id):
        """创建SKU"""
        resp = api_post(
            f"/api/user/products/{test_product_id}/sku/create",
            token=admin_token,
            json_data={
                "specs": {"颜色": "红色", "容量": "128GB"},
                "price": 199.99,
                "stock": 50
            }
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        assert "sku_id" in data["data"]

    def test_update_sku_price_stock(self, client, admin_token, test_product_id):
        """更新SKU价格和库存"""
        # 先创建SKU
        create_resp = api_post(
            f"/api/user/products/{test_product_id}/sku/create",
            token=admin_token,
            json_data={
                "specs": {"颜色": "蓝色", "容量": "128GB"},
                "price": 199.99,
                "stock": 30
            }
        )
        create_data = json.loads(create_resp.data)
        sku_id = create_data["data"]["sku_id"]

        # 更新SKU
        update_resp = api_put(
            f"/api/user/skus/{sku_id}",
            token=admin_token,
            json_data={
                "price": 179.99,
                "stock": 25
            }
        )
        assert update_resp.status_code == 200
        update_data = json.loads(update_resp.data)
        assert update_data["success"] == True


# ============ V42.0 商品问答测试 ============

class TestProductQA:
    """商品问答测试"""

    def test_get_qa_list_empty(self, client, test_product_id):
        """获取问答列表 - 空"""
        resp = api_get(f"/api/user/products/{test_product_id}/qa")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        assert "items" in data["data"]
        assert "stats" in data["data"]

    def test_get_qa_stats(self, client, test_product_id):
        """获取问答统计"""
        resp = api_get(f"/api/user/products/{test_product_id}/qa/stats")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        stats = data["data"]
        assert "total" in stats
        assert "answered" in stats
        assert "pending" in stats

    def test_submit_question(self, client, user_token, test_product_id):
        """提交问题"""
        resp = api_post(
            f"/api/user/qa",
            token=user_token,
            json_data={
                "product_id": test_product_id,
                "content": "这个商品的质量怎么样？"
            }
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        assert "qa_id" in data["data"]
        return data["data"]["qa_id"]

    def test_submit_question_short_content(self, client, user_token, test_product_id):
        """提交问题 - 内容过短"""
        resp = api_post(
            f"/api/user/qa",
            token=user_token,
            json_data={
                "product_id": test_product_id,
                "content": "好"
            }
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == False

    def test_submit_question_no_login(self, client, test_product_id):
        """提交问题 - 未登录"""
        resp = api_post(
            f"/api/user/qa",
            json_data={
                "product_id": test_product_id,
                "content": "未登录用户提问"
            }
        )
        assert resp.status_code == 401

    def test_get_my_questions(self, client, user_token):
        """获取我的提问"""
        resp = api_get("/api/user/qa/my", token=user_token)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        assert "items" in data["data"]

    def test_answer_question(self, client, admin_token, test_product_id):
        """回复问题"""
        # 先提交一个问题
        qa_resp = api_post(
            f"/api/user/qa",
            token=user_token,
            json_data={
                "product_id": test_product_id,
                "content": "商品发货快吗？"
            }
        )
        qa_data = json.loads(qa_resp.data)
        qa_id = qa_data["data"]["qa_id"]

        # 员工回复
        answer_resp = api_post(
            f"/api/user/qa/{qa_id}/answer",
            token=admin_token,
            json_data={
                "content": "一般情况下48小时内发货。"
            }
        )
        assert answer_resp.status_code == 200
        answer_data = json.loads(answer_resp.data)
        assert answer_data["success"] == True

    def test_followup_question(self, client, user_token, test_product_id):
        """追问"""
        # 先提交问题并获取回复
        qa_resp = api_post(
            f"/api/user/qa",
            token=user_token,
            json_data={
                "product_id": test_product_id,
                "content": "请问有货吗？"
            }
        )
        qa_data = json.loads(qa_resp.data)
        qa_id = qa_data["data"]["qa_id"]

        # 员工回复
        api_post(
            f"/api/user/qa/{qa_id}/answer",
            token=admin_token,
            json_data={"content": "有货的"}
        )

        # 追问
        followup_resp = api_post(
            f"/api/user/qa/{qa_id}/followup",
            token=user_token,
            json_data={
                "content": "能发顺丰吗？"
            }
        )
        assert followup_resp.status_code == 200
        followup_data = json.loads(followup_resp.data)
        assert followup_data["success"] == True

    def test_close_question(self, client, user_token, test_product_id):
        """关闭问题"""
        # 提交问题
        qa_resp = api_post(
            f"/api/user/qa",
            token=user_token,
            json_data={
                "product_id": test_product_id,
                "content": "已解决，谢谢"
            }
        )
        qa_data = json.loads(qa_resp.data)
        qa_id = qa_data["data"]["qa_id"]

        # 关闭问题
        close_resp = api_post(
            f"/api/user/qa/{qa_id}/close",
            token=user_token
        )
        assert close_resp.status_code == 200
        close_data = json.loads(close_resp.data)
        assert close_data["success"] == True

    def test_get_qa_detail(self, client, test_product_id):
        """获取问答详情"""
        # 先提交一个问题
        qa_resp = api_post(
            f"/api/user/qa",
            token=user_token,
            json_data={
                "product_id": test_product_id,
                "content": "测试详情的问题"
            }
        )
        qa_data = json.loads(qa_resp.data)
        qa_id = qa_data["data"]["qa_id"]

        # 获取详情
        detail_resp = api_get(f"/api/user/qa/{qa_id}")
        assert detail_resp.status_code == 200
        detail_data = json.loads(detail_resp.data)
        assert detail_data["success"] == True
        assert detail_data["data"]["id"] == qa_id


# ============ V42.0 秒杀倒计时测试 ============

class TestSeckillCountdown:
    """秒杀倒计时测试"""

    def test_get_countdown(self, client):
        """获取秒杀倒计时"""
        resp = api_get("/api/user/seckill/countdown")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        countdown = data["data"]
        assert "status" in countdown
        assert countdown["status"] in ["waiting", "ongoing", "ended"]

    def test_countdown_structure(self, client):
        """秒杀倒计时数据结构"""
        resp = api_get("/api/user/seckill/countdown")
        data = json.loads(resp.data)
        countdown = data["data"]

        # 验证状态字段
        assert "status" in countdown
        # ongoing状态应该有结束时间
        if countdown["status"] == "ongoing":
            assert "end_time" in countdown
        # waiting状态应该有开始时间
        if countdown["status"] == "waiting":
            assert "start_time" in countdown


# ============ V42.0 会员数字卡测试 ============

class TestMemberCard:
    """会员数字卡测试"""

    def test_get_member_card(self, client, user_token):
        """获取会员数字卡信息"""
        resp = api_get("/api/user/member/card", token=user_token)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        card = data["data"]
        assert "member_number" in card
        assert "member_grade" in card

    def test_member_card_no_login(self, client):
        """会员数字卡 - 未登录"""
        resp = api_get("/api/user/member/card")
        # 应该返回错误或降级数据
        assert resp.status_code in [200, 401]

    def test_member_card_fields(self, client, user_token):
        """会员数字卡字段完整性"""
        resp = api_get("/api/user/member/card", token=user_token)
        data = json.loads(resp.data)
        card = data["data"]

        # 验证必要字段
        expected_fields = ["member_number", "member_grade", "points", "growth_value"]
        for field in expected_fields:
            assert field in card, f"缺少字段: {field}"


# ============ V42.0 追加评价测试 ============

class TestAppendReview:
    """追加评价测试"""

    def test_get_append_review_form(self, client, user_token, test_product_id):
        """获取追加评价表单"""
        resp = api_get(
            f"/api/user/reviews/append",
            token=user_token,
            params={"product_id": test_product_id}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        # 应该返回可追加的评价或空状态
        assert "can_append" in data["data"] or "items" in data["data"]

    def test_submit_append_review(self, client, user_token, test_product_id):
        """提交追加评价"""
        resp = api_post(
            f"/api/user/reviews/append",
            token=user_token,
            json_data={
                "product_id": test_product_id,
                "content": "使用了一段时间，感觉质量很好，推荐购买。"
            }
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        # 追加评价可能需要先有原始评价
        assert "success" in data

    def test_append_review_content_length(self, client, user_token, test_product_id):
        """追加评价内容长度验证"""
        resp = api_post(
            f"/api/user/reviews/append",
            token=user_token,
            json_data={
                "product_id": test_product_id,
                "content": "好"  # 太短
            }
        )
        data = json.loads(resp.data)
        # 应该被拒绝
        assert data["success"] == False or resp.status_code == 400


# ============ V42.0 积分商城测试 ============

class TestPointsMall:
    """积分商城测试"""

    def test_get_points_mall_list(self, client):
        """获取积分商品列表"""
        resp = api_get("/api/user/points-mall")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        assert "items" in data["data"]
        assert "total" in data["data"]

    def test_get_points_mall_detail(self, client):
        """获取积分商品详情"""
        # 先获取列表
        list_resp = api_get("/api/user/points-mall")
        list_data = json.loads(list_resp.data)
        items = list_data["data"]["items"]

        if len(items) > 0:
            product_id = items[0]["id"]
            detail_resp = api_get(f"/api/user/points-mall/{product_id}")
            assert detail_resp.status_code == 200
            detail_data = json.loads(detail_resp.data)
            assert detail_data["success"] == True

    def test_points_exchange(self, client, user_token):
        """积分兑换"""
        # 获取商品
        list_resp = api_get("/api/user/points-mall")
        list_data = json.loads(list_resp.data)
        items = list_data["data"]["items"]

        if len(items) > 0:
            product_id = items[0]["id"]

            resp = api_post(
                f"/api/user/points-mall/exchange",
                token=user_token,
                json_data={
                    "product_id": product_id,
                    "quantity": 1,
                    "address_id": 1
                }
            )
            assert resp.status_code == 200
            data = json.loads(resp.data)
            # 可能因积分不足失败，但不是服务器错误
            assert "success" in data

    def test_points_exchange_records(self, client, user_token):
        """获取兑换记录"""
        resp = api_get("/api/user/points-mall/exchanges", token=user_token)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        assert "items" in data["data"]


# ============ V42.0 商品评价增强测试 ============

class TestReviewEnhancement:
    """评价增强功能测试"""

    def test_get_reviews_with_stats(self, client, test_product_id):
        """获取评价及统计"""
        resp = api_get(
            f"/api/reviews",
            params={
                "target_type": "product",
                "target_id": test_product_id
            }
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "avg_rating" in data["data"]

    def test_get_product_reviews(self, client, test_product_id):
        """获取商品专属评价列表"""
        resp = api_get(f"/api/user/products/{test_product_id}/reviews")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] == True
        assert "items" in data["data"]


# ============ V42.0 集成测试 ============

class TestV42Integration:
    """V42.0集成测试"""

    def test_full_product_lifecycle(self, client, user_token, admin_token, test_product_id):
        """完整商品生命周期测试"""
        # 1. 添加规格
        spec_resp = admin_api_post(
            f"/api/admin/products/{test_product_id}/specs",
            token=admin_token,
            json_data={
                "spec_name": "测试规格",
                "values": ["A", "B"]
            }
        )
        assert json.loads(spec_resp.data)["success"] == True

        # 2. 提问
        qa_resp = api_post(
            f"/api/user/qa",
            token=user_token,
            json_data={
                "product_id": test_product_id,
                "content": "这个商品规格怎么选择？"
            }
        )
        qa_data = json.loads(qa_resp.data)
        assert qa_data["success"] == True
        qa_id = qa_data["data"]["qa_id"]

        # 3. 回复
        answer_resp = api_post(
            f"/api/user/qa/{qa_id}/answer",
            token=admin_token,
            json_data={"content": "请根据您的需求选择。"}
        )
        assert json.loads(answer_resp.data)["success"] == True

        # 4. 追问
        followup_resp = api_post(
            f"/api/user/qa/{qa_id}/followup",
            token=user_token,
            json_data={"content": "A和B有什么区别？"}
        )
        assert json.loads(followup_resp.data)["success"] == True

        # 5. 获取SKU矩阵
        matrix_resp = api_get(f"/api/user/products/{test_product_id}/sku/matrix")
        matrix_data = json.loads(matrix_resp.data)
        assert matrix_data["success"] == True

    def test_concurrent_qa_access(self, client, user_token, test_product_id):
        """并发问答访问测试"""
        # 同时发送多个请求
        import concurrent.futures

        def submit_question():
            return api_post(
                f"/api/user/qa",
                token=user_token,
                json_data={
                    "product_id": test_product_id,
                    "content": f"并发问题_{int(time.time() * 1000)}"
                }
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(submit_question) for _ in range(3)]
            results = [json.loads(f.result().data) for f in futures]

        # 所有请求应该成功
        assert all(r["success"] for r in results)


# ============ 运行入口 ============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
