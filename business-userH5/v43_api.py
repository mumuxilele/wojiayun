"""
V43.0 API端点扩展 - 用户端
添加订单追踪、售后申请等接口
"""

from flask import jsonify
import logging

logger = logging.getLogger(__name__)


def register_v43_apis(app, require_login, get_current_user):
    """
    注册V43.0 API端点
    
    Args:
        app: Flask应用实例
        require_login: 登录验证装饰器
        get_current_user: 获取当前用户函数
    """
    
    # ============ 订单追踪接口 ============
    
    @app.route('/api/user/orders/<int:order_id>/tracking', methods=['GET'])
    @require_login
    def get_order_tracking(user, order_id):
        """获取订单物流追踪信息"""
        from business_common.order_tracking_service import order_tracking
        
        # 验证订单归属
        from business_common import db
        order = db.get_one(
            "SELECT id FROM business_orders WHERE id=%s AND user_id=%s",
            [order_id, user['user_id']]
        )
        if not order:
            return jsonify({'success': False, 'msg': '订单不存在'})
        
        result = order_tracking.get_tracking_info(order_id)
        return jsonify(result)
    
    @app.route('/api/user/orders/<int:order_id>/tracking/sync', methods=['POST'])
    @require_login
    def sync_order_tracking(user, order_id):
        """同步订单物流信息"""
        from business_common.order_tracking_service import order_tracking
        
        # 验证订单归属
        from business_common import db
        order = db.get_one(
            "SELECT id FROM business_orders WHERE id=%s AND user_id=%s",
            [order_id, user['user_id']]
        )
        if not order:
            return jsonify({'success': False, 'msg': '订单不存在'})
        
        result = order_tracking.sync_tracking(order_id=order_id)
        return jsonify(result)
    
    @app.route('/api/user/orders/<int:order_id>/confirm', methods=['POST'])
    @require_login
    def confirm_order_receive(user, order_id):
        """确认收货"""
        from business_common.order_tracking_service import order_tracking
        from business_common import db
        
        # 验证订单归属和状态
        order = db.get_one(
            "SELECT id, order_status FROM business_orders WHERE id=%s AND user_id=%s",
            [order_id, user['user_id']]
        )
        if not order:
            return jsonify({'success': False, 'msg': '订单不存在'})
        
        if order['order_status'] not in ['shipped', 'delivery']:
            return jsonify({'success': False, 'msg': '订单状态不可确认收货'})
        
        try:
            # 更新订单状态
            db.execute(
                "UPDATE business_orders SET order_status='completed', updated_at=NOW() WHERE id=%s",
                [order_id]
            )
            
            # 更新追踪记录
            db.execute("""
                UPDATE business_order_tracking 
                SET confirmed_at=NOW(), current_status='completed'
                WHERE order_id=%s
            """, [order_id])
            
            # 记录事件
            order_tracking._log_event(order_id, 'confirmed', {
                'user_id': user['user_id'],
                'user_name': user.get('user_name')
            }, 'user', user['user_id'])
            
            return jsonify({'success': True, 'msg': '确认收货成功'})
            
        except Exception as e:
            logger.error(f"确认收货失败: {e}")
            return jsonify({'success': False, 'msg': str(e)})
    
    # ============ 售后接口 ============
    
    @app.route('/api/user/aftersales', methods=['GET'])
    @require_login
    def get_user_aftersales_list(user):
        """获取用户售后列表"""
        from business_common.aftersales_service import aftersales_service
        from flask import request
        
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 10)), 50)
        
        result = aftersales_service.get_user_aftersales_list(
            user_id=user['user_id'],
            page=page,
            page_size=page_size
        )
        return jsonify(result)
    
    @app.route('/api/user/aftersales', methods=['POST'])
    @require_login
    def create_aftersales_apply(user):
        """提交售后申请"""
        from business_common.aftersales_service import aftersales_service
        from flask import request
        
        data = request.get_json() or {}
        
        # 参数校验
        required = ['order_id', 'type', 'reason_code', 'items']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'msg': f'缺少参数: {field}'})
        
        result = aftersales_service.apply_aftersales(
            user_id=user['user_id'],
            order_id=data['order_id'],
            apply_type=data['type'],
            reason_code=data['reason_code'],
            items=data['items'],
            refund_amount=data.get('refund_amount'),
            apply_desc=data.get('apply_desc', ''),
            images=data.get('images', []),
            ec_id=user.get('ec_id'),
            project_id=user.get('project_id')
        )
        return jsonify(result)
    
    @app.route('/api/user/aftersales/<int:aftersales_id>', methods=['GET'])
    @require_login
    def get_aftersales_detail(user, aftersales_id):
        """获取售后详情"""
        from business_common.aftersales_service import aftersales_service
        
        result = aftersales_service.get_aftersales_detail(
            aftersales_id=aftersales_id,
            user_id=user['user_id']
        )
        return jsonify(result)
    
    @app.route('/api/user/aftersales/<int:aftersales_id>/return', methods=['POST'])
    @require_login
    def submit_return_logistics(user, aftersales_id):
        """提交退货物流信息"""
        from business_common.aftersales_service import aftersales_service
        from flask import request
        
        data = request.get_json() or {}
        
        if not data.get('tracking_no') or not data.get('carrier_name'):
            return jsonify({'success': False, 'msg': '请填写物流信息'})
        
        result = aftersales_service.submit_return(
            aftersales_id=aftersales_id,
            user_id=user['user_id'],
            tracking_no=data['tracking_no'],
            carrier_name=data['carrier_name']
        )
        return jsonify(result)
    
    @app.route('/api/user/aftersales/reasons', methods=['GET'])
    @require_login
    def get_aftersales_reasons(user):
        """获取售后原因列表"""
        from business_common.aftersales_service import aftersales_service
        
        reasons = []
        for code, info in aftersales_service.REFUND_REASONS.items():
            reasons.append({
                'code': code,
                'name': info['name'],
                'type': info['type']
            })
        
        return jsonify({'success': True, 'data': reasons})
    
    # ============ 评价增强接口 ============
    
    @app.route('/api/user/reviews/<int:review_id>/append', methods=['POST'])
    @require_login
    def append_review(user, review_id):
        """追加评价"""
        from business_common import db
        from flask import request
        
        data = request.get_json() or {}
        content = data.get('content', '').strip()
        images = data.get('images', [])
        
        if not content:
            return jsonify({'success': False, 'msg': '请填写评价内容'})
        
        # 验证原评价
        review = db.get_one(
            "SELECT * FROM business_reviews WHERE id=%s AND user_id=%s",
            [review_id, user['user_id']]
        )
        if not review:
            return jsonify({'success': False, 'msg': '评价不存在'})
        
        try:
            # 创建追评
            db.execute("""
                INSERT INTO business_reviews 
                (order_id, product_id, user_id, rating, content, images, parent_id, is_append, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
            """, [
                review['order_id'], review['product_id'], user['user_id'],
                review['rating'], content, 
                json.dumps(images) if images else None,
                review_id,
                review.get('ec_id'), review.get('project_id')
            ])
            
            return jsonify({'success': True, 'msg': '追评成功'})
            
        except Exception as e:
            logger.error(f"追评失败: {e}")
            return jsonify({'success': False, 'msg': str(e)})
    
    @app.route('/api/user/reviews/<int:review_id>/helpful', methods=['POST'])
    @require_login
    def mark_review_helpful(user, review_id):
        """标记评价有用"""
        from business_common import db
        
        try:
            db.execute("""
                UPDATE business_reviews 
                SET helpful_count = helpful_count + 1
                WHERE id=%s
            """, [review_id])
            
            return jsonify({'success': True, 'msg': '已标记'})
            
        except Exception as e:
            logger.error(f"标记有用失败: {e}")
            return jsonify({'success': False, 'msg': str(e)})
    
    logger.info("V43.0 API端点注册完成")


# 兼容直接导入
def init_v43_apis(app, require_login, get_current_user):
    """初始化V43 API"""
    register_v43_apis(app, require_login, get_current_user)
