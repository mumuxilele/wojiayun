"""
Flask API文档生成器 - 自动生成Swagger/OpenAPI文档
"""
import json

def generate_swagger_spec(title="社区商业服务系统API", version="1.0.0", description=""):
    """生成Swagger/OpenAPI规范文档"""
    
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": title,
            "version": version,
            "description": description or "社区商业服务系统 API 文档"
        },
        "servers": [
            {"url": "http://127.0.0.1:22311", "description": "用户端H5服务"},
            {"url": "http://127.0.0.1:22312", "description": "员工端H5服务"},
            {"url": "http://127.0.0.1:22313", "description": "管理端Web服务"}
        ],
        "paths": {},
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "在URL中传递access_token参数"
                }
            },
            "schemas": {
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": False},
                        "msg": {"type": "string", "example": "请先登录"}
                    }
                },
                "SuccessResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": True},
                        "data": {"type": "object"}
                    }
                }
            }
        }
    }
    
    # 用户端API
    user_paths = {
        # 统计
        "/api/user/stats": {
            "get": {
                "summary": "获取用户统计信息",
                "tags": ["用户-统计"],
                "parameters": [
                    {"name": "access_token", "in": "query", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {"200": {"description": "成功", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SuccessResponse"}}}}}
            }
        },
        # 申请单
        "/api/user/applications": {
            "get": {
                "summary": "获取用户申请单列表",
                "tags": ["用户-申请单"],
                "parameters": [
                    {"name": "access_token", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                    {"name": "page_size", "in": "query", "schema": {"type": "integer", "default": 20}},
                    {"name": "status", "in": "query", "schema": {"type": "string"}}
                ],
                "responses": {"200": {"description": "成功"}}
            },
            "post": {
                "summary": "创建申请单",
                "tags": ["用户-申请单"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "app_type": {"type": "string", "description": "申请类型"},
                                    "title": {"type": "string", "description": "标题"},
                                    "content": {"type": "string", "description": "内容"},
                                    "priority": {"type": "integer", "description": "优先级"}
                                },
                                "required": ["app_type", "title"]
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "成功"}}
            }
        },
        # 订单
        "/api/user/orders": {
            "get": {
                "summary": "获取用户订单列表",
                "tags": ["用户-订单"],
                "responses": {"200": {"description": "成功"}}
            },
            "post": {
                "summary": "创建订单",
                "tags": ["用户-订单"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "order_type": {"type": "string", "default": "product"},
                                    "items": {"type": "array", "items": {"type": "object"}},
                                    "cart_ids": {"type": "array", "items": {"type": "integer"}},
                                    "coupon_code": {"type": "string"},
                                    "remark": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "成功"}}
            }
        },
        # 购物车
        "/api/user/cart": {
            "get": {
                "summary": "获取购物车列表",
                "tags": ["用户-购物车"],
                "responses": {"200": {"description": "成功"}}
            },
            "post": {
                "summary": "添加商品到购物车",
                "tags": ["用户-购物车"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "product_id": {"type": "integer"},
                                    "sku_id": {"type": "integer", "description": "SKU规格ID"},
                                    "quantity": {"type": "integer", "default": 1}
                                },
                                "required": ["product_id"]
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "成功"}}
            }
        },
        # 收货地址
        "/api/user/addresses": {
            "get": {
                "summary": "获取收货地址列表",
                "tags": ["用户-地址管理"],
                "responses": {"200": {"description": "成功"}}
            },
            "post": {
                "summary": "新增收货地址",
                "tags": ["用户-地址管理"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "user_name": {"type": "string"},
                                    "phone": {"type": "string"},
                                    "province": {"type": "string"},
                                    "city": {"type": "string"},
                                    "area": {"type": "string"},
                                    "address": {"type": "string"},
                                    "is_default": {"type": "integer", "default": 0},
                                    "tag": {"type": "string"}
                                },
                                "required": ["user_name", "phone", "address"]
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "成功"}}
            }
        },
        # 优惠券
        "/api/user/coupons": {
            "get": {
                "summary": "获取我的优惠券",
                "tags": ["用户-优惠券"],
                "parameters": [
                    {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["unused", "used", "expired"]}}
                ],
                "responses": {"200": {"description": "成功"}}
            }
        },
        # 收藏
        "/api/user/favorites": {
            "get": {
                "summary": "获取我的收藏",
                "tags": ["用户-收藏"],
                "responses": {"200": {"description": "成功"}}
            }
        },
        # 评价
        "/api/reviews": {
            "get": {
                "summary": "获取评价列表（公开）",
                "tags": ["用户-评价"],
                "parameters": [
                    {"name": "target_type", "in": "query", "schema": {"type": "string", "enum": ["venue", "shop", "product"]}},
                    {"name": "target_id", "in": "query", "schema": {"type": "integer"}}
                ],
                "responses": {"200": {"description": "成功"}}
            }
        },
        # 公告
        "/api/notices": {
            "get": {
                "summary": "获取公告列表",
                "tags": ["用户-公告"],
                "responses": {"200": {"description": "成功"}}
            }
        },
        # 通知
        "/api/user/notifications": {
            "get": {
                "summary": "获取通知列表",
                "tags": ["用户-通知"],
                "responses": {"200": {"description": "成功"}}
            }
        }
    }
    
    # 管理端API
    admin_paths = {
        "/api/admin/statistics": {
            "get": {
                "summary": "管理端统计概览",
                "tags": ["管理-统计"],
                "responses": {"200": {"description": "成功"}}
            }
        },
        "/api/admin/applications": {
            "get": {
                "summary": "申请单列表",
                "tags": ["管理-申请单"],
                "responses": {"200": {"description": "成功"}}
            }
        },
        "/api/admin/orders": {
            "get": {
                "summary": "订单列表",
                "tags": ["管理-订单"],
                "responses": {"200": {"description": "成功"}}
            }
        },
        "/api/admin/shops": {
            "get": {
                "summary": "门店列表",
                "tags": ["管理-门店"],
                "responses": {"200": {"description": "成功"}}
            }
        },
        "/api/admin/products": {
            "get": {
                "summary": "商品列表",
                "tags": ["管理-商品"],
                "responses": {"200": {"description": "成功"}}
            },
            "post": {
                "summary": "创建商品",
                "tags": ["管理-商品"],
                "responses": {"200": {"description": "成功"}}
            }
        },
        "/api/admin/venues": {
            "get": {
                "summary": "场地列表",
                "tags": ["管理-场地"],
                "responses": {"200": {"description": "成功"}}
            }
        },
        "/api/admin/coupons": {
            "get": {
                "summary": "优惠券列表",
                "tags": ["管理-优惠券"],
                "responses": {"200": {"description": "成功"}}
            },
            "post": {
                "summary": "创建优惠券",
                "tags": ["管理-优惠券"],
                "responses": {"200": {"description": "成功"}}
            }
        },
        "/api/admin/notices": {
            "get": {
                "summary": "公告管理列表",
                "tags": ["管理-公告"],
                "responses": {"200": {"description": "成功"}}
            },
            "post": {
                "summary": "创建公告",
                "tags": ["管理-公告"],
                "responses": {"200": {"description": "成功"}}
            }
        },
        "/api/admin/points/members": {
            "get": {
                "summary": "会员积分列表",
                "tags": ["管理-积分"],
                "responses": {"200": {"description": "成功"}}
            }
        }
    }
    
    # 合并所有路径
    spec["paths"].update(user_paths)
    spec["paths"].update(admin_paths)
    
    return spec


def generate_swagger_html():
    """生成Swagger UI HTML页面"""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API文档 - 社区商业服务系统</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css">
    <style>
        body { margin: 0; padding: 0; }
        .topbar { display: none; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
    <script>
        const spec = ''' + json.dumps(generate_swagger_spec()) + ''';
        window.onload = function() {
            const ui = SwaggerUIBundle({
                spec: spec,
                dom_id: "#swagger-ui",
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "StandaloneLayout",
                "syntaxHighlight.theme": "monokai",
                "showExtensions": true,
                "showCommonExtensions": true
            });
            window.ui = ui;
        };
    </script>
</body>
</html>'''


if __name__ == '__main__':
    # 生成JSON规范文件
    spec = generate_swagger_spec()
    print(json.dumps(spec, indent=2, ensure_ascii=False))
