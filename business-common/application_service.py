#!/usr/bin/env python3
"""
申请审批服务模块 V29.0
功能：
  - 8种业务申请类型的创建和处理
  - 多级审批流程管理
  - 到期提醒和通知
  - 历史记录和一键复用
"""
import json
import logging
import uuid
from datetime import datetime, timedelta
from . import db, utils

logger = logging.getLogger(__name__)


class ApplicationService:
    """申请审批服务"""

    # 申请状态
    STATUS_PENDING = 'pending'      # 待审批
    STATUS_PROCESSING = 'processing'  # 审批中
    STATUS_APPROVED = 'approved'    # 已通过
    STATUS_REJECTED = 'rejected'    # 已拒绝
    STATUS_CANCELLED = 'cancelled'  # 已取消
    STATUS_COMPLETED = 'completed'  # 已完成

    @staticmethod
    def get_application_types(category=None, is_active=1):
        """获取申请类型列表"""
        where = "is_active=%s"
        params = [is_active]
        
        if category:
            where += " AND category=%s"
            params.append(category)
        
        types = db.get_all(
            f"""SELECT id, type_code, type_name, category, icon, description,
                      form_schema, approve_flow, require_attachment, max_attachment,
                      need_remind, remind_before_hours, sort_order
               FROM business_application_types
               WHERE {where}
               ORDER BY sort_order ASC""",
            params
        )
        
        # 解析JSON字段
        for t in types or []:
            if t.get('form_schema'):
                try:
                    t['form_schema'] = json.loads(t['form_schema'])
                except:
                    t['form_schema'] = {}
            if t.get('approve_flow'):
                try:
                    t['approve_flow'] = json.loads(t['approve_flow'])
                except:
                    t['approve_flow'] = {}
        
        return types or []

    @staticmethod
    def get_application_type(type_code):
        """获取申请类型详情"""
        t = db.get_one(
            """SELECT * FROM business_application_types WHERE type_code=%s AND is_active=1""",
            [type_code]
        )
        
        if t:
            if t.get('form_schema'):
                try:
                    t['form_schema'] = json.loads(t['form_schema'])
                except:
                    t['form_schema'] = {}
            if t.get('approve_flow'):
                try:
                    t['approve_flow'] = json.loads(t['approve_flow'])
                except:
                    t['approve_flow'] = {}
        
        return t

    @staticmethod
    def validate_form_data(type_code, form_data):
        """验证表单数据"""
        app_type = ApplicationService.get_application_type(type_code)
        if not app_type:
            return {'valid': False, 'msg': '申请类型不存在'}
        
        form_schema = app_type.get('form_schema', {})
        fields = form_schema.get('fields', [])
        
        errors = []
        for field in fields:
            name = field.get('name')
            label = field.get('label')
            required = field.get('required', False)
            field_type = field.get('type')
            
            value = form_data.get(name)
            
            # 必填验证
            if required and (value is None or str(value).strip() == ''):
                errors.append(f"{label}不能为空")
                continue
            
            if not value:
                continue
            
            # 类型验证
            if field_type == 'number':
                try:
                    num_val = float(value)
                    min_val = field.get('min')
                    max_val = field.get('max')
                    if min_val is not None and num_val < min_val:
                        errors.append(f"{label}不能小于{min_val}")
                    if max_val is not None and num_val > max_val:
                        errors.append(f"{label}不能大于{max_val}")
                except:
                    errors.append(f"{label}必须是数字")
            
            elif field_type == 'date':
                try:
                    datetime.strptime(str(value), '%Y-%m-%d')
                except:
                    errors.append(f"{label}日期格式不正确")
            
            elif field_type == 'time':
                try:
                    datetime.strptime(str(value), '%H:%M')
                except:
                    try:
                        datetime.strptime(str(value), '%H:%M:%S')
                    except:
                        errors.append(f"{label}时间格式不正确")
        
        if errors:
            return {'valid': False, 'msg': '；'.join(errors)}
        
        return {'valid': True}

    @staticmethod
    def create_application(user_id, user_name, user_phone, type_code, title, form_data, 
                          ec_id=None, project_id=None, attachments=None, remark=''):
        """
        创建申请
        
        Args:
            user_id: 用户ID
            user_name: 用户名
            user_phone: 用户电话
            type_code: 申请类型代码
            title: 申请标题
            form_data: 表单数据(dict)
            ec_id: 企业ID
            project_id: 项目ID
            attachments: 附件列表 [{'file_name': '', 'file_url': '', 'file_size': 0}]
            remark: 备注
        
        Returns:
            dict: 创建结果
        """
        # 验证申请类型
        app_type = ApplicationService.get_application_type(type_code)
        if not app_type:
            return {'success': False, 'msg': '申请类型不存在'}
        
        # 验证表单数据
        validation = ApplicationService.validate_form_data(type_code, form_data)
        if not validation['valid']:
            return {'success': False, 'msg': validation['msg']}
        
        # 检查时间冲突（货梯预约）
        if type_code == 'cargo_lift':
            conflict = ApplicationService._check_lift_conflict(form_data, ec_id, project_id)
            if conflict:
                return {'success': False, 'msg': f'该时间段货梯已被预约，请选择其他时间'}
        
        # 生成申请编号
        app_no = utils.generate_no('APP')
        
        # 获取审批流程
        approve_flow = app_type.get('approve_flow', {})
        total_steps = approve_flow.get('steps', 1)
        
        # 计算到期提醒时间
        expire_time = None
        if app_type.get('need_remind'):
            # 从表单数据中获取结束日期
            end_date = form_data.get('end_date') or form_data.get('use_date')
            end_time = form_data.get('end_time', '23:59')
            if end_date:
                try:
                    remind_hours = app_type.get('remind_before_hours', 24)
                    end_datetime = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
                    expire_time = end_datetime - timedelta(hours=remind_hours)
                except:
                    pass
        
        try:
            conn = db.get_db()
            cursor = conn.cursor()
            conn.begin()
            
            # 插入申请记录
            cursor.execute(
                """INSERT INTO business_applications
                   (app_no, app_type, title, content, user_id, user_name, user_phone,
                    ec_id, project_id, status, form_data, approve_flow, total_steps,
                    expire_time, remark, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
                [app_no, type_code, title, json.dumps(form_data, ensure_ascii=False),
                 user_id, user_name, user_phone, ec_id, project_id,
                 ApplicationService.STATUS_PENDING,
                 json.dumps(form_data, ensure_ascii=False),
                 json.dumps(approve_flow, ensure_ascii=False),
                 total_steps, expire_time, remark]
            )
            
            app_id = cursor.lastrowid
            
            # 保存附件
            if attachments:
                for att in attachments:
                    cursor.execute(
                        """INSERT INTO business_application_attachments
                           (app_id, file_name, file_url, file_size, file_type, uploaded_by)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        [app_id, att.get('file_name'), att.get('file_url'),
                         att.get('file_size', 0), att.get('file_type', ''), user_id]
                    )
            
            # 创建提醒记录
            if expire_time:
                cursor.execute(
                    """INSERT INTO business_application_reminds
                       (app_id, remind_type, remind_time, remind_content)
                       VALUES (%s, %s, %s, %s)""",
                    [app_id, 'expire', expire_time, f"申请[{title}]即将到期"]
                )
            
            conn.commit()
            
            return {
                'success': True,
                'msg': '申请提交成功',
                'data': {
                    'app_id': app_id,
                    'app_no': app_no,
                    'status': ApplicationService.STATUS_PENDING
                }
            }
            
        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            logger.error(f"创建申请失败: {e}")
            return {'success': False, 'msg': '申请提交失败，请稍后重试'}
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

    @staticmethod
    def _check_lift_conflict(form_data, ec_id, project_id):
        """检查货梯时间冲突"""
        lift_no = form_data.get('lift_no')
        use_date = form_data.get('use_date')
        start_time = form_data.get('start_time')
        end_time = form_data.get('end_time')
        
        if not all([lift_no, use_date, start_time, end_time]):
            return False
        
        # 查询同一货梯同一时间段的已批准申请
        existing = db.get_one(
            """SELECT id FROM business_applications
               WHERE app_type='cargo_lift' 
                 AND status IN ('pending', 'approved', 'processing')
                 AND JSON_EXTRACT(form_data, '$.lift_no') = %s
                 AND JSON_EXTRACT(form_data, '$.use_date') = %s
                 AND (
                   (JSON_EXTRACT(form_data, '$.start_time') <= %s AND JSON_EXTRACT(form_data, '$.end_time') > %s)
                   OR (JSON_EXTRACT(form_data, '$.start_time') < %s AND JSON_EXTRACT(form_data, '$.end_time') >= %s)
                 )
                 AND ec_id=%s AND project_id=%s
               LIMIT 1""",
            [lift_no, use_date, end_time, start_time, end_time, start_time, ec_id, project_id]
        )
        
        return existing is not None

    @staticmethod
    def get_user_applications(user_id, type_code=None, status=None, keyword=None, page=1, page_size=20):
        """获取用户的申请列表"""
        where = "user_id=%s AND deleted=0"
        params = [user_id]
        
        if type_code:
            where += " AND app_type=%s"
            params.append(type_code)
        if status:
            where += " AND status=%s"
            params.append(status)
        if keyword:
            where += " AND (title LIKE %s OR app_no LIKE %s OR content LIKE %s)"
            kw = f"%{keyword}%"
            params.extend([kw, kw, kw])
        
        total = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {where}", params)
        offset = (page - 1) * page_size
        
        items = db.get_all(
            f"""SELECT id, app_no, app_type, title, status, current_step, total_steps,
                      approver_name, approve_remark, expire_time, is_favorite,
                      related_order_no, created_at, updated_at
               FROM business_applications
               WHERE {where}
               ORDER BY created_at DESC
               LIMIT %s OFFSET %s""",
            params + [page_size, offset]
        )
        
        # 获取申请类型名称
        type_names = {}
        types = ApplicationService.get_application_types()
        for t in types:
            type_names[t['type_code']] = t['type_name']
        
        for item in items or []:
            item['type_name'] = type_names.get(item.get('app_type'), item.get('app_type'))
        
        return {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }

    @staticmethod
    def get_application_detail(app_id, user_id=None, is_staff=False):
        """获取申请详情"""
        if is_staff:
            # 员工查看，需要验证权限
            app = db.get_one(
                "SELECT * FROM business_applications WHERE id=%s AND deleted=0",
                [app_id]
            )
        else:
            # 用户查看，只能看自己的
            app = db.get_one(
                "SELECT * FROM business_applications WHERE id=%s AND user_id=%s AND deleted=0",
                [app_id, user_id]
            )
        
        if not app:
            return None
        
        # 解析JSON字段
        if app.get('form_data'):
            try:
                app['form_data'] = json.loads(app['form_data'])
            except:
                app['form_data'] = {}
        if app.get('approve_flow'):
            try:
                app['approve_flow'] = json.loads(app['approve_flow'])
            except:
                app['approve_flow'] = {}
        if app.get('approve_history'):
            try:
                app['approve_history'] = json.loads(app['approve_history'])
            except:
                app['approve_history'] = []
        
        # 获取申请类型信息
        app_type = ApplicationService.get_application_type(app.get('app_type'))
        if app_type:
            app['type_name'] = app_type.get('type_name')
            app['type_icon'] = app_type.get('icon')
            app['form_schema'] = app_type.get('form_schema')
        
        # 获取附件
        attachments = db.get_all(
            """SELECT id, file_name, file_url, file_size, file_type, uploaded_at
               FROM business_application_attachments
               WHERE app_id=%s
               ORDER BY uploaded_at DESC""",
            [app_id]
        )
        app['attachments'] = attachments or []
        
        return app

    @staticmethod
    def approve_application(app_id, approver_id, approver_name, action, remark='', transfer_to=None):
        """
        审批申请
        
        Args:
            app_id: 申请ID
            approver_id: 审批人ID
            approver_name: 审批人姓名
            action: 操作类型 (approve-通过, reject-拒绝, transfer-转交)
            remark: 审批备注
            transfer_to: 转交人ID
        
        Returns:
            dict: 审批结果
        """
        app = db.get_one(
            "SELECT * FROM business_applications WHERE id=%s AND deleted=0",
            [app_id]
        )
        
        if not app:
            return {'success': False, 'msg': '申请不存在'}
        
        if app.get('status') not in [ApplicationService.STATUS_PENDING, ApplicationService.STATUS_PROCESSING]:
            return {'success': False, 'msg': '该申请已处理完毕'}
        
        try:
            conn = db.get_db()
            cursor = conn.cursor()
            conn.begin()
            
            # 解析审批历史和流程
            approve_history = []
            if app.get('approve_history'):
                try:
                    approve_history = json.loads(app['approve_history'])
                except:
                    pass
            
            approve_flow = {}
            if app.get('approve_flow'):
                try:
                    approve_flow = json.loads(app['approve_flow'])
                except:
                    pass
            
            current_step = app.get('current_step', 0)
            total_steps = app.get('total_steps', 1)
            
            # 记录审批历史
            history_record = {
                'step': current_step + 1,
                'approver_id': approver_id,
                'approver_name': approver_name,
                'action': action,
                'remark': remark,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            approve_history.append(history_record)
            
            new_status = app.get('status')
            new_step = current_step
            new_approver_id = None
            new_approver_name = None
            related_order_no = app.get('related_order_no', '')
            
            if action == 'reject':
                # 拒绝
                new_status = ApplicationService.STATUS_REJECTED
            elif action == 'transfer' and transfer_to:
                # 转交
                transfer_user = db.get_one("SELECT user_name FROM sys_user WHERE id=%s", [transfer_to])
                new_approver_id = transfer_to
                new_approver_name = transfer_user.get('user_name') if transfer_user else ''
            elif action == 'approve':
                # 通过
                if current_step + 1 >= total_steps:
                    # 最后一步，审批完成
                    new_status = ApplicationService.STATUS_APPROVED
                    
                    # 租户活动申请自动生成工单
                    if app.get('app_type') == 'tenant_activity':
                        order_no = f"WO{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        related_order_no = order_no
                        # TODO: 创建工单
                else:
                    # 进入下一步
                    new_step = current_step + 1
                    new_status = ApplicationService.STATUS_PROCESSING
                    
                    # 获取下一步审批人
                    nodes = approve_flow.get('nodes', [])
                    next_node = next((n for n in nodes if n.get('step') == new_step + 1), None)
                    if next_node:
                        # 根据角色查找审批人
                        role = next_node.get('role')
                        # TODO: 根据角色查找具体审批人
            
            # 更新申请状态
            cursor.execute(
                """UPDATE business_applications
                   SET status=%s, current_step=%s, approver_id=%s, approver_name=%s,
                       approve_remark=%s, approve_history=%s, related_order_no=%s,
                       updated_at=NOW()
                   WHERE id=%s""",
                [new_status, new_step, new_approver_id, new_approver_name,
                 remark, json.dumps(approve_history, ensure_ascii=False),
                 related_order_no, app_id]
            )
            
            conn.commit()
            
            # 发送通知给申请人
            try:
                from business_common.notification import send_notification
                status_text = {'approved': '已通过', 'rejected': '已拒绝', 'processing': '审批中'}.get(new_status, new_status)
                send_notification(
                    user_id=app.get('user_id'),
                    title=f"申请{status_text}",
                    content=f"您的申请[{app.get('title')}]已被{approver_name}{status_text}",
                    notify_type='application',
                    ref_id=str(app_id),
                    ref_type='application'
                )
            except:
                pass
            
            return {
                'success': True,
                'msg': '审批成功',
                'data': {
                    'status': new_status,
                    'current_step': new_step,
                    'total_steps': total_steps
                }
            }
            
        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            logger.error(f"审批申请失败: {e}")
            return {'success': False, 'msg': '审批失败，请稍后重试'}
        finally:
            try:
                cursor.close()
                conn.close()
            except:
                pass

    @staticmethod
    def get_pending_applications(approver_id=None, ec_id=None, project_id=None, page=1, page_size=20):
        """获取待审批的申请列表"""
        where = "status IN ('pending', 'processing') AND deleted=0"
        params = []
        
        if approver_id:
            where += " AND (approver_id=%s OR approver_id IS NULL)"
            params.append(approver_id)
        if ec_id:
            where += " AND ec_id=%s"
            params.append(ec_id)
        if project_id:
            where += " AND project_id=%s"
            params.append(project_id)
        
        total = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {where}", params)
        offset = (page - 1) * page_size
        
        items = db.get_all(
            f"""SELECT id, app_no, app_type, title, user_id, user_name, user_phone,
                      status, current_step, total_steps, form_data, created_at
               FROM business_applications
               WHERE {where}
               ORDER BY created_at DESC
               LIMIT %s OFFSET %s""",
            params + [page_size, offset]
        )
        
        # 获取申请类型名称
        type_names = {}
        types = ApplicationService.get_application_types()
        for t in types:
            type_names[t['type_code']] = {'name': t['type_name'], 'icon': t['icon']}
        
        for item in items or []:
            type_info = type_names.get(item.get('app_type'), {})
            item['type_name'] = type_info.get('name', item.get('app_type'))
            item['type_icon'] = type_info.get('icon', '')
            
            if item.get('form_data'):
                try:
                    item['form_data'] = json.loads(item['form_data'])
                except:
                    item['form_data'] = {}
        
        return {
            'items': items or [],
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size if total else 0
        }

    @staticmethod
    def set_favorite(app_id, user_id, is_favorite=1):
        """设置/取消常用申请"""
        try:
            db.execute(
                "UPDATE business_applications SET is_favorite=%s WHERE id=%s AND user_id=%s",
                [is_favorite, app_id, user_id]
            )
            return {'success': True, 'msg': '设置成功'}
        except Exception as e:
            logger.error(f"设置常用申请失败: {e}")
            return {'success': False, 'msg': '设置失败'}

    @staticmethod
    def cancel_application(app_id, user_id):
        """取消申请"""
        app = db.get_one(
            "SELECT status FROM business_applications WHERE id=%s AND user_id=%s AND deleted=0",
            [app_id, user_id]
        )
        
        if not app:
            return {'success': False, 'msg': '申请不存在'}
        
        if app.get('status') not in [ApplicationService.STATUS_PENDING]:
            return {'success': False, 'msg': '只能取消待审批的申请'}
        
        try:
            db.execute(
                "UPDATE business_applications SET status='cancelled', updated_at=NOW() WHERE id=%s",
                [app_id]
            )
            return {'success': True, 'msg': '申请已取消'}
        except Exception as e:
            logger.error(f"取消申请失败: {e}")
            return {'success': False, 'msg': '取消失败'}

    @staticmethod
    def copy_application(app_id, user_id):
        """复制申请（一键复用）"""
        app = db.get_one(
            """SELECT app_type, title, form_data, ec_id, project_id 
               FROM business_applications 
               WHERE id=%s AND user_id=%s AND deleted=0""",
            [app_id, user_id]
        )
        
        if not app:
            return {'success': False, 'msg': '申请不存在'}
        
        return {
            'success': True,
            'data': {
                'app_type': app.get('app_type'),
                'title': app.get('title'),
                'form_data': json.loads(app.get('form_data')) if app.get('form_data') else {}
            }
        }
