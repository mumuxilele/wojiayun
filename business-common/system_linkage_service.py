#!/usr/bin/env python3
"""
系统联动服务模块 V44.0
功能：
  - 门禁系统联动（自动下发权限）
  - 梯控系统联动（货梯预约）
  - 暖通系统联动（加时鲜风）
  - 监控系统联动（录像调取审计）
"""
import json
import logging
import requests
from datetime import datetime, timedelta
from . import db

logger = logging.getLogger(__name__)


class SystemLinkageService:
    """系统联动服务"""

    # 门禁系统API配置（从环境变量读取）
    ACCESS_CONTROL_API = ''  # 门禁系统API地址
    ACCESS_CONTROL_KEY = ''  # 门禁系统API密钥

    # 梯控系统API配置
    LIFT_CONTROL_API = ''  # 梯控系统API地址
    LIFT_CONTROL_KEY = ''  # 梯控系统API密钥

    # 暖通系统API配置
    HVAC_CONTROL_API = ''  # 暖通系统API地址
    HVAC_CONTROL_KEY = ''  # 暖通系统API密钥

    @staticmethod
    def grant_access_permission(user_info, permission_data):
        """
        门禁系统：下发门禁权限

        Args:
            user_info: 用户信息（user_id, user_name, phone等）
            permission_data: 权限数据
                - area_ids: 区域ID列表
                - valid_from: 生效开始时间
                - valid_to: 生效结束时间
                - card_no: 门禁卡号（可选）

        Returns:
            dict: 下发结果
        """
        if not SystemLinkageService.ACCESS_CONTROL_API:
            logger.warning("门禁系统API未配置，模拟下发成功")
            return {
                'success': True,
                'msg': '模拟下发成功',
                'is_mock': True,
                'permission_id': f"MOCK_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }

        try:
            # 构建请求参数
            data = {
                'userId': user_info.get('user_id'),
                'userName': user_info.get('user_name'),
                'phone': user_info.get('user_phone'),
                'areaIds': permission_data.get('area_ids', []),
                'validFrom': permission_data.get('valid_from'),
                'validTo': permission_data.get('valid_to'),
                'cardNo': permission_data.get('card_no', ''),
                'applyTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

            # 调用门禁系统API
            resp = requests.post(
                f"{SystemLinkageService.ACCESS_CONTROL_API}/permission/grant",
                json=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {SystemLinkageService.ACCESS_CONTROL_KEY}"
                },
                timeout=15
            )

            result = resp.json()
            if result.get('success') or result.get('code') == 0:
                logger.info(f"门禁权限下发成功: user_id={user_info.get('user_id')}")
                return {
                    'success': True,
                    'msg': '权限下发成功',
                    'permission_id': result.get('data', {}).get('permissionId')
                }
            else:
                logger.error(f"门禁权限下发失败: {result}")
                return {'success': False, 'msg': result.get('msg', '下发失败')}

        except requests.RequestException as e:
            logger.error(f"门禁系统请求失败: {e}")
            return {'success': False, 'msg': f'系统请求失败: {e}'}
        except Exception as e:
            logger.error(f"门禁权限下发异常: {e}")
            return {'success': False, 'msg': f'下发异常: {e}'}

    @staticmethod
    def revoke_access_permission(user_id, area_ids=None):
        """
        门禁系统：撤销门禁权限

        Args:
            user_id: 用户ID
            area_ids: 区域ID列表（为空则撤销全部）

        Returns:
            dict: 撤销结果
        """
        if not SystemLinkageService.ACCESS_CONTROL_API:
            logger.warning("门禁系统API未配置，模拟撤销成功")
            return {'success': True, 'msg': '模拟撤销成功', 'is_mock': True}

        try:
            data = {
                'userId': user_id,
                'areaIds': area_ids or [],
                'revokeTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

            resp = requests.post(
                f"{SystemLinkageService.ACCESS_CONTROL_API}/permission/revoke",
                json=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {SystemLinkageService.ACCESS_CONTROL_KEY}"
                },
                timeout=15
            )

            result = resp.json()
            if result.get('success') or result.get('code') == 0:
                logger.info(f"门禁权限撤销成功: user_id={user_id}")
                return {'success': True, 'msg': '权限撤销成功'}
            else:
                return {'success': False, 'msg': result.get('msg', '撤销失败')}

        except Exception as e:
            logger.error(f"门禁权限撤销异常: {e}")
            return {'success': False, 'msg': f'撤销异常: {e}'}

    @staticmethod
    def reserve_cargo_lift(lift_no, time_slot, user_info, purpose=''):
        """
        梯控系统：预约货梯

        Args:
            lift_no: 货梯编号
            time_slot: 时间段
                - start_time: 开始时间
                - end_time: 结束时间
            user_info: 用户信息
            purpose: 使用目的

        Returns:
            dict: 预约结果
        """
        if not SystemLinkageService.LIFT_CONTROL_API:
            logger.warning("梯控系统API未配置，模拟预约成功")
            return {
                'success': True,
                'msg': '模拟预约成功',
                'is_mock': True,
                'reservation_id': f"LIFT_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }

        try:
            data = {
                'liftNo': lift_no,
                'startTime': time_slot.get('start_time'),
                'endTime': time_slot.get('end_time'),
                'userId': user_info.get('user_id'),
                'userName': user_info.get('user_name'),
                'phone': user_info.get('user_phone'),
                'purpose': purpose,
            }

            resp = requests.post(
                f"{SystemLinkageService.LIFT_CONTROL_API}/lift/reserve",
                json=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {SystemLinkageService.LIFT_CONTROL_KEY}"
                },
                timeout=15
            )

            result = resp.json()
            if result.get('success') or result.get('code') == 0:
                logger.info(f"货梯预约成功: lift_no={lift_no}")
                return {
                    'success': True,
                    'msg': '预约成功',
                    'reservation_id': result.get('data', {}).get('reservationId')
                }
            else:
                return {'success': False, 'msg': result.get('msg', '预约失败')}

        except Exception as e:
            logger.error(f"货梯预约异常: {e}")
            return {'success': False, 'msg': f'预约异常: {e}'}

    @staticmethod
    def check_lift_availability(lift_no, start_time, end_time):
        """
        梯控系统：检查货梯可用性

        Args:
            lift_no: 货梯编号
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            dict: 可用性检查结果
        """
        if not SystemLinkageService.LIFT_CONTROL_API:
            # 未配置时从本地数据库检查
            return SystemLinkageService._check_lift_from_db(lift_no, start_time, end_time)

        try:
            resp = requests.get(
                f"{SystemLinkageService.LIFT_CONTROL_API}/lift/availability",
                params={
                    'liftNo': lift_no,
                    'startTime': start_time,
                    'endTime': end_time,
                },
                headers={
                    'Authorization': f"Bearer {SystemLinkageService.LIFT_CONTROL_KEY}"
                },
                timeout=10
            )

            result = resp.json()
            return {
                'success': True,
                'available': result.get('data', {}).get('available', True),
                'conflicts': result.get('data', {}).get('conflicts', [])
            }

        except Exception as e:
            logger.error(f"货梯可用性检查异常: {e}")
            return {'success': False, 'msg': f'检查异常: {e}'}

    @staticmethod
    def _check_lift_from_db(lift_no, start_time, end_time):
        """从数据库检查货梯时间冲突"""
        try:
            # 查询同一货梯同一时间段的已批准申请
            conflicts = db.get_all(
                """SELECT app_no, form_data->>'$.use_date' as use_date,
                          form_data->>'$.start_time' as start_time,
                          form_data->>'$.end_time' as end_time
                   FROM business_applications
                   WHERE app_type='cargo_lift'
                     AND status IN ('pending', 'approved')
                     AND JSON_EXTRACT(form_data, '$.lift_no') = %s
                     AND NOT (form_data->>'$.end_time' <= %s OR form_data->>'$.start_time' >= %s)""",
                [lift_no, start_time, end_time]
            )

            return {
                'success': True,
                'available': not conflicts or len(conflicts) == 0,
                'conflicts': conflicts or []
            }

        except Exception as e:
            logger.error(f"数据库检查货梯冲突失败: {e}")
            return {'success': True, 'available': True, 'conflicts': []}

    @staticmethod
    def request_hvac_overtime(area_info, time_slot, user_info):
        """
        暖通系统：申请加时鲜风供应

        Args:
            area_info: 区域信息
            time_slot: 时间段
            user_info: 用户信息

        Returns:
            dict: 申请结果
        """
        if not SystemLinkageService.HVAC_CONTROL_API:
            logger.warning("暖通系统API未配置，模拟申请成功")
            return {
                'success': True,
                'msg': '模拟申请成功',
                'is_mock': True,
                'request_id': f"HVAC_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }

        try:
            data = {
                'areaId': area_info.get('area_id'),
                'areaName': area_info.get('area_name'),
                'startTime': time_slot.get('start_time'),
                'endTime': time_slot.get('end_time'),
                'userId': user_info.get('user_id'),
                'userName': user_info.get('user_name'),
                'phone': user_info.get('user_phone'),
            }

            resp = requests.post(
                f"{SystemLinkageService.HVAC_CONTROL_API}/hvac/overtime",
                json=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {SystemLinkageService.HVAC_CONTROL_KEY}"
                },
                timeout=15
            )

            result = resp.json()
            if result.get('success') or result.get('code') == 0:
                logger.info(f"暖通加时申请成功: area={area_info.get('area_name')}")
                return {
                    'success': True,
                    'msg': '申请成功',
                    'request_id': result.get('data', {}).get('requestId')
                }
            else:
                return {'success': False, 'msg': result.get('msg', '申请失败')}

        except Exception as e:
            logger.error(f"暖通加时申请异常: {e}")
            return {'success': False, 'msg': f'申请异常: {e}'}

    @staticmethod
    def log_monitor_query(query_info, operator_info):
        """
        监控系统：记录录像调取审计日志

        Args:
            query_info: 查询信息
                - camera_ids: 摄像头ID列表
                - time_range: 时间范围
                - reason: 调取原因
            operator_info: 操作人信息

        Returns:
            dict: 记录结果
        """
        try:
            # 写入审计日志
            log_data = {
                'query_type': 'monitor_query',
                'camera_ids': query_info.get('camera_ids', []),
                'time_range': query_info.get('time_range', {}),
                'reason': query_info.get('reason', ''),
                'operator_id': operator_info.get('user_id') or operator_info.get('staff_id'),
                'operator_name': operator_info.get('user_name') or operator_info.get('staff_name'),
                'operator_phone': operator_info.get('user_phone') or operator_info.get('staff_phone'),
                'query_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

            # 存储到数据库
            db.execute(
                """INSERT INTO business_monitor_query_logs
                   (query_type, camera_ids, time_range, reason, operator_id, 
                    operator_name, operator_phone, query_time, ec_id, project_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                [log_data['query_type'], json.dumps(log_data['camera_ids']),
                 json.dumps(log_data['time_range']), log_data['reason'],
                 log_data['operator_id'], log_data['operator_name'],
                 log_data['operator_phone'], log_data['query_time'],
                 operator_info.get('ec_id'), operator_info.get('project_id')]
            )

            logger.info(f"监控调取审计日志已记录: operator={log_data['operator_name']}")
            return {'success': True, 'msg': '审计日志已记录'}

        except Exception as e:
            logger.error(f"监控调取审计日志记录失败: {e}")
            return {'success': False, 'msg': f'记录失败: {e}'}


# 便捷实例
system_linkage = SystemLinkageService()
