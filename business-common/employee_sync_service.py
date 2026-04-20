#!/usr/bin/env python3
"""
员工数据同步服务
- 从第三方API同步员工数据到本地表
- 限制每小时只同步一次
"""

import logging
import requests
import threading
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger('employee_sync')

# 第三方API配置
EMPLOYEE_API_URL = "https://gj.wojiacloud.com/api/employees/getProjectEmployeesV2"

# 同步缓存key前缀
SYNC_CACHE_PREFIX = "employee_sync:"


class EmployeeSyncService:
    """员工数据同步服务"""
    
    def __init__(self, db_instance=None, cache_instance=None):
        self.db = db_instance
        self.cache = cache_instance  # 用于记录同步时间
    
    def should_sync(self, ec_id: str) -> bool:
        """
        检查是否需要同步（一小时内只同步一次）
        
        Args:
            ec_id: 企业ID
            
        Returns:
            bool: 是否需要同步
        """
        if not ec_id:
            return False
        
        cache_key = f"{SYNC_CACHE_PREFIX}{ec_id}"
        
        # 检查缓存中是否有上次同步时间
        if self.cache:
            last_sync = self.cache.get(cache_key)
            if last_sync:
                # 一小时内已同步过
                logger.info(f"企业 {ec_id} 在一小时内已同步过员工数据")
                return False
        
        return True
    
    def mark_synced(self, ec_id: str):
        """
        标记已同步（缓存1小时）
        
        Args:
            ec_id: 企业ID
        """
        cache_key = f"{SYNC_CACHE_PREFIX}{ec_id}"
        if self.cache:
            self.cache.set(cache_key, datetime.now().isoformat(), expire=3600)
    
    def fetch_employees_from_api(self, access_token: str, project_id: str = None) -> list:
        """
        从第三方API获取员工列表
        
        Args:
            access_token: 访问令牌
            project_id: 项目ID（可选）
            
        Returns:
            list: 员工列表
        """
        try:
            params = {
                'access_token': access_token,
                'searchPhrase': '',
                'rowCount': 2000,
                'current': 1
            }
            
            if project_id:
                params['projectId'] = project_id
            
            logger.info(f"开始从API获取员工数据: {EMPLOYEE_API_URL}")
            
            response = requests.get(EMPLOYEE_API_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 解析返回数据
            if isinstance(data, dict):
                # 可能的结构: {success: true, data: {rows: [...]}} 或 {rows: [...]}
                if 'data' in data and isinstance(data['data'], dict):
                    employees = data['data'].get('rows', [])
                elif 'rows' in data:
                    employees = data.get('rows', [])
                else:
                    employees = data.get('data', [])
            elif isinstance(data, list):
                employees = data
            else:
                logger.warning(f"未知的API返回格式: {type(data)}")
                employees = []
            
            logger.info(f"获取到 {len(employees)} 条员工数据")
            return employees
            
        except requests.exceptions.Timeout:
            logger.error("获取员工数据超时")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"获取员工数据失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析员工数据失败: {e}")
            return []
    
    def sync_employees(self, access_token: str, ec_id: str, project_id: str = None) -> Dict[str, Any]:
        """
        同步员工数据
        
        Args:
            access_token: 访问令牌
            ec_id: 企业ID
            project_id: 项目ID（可选）
            
        Returns:
            dict: 同步结果
        """
        if not self.should_sync(ec_id):
            return {'success': True, 'msg': '一小时内已同步过', 'skipped': True}
        
        # 获取员工数据
        employees = self.fetch_employees_from_api(access_token, project_id)
        
        if not employees:
            return {'success': False, 'msg': '未获取到员工数据'}
        
        # 同步到数据库
        inserted = 0
        updated = 0
        errors = 0
        
        for emp in employees:
            try:
                emp_id = emp.get('id') or emp.get('FID') or emp.get('empId')
                emp_name = emp.get('name') or emp.get('FName') or emp.get('empName')
                
                if not emp_id:
                    continue
                
                # 检查是否存在
                existing = self.db.get_one(
                    "SELECT FID FROM t_pc_employee WHERE FID = %s",
                    [emp_id]
                )
                
                now = datetime.now()
                
                if existing:
                    # 更新
                    self.db.execute(
                        """
                        UPDATE t_pc_employee 
                        SET FName = %s, FECID = %s, FStatus = 1, FUpdateTime = NOW()
                        WHERE FID = %s
                        """,
                        [emp_name, ec_id, emp_id]
                    )
                    updated += 1
                else:
                    # 插入
                    self.db.execute(
                        """
                        INSERT INTO t_pc_employee 
                        (FID, FName, FECID, FStatus, FCreateTime, FUpdateTime, FIsDelete)
                        VALUES (%s, %s, %s, 1, NOW(), NOW(), 0)
                        """,
                        [emp_id, emp_name, ec_id]
                    )
                    inserted += 1
                    
            except Exception as e:
                logger.error(f"同步员工 {emp.get('id', 'unknown')} 失败: {e}")
                errors += 1
        
        # 标记已同步
        self.mark_synced(ec_id)
        
        result = {
            'success': True,
            'msg': f'同步完成: 新增{inserted}条, 更新{updated}条',
            'inserted': inserted,
            'updated': updated,
            'errors': errors,
            'total': len(employees)
        }
        
        logger.info(f"员工同步完成: {result}")
        return result
    
    def sync_employees_async(self, access_token: str, ec_id: str, project_id: str = None):
        """
        异步同步员工数据
        
        Args:
            access_token: 访问令牌
            ec_id: 企业ID
            project_id: 项目ID（可选）
        """
        def _sync():
            try:
                self.sync_employees(access_token, ec_id, project_id)
            except Exception as e:
                logger.error(f"异步同步员工数据失败: {e}")
        
        thread = threading.Thread(target=_sync, daemon=True)
        thread.start()


# 便捷实例
employee_sync = None

def init_employee_sync(db_instance, cache_instance=None):
    """初始化员工同步服务"""
    global employee_sync
    employee_sync = EmployeeSyncService(db_instance, cache_instance)
    return employee_sync
