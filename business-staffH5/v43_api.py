"""
V43.0 API端点扩展 - 员工端
添加售后处理、物流确认等接口
"""

from flask import jsonify
import logging

logger = logging.getLogger(__name__)


def register_v43_apis(app, require_staff, get_current_staff):
    """
    注册V43.0 API端点
    
    Args:
        app: Flask应用实例
        require_staff: 员工验证装饰器
        get_current_staff: 获取当前员工函数
    """
    
    # ============ 售后处理接口 ============
    
    @app.route('/api/staff/aftersales', methods=['GET'])
    @require_staff
    def get_staff_aftersales_list(staff):
        """获取售后列表"""
        from business_common.aftersales_service import aftersales_service
        from business_common import db
        from flask import request
        
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 20)), 50)
        status = request.args.get('status')
        
        ec_id = staff.get('ec_id')
        project_id = staff.get('project_id')
        
        # 构建查询
        where = "1=1"
        params = []
        
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        if status:
            where += " AND status=%s"
            params.append(status)
        
        total = db.get_total(
            f"SELECT COUNT(*) FROM business_aftersales WHERE {where}",
            params.copy()
        )
        
        offset = (page - 1) * page_size
        items = db.get_all(f"""
            SELECT a.*, o.product_name as order_product_name,
                   u.user_name as applicant_name, u.phone as applicant_phone
            FROM business_aftersales a
            LEFT JOIN business_orders o ON a.order_id = o.id
            LEFT JOIN business_members u ON a.user_id = u.user_id
            WHERE {where}
            ORDER BY a.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])
        
        result = []
        for item in items:
            result.append({
                'aftersales_id': item['id'],
                'aftersales_no': item['aftersales_no'],
                'type': item['type'],
                'type_name': aftersales_service._get_type_name(item['type']),
                'status': item['status'],
                'status_name': aftersales_service._get_status_name(item['status']),
                'refund_amount': float(item['refund_amount']) if item['refund_amount'] else 0,
                'applicant_name': item['applicant_name'],
                'applicant_phone': item['applicant_phone'],
                'reason_desc': item['reason_desc'],
                'created_at': str(item['created_at']),
            })
        
        return jsonify({
            'success': True,
            'data': {
                'items': result,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        })
    
    @app.route('/api/staff/aftersales/<int:aftersales_id>', methods=['GET'])
    @require_staff
    def get_staff_aftersales_detail(staff, aftersales_id):
        """获取售后详情"""
        from business_common.aftersales_service import aftersales_service
        from business_common import db
        
        ec_id = staff.get('ec_id')
        project_id = staff.get('project_id')
        
        # 检查权限
        aftersales = db.get_one(
            "SELECT ec_id, project_id FROM business_aftersales WHERE id=%s",
            [aftersales_id]
        )
        if not aftersales:
            return jsonify({'success': False, 'msg': '售后单不存在'})
        
        if ec_id and aftersales.get('ec_id') != ec_id:
            return jsonify({'success': False, 'msg': '无权查看'})
        if project_id and aftersales.get('project_id') != project_id:
            return jsonify({'success': False, 'msg': '无权查看'})
        
        result = aftersales_service.get_aftersales_detail(aftersales_id)
        return jsonify(result)
    
    @app.route('/api/staff/aftersales/<int:aftersales_id>/handle', methods=['POST'])
    @require_staff
    def handle_aftersales_apply(staff, aftersales_id):
        """处理售后申请"""
        from business_common.aftersales_service import aftersales_service
        from flask import request
        
        data = request.get_json() or {}
        action = data.get('action')  # approve/reject
        remark = data.get('remark', '')
        return_address = data.get('return_address', '')
        
        if action not in ['approve', 'reject']:
            return jsonify({'success': False, 'msg': '无效的操作'})
        
        result = aftersales_service.handle_apply(
            aftersales_id=aftersales_id,
            action=action,
            handler_id=staff.get('user_id'),
            handler_name=staff.get('user_name'),
            remark=remark,
            return_address=return_address
        )
        return jsonify(result)
    
    @app.route('/api/staff/aftersales/<int:aftersales_id>/receive', methods=['POST'])
    @require_staff
    def confirm_aftersales_receive(staff, aftersales_id):
        """确认收货"""
        from business_common.aftersales_service import aftersales_service
        
        result = aftersales_service.confirm_receive(
            aftersales_id=aftersales_id,
            staff_id=staff.get('user_id'),
            staff_name=staff.get('user_name')
        )
        return jsonify(result)
    
    @app.route('/api/staff/aftersales/<int:aftersales_id>/complete', methods=['POST'])
    @require_staff
    def complete_aftersales_order(staff, aftersales_id):
        """完成售后"""
        from business_common.aftersales_service import aftersales_service
        
        result = aftersales_service.complete_aftersales(
            aftersales_id=aftersales_id,
            staff_id=staff.get('user_id'),
            staff_name=staff.get('user_name')
        )
        return jsonify(result)
    
    @app.route('/api/staff/aftersales/stats', methods=['GET'])
    @require_staff
    def get_aftersales_stats(staff):
        """获取售后统计"""
        from business_common.aftersales_service import aftersales_service
        from flask import request
        
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        result = aftersales_service.get_aftersales_stats(
            ec_id=staff.get('ec_id'),
            project_id=staff.get('project_id'),
            date_from=date_from,
            date_to=date_to
        )
        return jsonify(result)
    
    # ============ 订单发货接口 ============
    
    @app.route('/api/staff/orders/<int:order_id>/ship', methods=['POST'])
    @require_staff
    def staff_ship_order(staff, order_id):
        """订单发货"""
        from business_common.order_tracking_service import order_tracking
        from business_common import db
        from flask import request
        
        data = request.get_json() or {}
        tracking_no = data.get('tracking_no')
        carrier_code = data.get('carrier_code')
        carrier_name = data.get('carrier_name')
        
        if not tracking_no or not carrier_name:
            return jsonify({'success': False, 'msg': '请填写物流信息'})
        
        ec_id = staff.get('ec_id')
        project_id = staff.get('project_id')
        
        # 检查订单权限
        order = db.get_one(
            "SELECT id, order_no, order_status FROM business_orders WHERE id=%s",
            [order_id]
        )
        if not order:
            return jsonify({'success': False, 'msg': '订单不存在'})
        
        if order['order_status'] != 'paid':
            return jsonify({'success': False, 'msg': '订单状态不可发货'})
        
        try:
            # 更新订单状态
            db.execute("""
                UPDATE business_orders 
                SET order_status='shipped', tracking_no=%s, carrier_name=%s, 
                    shipped_at=NOW(), updated_at=NOW()
                WHERE id=%s
            """, [tracking_no, carrier_name, order_id])
            
            # 创建或更新追踪记录
            tracking = db.get_one(
                "SELECT id FROM business_order_tracking WHERE order_id=%s",
                [order_id]
            )
            if tracking:
                order_tracking.update_shipment(order_id, tracking_no, carrier_code, carrier_name)
            else:
                order_tracking.create_tracking(order_id, order['order_no'])
                order_tracking.update_shipment(order_id, tracking_no, carrier_code, carrier_name)
            
            return jsonify({'success': True, 'msg': '发货成功'})
            
        except Exception as e:
            logger.error(f"发货失败: {e}")
            return jsonify({'success': False, 'msg': str(e)})
    
    logger.info("V43.0 员工端API端点注册完成")
