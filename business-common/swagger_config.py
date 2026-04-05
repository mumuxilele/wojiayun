#!/usr/bin/env python3
"""
Swagger API文档配置 V21.0
提供交互式API文档支持
"""
from flask import Flask, jsonify
import os

# 尝试导入flasgger，如果未安装则使用简单的文档路由
try:
    from flasgger import Swagger, SwaggerView, swag_from
    HAS_FLASGGER = True
except ImportError:
    HAS_FLASGGER = False


# Swagger配置
SWAGGER_CONFIG = {
    'title': '社区商业系统 API',
    'version': '21.0.0',
    'description': '''
## 系统说明

社区商业服务系统，提供以下功能：

### 用户端 (端口 22311)
- 会员管理（积分、签到、等级）
- 商品浏览与购买
- 场馆预约
- 申请单提交
- 优惠券使用
- 秒杀活动参与

### 员工端 (端口 22312)
- 申请单处理
- 订单管理
- 预约核销
- 数据统计

### 管理端 (端口 22313)
- 全局数据管理
- 营销活动配置
- 统计报表

---

## 认证方式

所有API通过 `access_token` 参数或 `Token` 请求头传递用户凭证。

示例：
```
GET /api/user/profile?access_token=xxx
POST /api/orders (Header: Token: xxx)
```

---

## 响应格式

```json
{
    "success": true,
    "data": {...},
    "msg": "操作成功"
}
```

错误响应：
```json
{
    "success": false,
    "msg": "错误描述",
    "code": 401
}
```
''',
    'termsOfService': '',
    'contact': {
        'name': '技术支持',
        'email': 'support@example.com'
    },
    'license': {
        'name': '私有软件'
    },
    'specs_route': '/api/docs/',
    'specs_json_route': '/api/docs.json',
    'swagger_ui': True,
    'apisitivity': False,
}


def init_swagger(app: Flask):
    """
    初始化Swagger文档
    
    Args:
        app: Flask应用实例
    """
    if HAS_FLASGGER:
        Swagger(app, config=SWAGGER_CONFIG)
        
        # 添加自定义静态资源路径
        static_folder = app.static_folder or 'static'
        if os.path.exists(static_folder):
            app.logger.info("Swagger UI已启用，访问 /api/docs/ 查看交互式文档")
    else:
        # 提供简化版文档路由
        @app.route('/api/docs/')
        def api_docs():
            """API文档"""
            return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>API文档</title>
    <style>
        body { font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; }
        h1 { color: #333; border-bottom: 2px solid #1890ff; padding-bottom: 10px; }
        h2 { color: #666; margin-top: 30px; }
        .endpoint { background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 10px 0; }
        .method { display: inline-block; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
        .get { background: #61affe; color: white; }
        .post { background: #49cc90; color: white; }
        .put { background: #fca130; color: white; }
        .delete { background: #f93e3e; color: white; }
        .path { font-family: monospace; color: #333; }
        code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }
        pre { background: #272822; color: #f8f8f2; padding: 15px; border-radius: 8px; overflow-x: auto; }
        .note { background: #fffbe6; border-left: 4px solid #faad14; padding: 10px; margin: 15px 0; }
        .install { background: #f6ffed; border-left: 4px solid #52c41a; padding: 10px; margin: 15px 0; }
    </style>
</head>
<body>
    <h1>📚 社区商业系统 API 文档</h1>
    
    <div class="note">
        <strong>提示：</strong>本系统使用简化版文档。如需交互式Swagger UI，请安装 flasgger：
        <code>pip install flasgger</code>，然后重启服务。
    </div>
    
    <h2>📌 基础信息</h2>
    <div class="endpoint">
        <p><strong>版本：</strong>V21.0</p>
        <p><strong>认证：</strong>通过 <code>access_token</code> 参数或 <code>Token</code> 请求头</p>
    </div>
    
    <h2>👤 用户端 API (端口 22311)</h2>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/user/stats</span>
        <p>获取用户统计信息</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/user/profile</span>
        <p>获取个人中心信息</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/user/orders</span>
        <p>获取订单列表（支持分页、状态筛选）</p>
    </div>
    
    <div class="endpoint">
        <span class="method post">POST</span>
        <span class="path">/api/user/orders</span>
        <p>创建商品订单</p>
        <pre>{
    "items": [{"product_id": 1, "quantity": 1}],
    "coupon_code": "COUPON123",
    "address_id": 1
}</pre>
    </div>
    
    <div class="endpoint">
        <span class="method post">POST</span>
        <span class="path">/api/user/orders/{id}/refund</span>
        <p>申请退款</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/user/bookings</span>
        <p>获取场地预约列表</p>
    </div>
    
    <div class="endpoint">
        <span class="method post">POST</span>
        <span class="path">/api/user/checkin</span>
        <p>每日签到</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/user/coupons</span>
        <p>获取我的优惠券</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/user/favorites</span>
        <p>获取我的收藏</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/seckill/activity</span>
        <p>获取当前秒杀活动</p>
    </div>
    
    <div class="endpoint">
        <span class="method post">POST</span>
        <span class="path">/api/seckill/orders</span>
        <p>创建秒杀订单</p>
        <pre>{
    "activity_id": 1,
    "quantity": 1,
    "address_id": 1
}</pre>
    </div>
    
    <div class="endpoint">
        <span class="method post">POST</span>
        <span class="path">/api/user/reviews</span>
        <p>提交评价</p>
        <pre>{
    "target_type": "order",
    "target_id": 123,
    "rating": 5,
    "content": "服务很好！"
}</pre>
    </div>
    
    <h2>👔 员工端 API (端口 22312)</h2>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/staff/applications</span>
        <p>获取申请单列表</p>
    </div>
    
    <div class="endpoint">
        <span class="method put">PUT</span>
        <span class="path">/api/staff/applications/{id}</span>
        <p>处理申请单</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/staff/orders</span>
        <p>获取订单列表</p>
    </div>
    
    <div class="endpoint">
        <span class="method post">POST</span>
        <span class="path">/api/staff/orders/{id}/ship</span>
        <p>发货</p>
    </div>
    
    <div class="endpoint">
        <span class="method post">POST</span>
        <span class="path">/api/staff/bookings/{id}/verify</span>
        <p>核销预约</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/staff/statistics</span>
        <p>获取统计数据</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/staff/reviews</span>
        <p>获取评价列表</p>
    </div>
    
    <h2>⚙️ 管理端 API (端口 22313)</h2>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/admin/statistics</span>
        <p>获取管理统计概览</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/admin/promotions</span>
        <p>获取营销活动列表</p>
    </div>
    
    <div class="endpoint">
        <span class="method post">POST</span>
        <span class="path">/api/admin/promotions</span>
        <p>创建营销活动</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/admin/reviews</span>
        <p>获取评价列表</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/admin/seckill/{id}/orders</span>
        <p>获取秒杀订单</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/health/detailed</span>
        <p>详细健康检查（无需认证）</p>
    </div>
    
    <h2>📋 公共接口</h2>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/products</span>
        <p>获取商品列表（支持搜索、分类、排序）</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/shops</span>
        <p>获取门店列表</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/venues</span>
        <p>获取场馆列表</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="path">/api/announcements</span>
        <p>获取公告列表</p>
    </div>
    
    <h2>🔗 相关链接</h2>
    <ul>
        <li>用户端地址：<code>http://localhost:22311/</code></li>
        <li>员工端地址：<code>http://localhost:22312/</code></li>
        <li>管理端地址：<code>http://localhost:22313/</code></li>
    </ul>
    
    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #999;">
        <p>Generated by WorkBuddy AI · V21.0</p>
    </footer>
</body>
</html>
            '''
        
        @app.route('/api/docs.json')
        def api_docs_json():
            """获取OpenAPI JSON格式的文档"""
            return jsonify({
                'openapi': '3.0.0',
                'info': {
                    'title': '社区商业系统 API',
                    'version': '21.0.0',
                    'description': '完整的API文档请访问 /api/docs/'
                },
                'paths': {}  # 完整路径定义可扩展
            })
        
        app.logger.info("简化版API文档已启用，访问 /api/docs/ 查看")


def get_swagger_params():
    """
    获取Swagger通用参数定义
    
    Returns:
        常用参数定义字典
    """
    return {
        'access_token': {
            'name': 'access_token',
            'in': 'query',
            'description': '用户访问令牌',
            'required': False,
            'schema': {'type': 'string'}
        },
        'page': {
            'name': 'page',
            'in': 'query',
            'description': '页码（默认1）',
            'required': False,
            'schema': {'type': 'integer', 'default': 1}
        },
        'page_size': {
            'name': 'page_size',
            'in': 'query',
            'description': '每页数量（默认20，最大50）',
            'required': False,
            'schema': {'type': 'integer', 'default': 20}
        }
    }
