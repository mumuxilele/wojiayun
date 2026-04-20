#!/bin/bash
TOKEN='9f2e0ad4213dba711f73a17a6e538f5c7eb349613ba56d6e83aa0c7cf05b0556'
BASE='http://127.0.0.1:22313'

echo "=== 1. 测试页面加载 ==="
pages=("index.html" "data-board.html" "statistics.html" "member-levels.html" "members.html" "shops.html" "orders.html" "products.html" "coupons.html" "promotions.html" "group-buy.html" "applications.html" "refunds.html" "notices.html" "points-mall.html" "users.html")
for page in "${pages[@]}"; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/business-admin/$page")
    echo "$page: $STATUS"
done

echo ""
echo "=== 2. 测试核心 API ==="
apis=(
    "/api/admin/statistics/overview?access_token=$TOKEN&days=7"
    "/api/admin/statistics/trend?access_token=$TOKEN&days=7"
    "/api/admin/members?access_token=$TOKEN"
    "/api/admin/member-levels?access_token=$TOKEN"
    "/api/admin/shops?access_token=$TOKEN"
    "/api/admin/orders?access_token=$TOKEN"
    "/api/admin/products?access_token=$TOKEN"
    "/api/admin/coupons?access_token=$TOKEN"
    "/api/admin/promotions?access_token=$TOKEN"
    "/api/admin/group-buys?access_token=$TOKEN"
    "/api/admin/applications?access_token=$TOKEN"
    "/api/admin/refunds?access_token=$TOKEN"
    "/api/admin/notices?access_token=$TOKEN"
    "/api/admin/users?access_token=$TOKEN"
    "/api/admin/points-mall/goods?access_token=$TOKEN"
)
for api in "${apis[@]}"; do
    RESP=$(curl -s "$BASE$api")
    if echo "$RESP" | grep -q '"success":true'; then
        echo "✓ $api"
    elif echo "$RESP" | grep -q '"success":false'; then
        MSG=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('msg','')[:30])" 2>/dev/null)
        echo "✗ $api: $MSG"
    else
        echo "? $api: $RESP" | head -c 100
    fi
done

echo ""
echo "=== 3. PM2 服务状态 ==="
pm2 list | grep wojiayun
