#!/usr/bin/env python3
"""
批量操作服务模块 V28.0
功能:
  - 批量订单发货
  - 批量处理申请单
  - 批量退款处理
  - 批量操作日志记录
"""
import json
import logging
import uuid
from datetime import datetime
from . import db

logger = logging.getLogger(__name__)


class BatchOperationService:
    """批量操作服务"""

    @staticmethod
    def batch_ship_orders(operator_id, operator_name, order_ids, 
                          logistics_company='', ec_id=None, project_id=None):
        """
        批量订单发货

        Args:
            operator_id: 操作人ID
            operator_name: 操作人姓名
            order_ids: 订单ID列表
            logistics_company: 物流公司
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: 批量操作结果
        """
        if not order_ids or len(order_ids) == 0:
            return {'success': False, 'msg': '请选择要发货的订单'}

        batch_no = f"BATCH-SHIP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        success_count = 0
        fail_count = 0
        fail_details = []

        try:
            conn = db.get_db()
            cursor = conn.cursor()
            conn.begin()

            for order_id in order_ids:
                try:
                    # 构建查询条件
                    where = "id=%s AND deleted=0 AND order_status='paid'"
                    params = [order_id]

                    if ec_id:
                        where += " AND ec_id=%s"
                        params.append(ec_id)
                    if project_id:
                        where += " AND project_id=%s"
                        params.append(project_id)

                    cursor.execute(f"SELECT * FROM business_orders WHERE {where}", params)
                    order = cursor.fetchone()

                    if not order:
                        fail_count += 1
                        fail_details.append({
                            'order_id': order_id,
                            'reason': '订单不存在或状态不允许发货'
                        })
                        continue

                    # 更新订单状态
                    cursor.execute(
                        """UPDATE business_orders 
                           SET order_status='shipped', tracking_no='',
                               logistics_company=%s, shipped_at=NOW(), updated_at=NOW()
                           WHERE id=%s""",
                        [logistics_company, order_id]
                    )
                    success_count += 1

                except Exception as e:
                    fail_count += 1
                    fail_details.append({
                        'order_id': order_id,
                        'reason': str(e)
                    })
                    logger.error(f"批量发货订单{order_id}失败: {e}")

            # 记录批量操作日志
            cursor.execute(
                """INSERT INTO business_batch_operations
                   (batch_no, operation_type, target_type, total_count, success_count, fail_count,
                    fail_details, operator_id, operator_name, ec_id, project_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                [batch_no, 'batch_ship', 'order', len(order_ids), success_count,
                 fail_count, json.dumps(fail_details, ensure_ascii=False),
                 operator_id, operator_name, ec_id, project_id]
            )

            conn.commit()

            return {
                'success': True,
                'msg': f'批量发货完成：成功{success_count}个，失败{fail_count}个',
                'data': {
                    'batch_no': batch_no,
                    'total': len(order_ids),
                    'success': success_count,
                    'fail': fail_count,
                    'fail_details': fail_details
                }
            }

        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            logger.error(f"批量发货失败: {e}")
            return {'success': False, 'msg': f'批量发货失败: {str(e)}'}

        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

    @staticmethod
    def batch_process_applications(operator_id, operator_name, app_ids, action,
                                    ec_id=None, project_id=None):
        """
        批量处理申请单

        Args:
            operator_id: 操作人ID
            operator_name: 操作人姓名
            app_ids: 申请单ID列表
            action: 操作类型 (approve/reject/assign)
            ec_id: 企业ID
            project_id: 项目ID

        Returns:
            dict: 批量操作结果
        """
        if not app_ids or len(app_ids) == 0:
            return {'success': False, 'msg': '请选择要处理的申请单'}

        batch_no = f"BATCH-APP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        success_count = 0
        fail_count = 0
        fail_details = []

        # 验证action
        valid_actions = ['approve', 'reject', 'assign']
        if action not in valid_actions:
            return {'success': False, 'msg': f'无效的操作类型，仅支持: {", ".join(valid_actions)}'}

        try:
            conn = db.get_db()
            cursor = conn.cursor()
            conn.begin()

            for app_id in app_ids:
                try:
                    where = "id=%s AND deleted=0 AND status='pending'"
                    params = [app_id]

                    if ec_id:
                        where += " AND ec_id=%s"
                        params.append(ec_id)
                    if project_id:
                        where += " AND project_id=%s"
                        params.append(project_id)

                    cursor.execute(f"SELECT * FROM business_applications WHERE {where}", params)
                    app = cursor.fetchone()

                    if not app:
                        fail_count += 1
                        fail_details.append({
                            'app_id': app_id,
                            'reason': '申请单不存在或状态不允许处理'
                        })
                        continue

                    # 根据操作类型更新状态
                    if action == 'approve':
                        new_status = 'completed'
                    elif action == 'reject':
                        new_status = 'rejected'
                    else:
                        new_status = 'processing'

                    cursor.execute(
                        """UPDATE business_applications 
                           SET status=%s, assignee_id=%s, assignee_name=%s,
                               completed_at=NOW(), updated_at=NOW()
                           WHERE id=%s""",
                        [new_status, operator_id, operator_name, app_id]
                    )
                    success_count += 1

                except Exception as e:
                    fail_count += 1
                    fail_details.append({
                        'app_id': app_id,
                        'reason': str(e)
                    })
                    logger.error(f"批量处理申请单{app_id}失败: {e}")

            # 记录批量操作日志
            cursor.execute(
                """INSERT INTO business_batch_operations
                   (batch_no, operation_type, target_type, total_count, success_count, fail_count,
                    fail_details, operator_id, operator_name, ec_id, project_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                [batch_no, 'batch_process', 'application', len(app_ids), success_count,
                 fail_count, json.dumps(fail_details, ensure_ascii=False),
                 operator_id, operator_name, ec_id, project_id]
            )

            conn.commit()

            return {
                'success': True,
                'msg': f'批量处理完成：成功{success_count}个，失败{fail_count}个',
                'data': {
                    'batch_no': batch_no,
                    'total': len(app_ids),
                    'success': success_count,
                    'fail': fail_count,
                    'fail_details': fail_details
                }
            }

        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            logger.error(f"批量处理申请单失败: {e}")
            return {'success': False, 'msg': f'批量处理失败: {str(e)}'}

        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

    @staticmethod
    def get_batch_operation_logs(operator_id, page=1, page_size=20, ec_id=None, project_id=None):
        """获取批量操作日志"""
        where = "1=1"
        params = []

        if operator_id:
            where += " AND operator_id=%s"
            params.append(operator_id)
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)

        total = db.get_total(f"SELECT COUNT(*) FROM business_batch_operations WHERE {where}", params)
        offset = (page - 1) * page_size

        logs = db.get_all(
            f"""SELECT id, batch_no, operation_type, target_type, total_count, 
                      success_count, fail_count, fail_details, operator_name, created_at
               FROM business_batch_operations
               WHERE {where}
               ORDER BY created_at DESC
               LIMIT %s OFFSET %s""",
            params + [page_size, offset]
        )

        # 解析fail_details
        for log in logs or []:
            if log.get('fail_details'):
                try:
                    log['fail_details'] = json.loads(log['fail_details'])
                except:
                    log['fail_details'] = []

        return {
            'items': logs or [],
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }
