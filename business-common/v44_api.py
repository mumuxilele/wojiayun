#!/usr/bin/env python3
"""
V44.0 API扩展模块
功能：
  - 大厦门禁卡申请API
  - 企微推送集成
  - 系统联动接口
"""
import json
import logging
from datetime import datetime
from flask import request, jsonify

logger = logging.getLogger(__name__)


def register_v44_user_apis(app, require_login, get_current_user):
    """注册用户端V44.0 API"""

    @app.route('/api/user/applications/v2/access-card', methods=['POST'])
    @require_login
    def create_access_card_application(user):
        """创建大厦门禁卡申请"""
        from business_common.application_service import ApplicationService
        from business_common.external_auth_service import ExternalAuthService
        from business_common.response_builder import success_resp, error_resp, ErrorCode

        data = request.get_json() or {}

        # 获取用户完整信息（包含ec_id, project_id）
        user_info = ExternalAuthService.get_user_info(user.get('access_token', ''))
        if not user_info:
            return error_resp(ErrorCode.AUTH_FAILED, '获取用户信息失败')

        # 构建表单数据
        form_data = {
            'applicant_name': data.get('applicant_name'),
            'applicant_phone': data.get('applicant_phone'),
            'department': data.get('department'),
            'position': data.get('position', ''),
            'card_type': data.get('card_type'),
            'area_ids': data.get('area_ids', []),
            'valid_from': data.get('valid_from'),
            'valid_to': data.get('valid_to'),
            'reason': data.get('reason'),
            'remark': data.get('remark', ''),
        }

        # 创建申请
        result = ApplicationService.create_application(
            type_code='access_card',
            form_data=form_data,
            user_id=user_info.get('user_id'),
            user_name=user_info.get('user_name') or form_data['applicant_name'],
            user_phone=user_info.get('user_phone') or form_data['applicant_phone'],
            ec_id=user_info.get('ec_id'),
            project_id=user_info.get('project_id'),
            attachments=data.get('attachments', [])
        )

        if result.get('success'):
            return success_resp(result.get('data'), '申请提交成功')
        else:
            return error_resp(ErrorCode.DB_ERROR, result.get('msg', '申请提交失败'))

    @app.route('/api/user/applications/v2/<int:app_id>/cancel', methods=['POST'])
    @require_login
    def cancel_application_v44(user, app_id):
        """取消申请"""
        from business_common.application_service import ApplicationService
        from business_common.response_builder import success_resp, error_resp, ErrorCode

        result = ApplicationService.cancel_application(
            app_id=app_id,
            user_id=user.get('user_id')
        )

        if result.get('success'):
            return success_resp(msg='取消成功')
        else:
            return error_resp(ErrorCode.DB_ERROR, result.get('msg', '取消失败'))

    @app.route('/api/user/applications/v2/<int:app_id>/copy', methods=['POST'])
    @require_login
    def copy_application_v44(user, app_id):
        """复制申请"""
        from business_common.application_service import ApplicationService
        from business_common.response_builder import success_resp, error_resp, ErrorCode

        result = ApplicationService.copy_application(
            app_id=app_id,
            user_id=user.get('user_id')
        )

        if result.get('success'):
            return success_resp(result.get('data'), '复制成功')
        else:
            return error_resp(ErrorCode.DB_ERROR, result.get('msg', '复制失败'))

    @app.route('/api/user/applications/v2/favorites', methods=['GET'])
    @require_login
    def get_favorite_applications(user):
        """获取常用申请"""
        from business_common import db
        from business_common.response_builder import success_resp

        user_id = user.get('user_id')

        favorites = db.get_all(
            """SELECT a.*, t.type_name, t.icon 
               FROM business_applications a
               LEFT JOIN business_application_types t ON a.app_type = t.type_code
               WHERE a.user_id = %s AND a.is_favorite = 1 AND a.deleted = 0
               ORDER BY a.updated_at DESC""",
            [user_id]
        )

        return success_resp({'items': favorites or []})

    @app.route('/api/user/applications/v2/<int:app_id>/favorite', methods=['POST'])
    @require_login
    def set_favorite_application(user, app_id):
        """设置常用申请"""
        from business_common import db
        from business_common.response_builder import success_resp, error_resp, ErrorCode

        data = request.get_json() or {}
        is_favorite = data.get('is_favorite', True)

        try:
            db.execute(
                "UPDATE business_applications SET is_favorite = %s WHERE id = %s AND user_id = %s",
                [1 if is_favorite else 0, app_id, user.get('user_id')]
            )
            return success_resp(msg='设置成功')
        except Exception as e:
            logger.error(f"设置常用申请失败: {e}")
            return error_resp(ErrorCode.DB_ERROR, '设置失败')


def register_v44_staff_apis(app, require_staff, get_current_staff):
    """注册员工端V44.0 API"""

    @app.route('/api/staff/applications/v2/<int:app_id>/approve', methods=['POST'])
    @require_staff
    def approve_application_v44(staff, app_id):
        """审批申请（增强版：支持系统联动）"""
        from business_common import db
        from business_common.application_service import ApplicationService
        from business_common.wecom_push_service import WeComPushService
        from business_common.system_linkage_service import SystemLinkageService
        from business_common.response_builder import success_resp, error_resp, ErrorCode

        data = request.get_json() or {}
        action = data.get('action')  # approve / reject
        remark = data.get('remark', '')

        # 获取申请详情
        app_info = db.get_one(
            "SELECT * FROM business_applications WHERE id = %s",
            [app_id]
        )

        if not app_info:
            return error_resp(ErrorCode.NOT_FOUND, '申请不存在')

        # 执行审批
        result = ApplicationService.approve_application(
            app_id=app_id,
            action=action,
            approver_id=staff.get('staff_id'),
            approver_name=staff.get('staff_name'),
            remark=remark
        )

        if not result.get('success'):
            return error_resp(ErrorCode.DB_ERROR, result.get('msg', '审批失败'))

        # 审批通过后执行系统联动
        if action == 'approve':
            app_type = app_info.get('app_type')
            form_data = json.loads(app_info.get('form_data', '{}')) if isinstance(app_info.get('form_data'), str) else app_info.get('form_data', {})

            # 大厦门禁卡申请：自动下发门禁权限
            if app_type == 'access_card':
                linkage_result = SystemLinkageService.grant_access_permission(
                    user_info={
                        'user_id': app_info.get('user_id'),
                        'user_name': app_info.get('user_name'),
                        'user_phone': app_info.get('user_phone'),
                    },
                    permission_data={
                        'area_ids': form_data.get('area_ids', []),
                        'valid_from': form_data.get('valid_from'),
                        'valid_to': form_data.get('valid_to'),
                    }
                )

                # 记录联动日志
                db.execute(
                    """INSERT INTO business_system_linkage_logs
                       (linkage_type, app_no, action, status, created_at)
                       VALUES (%s, %s, %s, %s, NOW())""",
                    ['access_control', app_info.get('app_no'), 'grant_access',
                     'success' if linkage_result.get('success') else 'failed']
                )

            # 货梯使用申请：预约货梯
            elif app_type == 'cargo_lift':
                linkage_result = SystemLinkageService.reserve_cargo_lift(
                    lift_no=form_data.get('lift_no'),
                    time_slot={
                        'start_time': form_data.get('start_time'),
                        'end_time': form_data.get('end_time'),
                    },
                    user_info={
                        'user_id': app_info.get('user_id'),
                        'user_name': app_info.get('user_name'),
                        'user_phone': app_info.get('user_phone'),
                    },
                    purpose=form_data.get('purpose', '')
                )

            # 加时鲜风申请：联动暖通系统
            elif app_type == 'hvac_overtime':
                linkage_result = SystemLinkageService.request_hvac_overtime(
                    area_info={
                        'area_id': form_data.get('area_id'),
                        'area_name': form_data.get('area_name'),
                    },
                    time_slot={
                        'start_time': form_data.get('start_time'),
                        'end_time': form_data.get('end_time'),
                    },
                    user_info={
                        'user_id': app_info.get('user_id'),
                        'user_name': app_info.get('user_name'),
                        'user_phone': app_info.get('user_phone'),
                    }
                )

            # 监控录像调用：记录审计日志
            elif app_type == 'monitor_query':
                SystemLinkageService.log_monitor_query(
                    query_info={
                        'camera_ids': form_data.get('camera_ids', []),
                        'time_range': {
                            'start': form_data.get('query_start_time'),
                            'end': form_data.get('query_end_time'),
                        },
                        'reason': form_data.get('reason', ''),
                    },
                    operator_info={
                        'user_id': app_info.get('user_id'),
                        'user_name': app_info.get('user_name'),
                        'user_phone': app_info.get('user_phone'),
                        'ec_id': app_info.get('ec_id'),
                        'project_id': app_info.get('project_id'),
                    }
                )

        # 企微推送通知
        try:
            WeComPushService.push_approval_result(
                app_info=app_info,
                result='approved' if action == 'approve' else 'rejected',
                approver_name=staff.get('staff_name')
            )
        except Exception as e:
            logger.warning(f"企微推送失败: {e}")

        return success_resp(msg='审批成功')

    @app.route('/api/staff/applications/v2/stats', methods=['GET'])
    @require_staff
    def get_application_stats_v44(staff):
        """获取申请统计"""
        from business_common import db
        from business_common.response_builder import success_resp

        stats = db.get_one(
            """SELECT 
                 COUNT(*) as total,
                 SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                 SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                 SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                 SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing
               FROM business_applications 
               WHERE deleted = 0"""
        )

        # 按类型统计
        by_type = db.get_all(
            """SELECT app_type, COUNT(*) as count 
               FROM business_applications 
               WHERE deleted = 0 
               GROUP BY app_type"""
        )

        return success_resp({
            'total': stats.get('total', 0) if stats else 0,
            'pending': stats.get('pending', 0) if stats else 0,
            'approved': stats.get('approved', 0) if stats else 0,
            'rejected': stats.get('rejected', 0) if stats else 0,
            'processing': stats.get('processing', 0) if stats else 0,
            'by_type': by_type or []
        })

    @app.route('/api/staff/applications/v2/remind-expired', methods=['GET'])
    @require_staff
    def get_expired_reminders(staff):
        """获取到期提醒列表"""
        from business_common import db
        from business_common.response_builder import success_resp

        # 查询即将到期的申请（候餐椅、货梯等）
        reminders = db.get_all(
            """SELECT a.*, t.type_name
               FROM business_applications a
               LEFT JOIN business_application_types t ON a.app_type = t.type_code
               WHERE a.status = 'approved'
                 AND a.expire_time IS NOT NULL
                 AND a.expire_time <= DATE_ADD(NOW(), INTERVAL 2 HOUR)
                 AND a.expire_time > NOW()
                 AND a.deleted = 0
               ORDER BY a.expire_time ASC"""
        )

        return success_resp({'items': reminders or []})
