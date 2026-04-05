#!/usr/bin/env python3
"""
系统健康检查服务 - V17.0新增
功能：
  1. 数据库连接状态检查
  2. 缓存服务状态检查
  3. 磁盘空间检查
  4. 内存使用情况检查
  5. 关键API响应时间检查
  6. 生成健康报告

使用方法：
  from health_check import HealthCheck
  checker = HealthCheck()
  result = checker.run_all_checks()
"""
import os
import sys
import time
import psutil
import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class HealthCheck:
    """系统健康检查服务"""
    
    # 健康检查项配置
    CHECK_INTERVAL = 60  # 检查间隔（秒）
    
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
    
    def check_database(self) -> Dict[str, Any]:
        """检查数据库连接"""
        result = {
            'name': 'database',
            'status': 'unknown',
            'message': '',
            'details': {},
            'duration_ms': 0
        }
        
        start = time.time()
        try:
            import pymysql
            from business_common import config
            
            conn = pymysql.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                database=config.DB_NAME,
                connect_timeout=5
            )
            
            # 执行简单查询测试
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            
            result['status'] = 'healthy'
            result['message'] = '数据库连接正常'
            result['details'] = {
                'host': config.DB_HOST,
                'port': config.DB_PORT,
                'database': config.DB_NAME
            }
        except ImportError:
            result['status'] = 'skipped'
            result['message'] = 'pymysql未安装，跳过数据库检查'
        except Exception as e:
            result['status'] = 'unhealthy'
            result['message'] = f'数据库连接失败: {str(e)}'
            logger.error(f"数据库健康检查失败: {e}")
        finally:
            result['duration_ms'] = int((time.time() - start) * 1000)
        
        return result
    
    def check_cache(self) -> Dict[str, Any]:
        """检查缓存服务"""
        result = {
            'name': 'cache',
            'status': 'unknown',
            'message': '',
            'details': {},
            'duration_ms': 0
        }
        
        start = time.time()
        try:
            from business_common.cache_service import cache_get, cache_set, cache_delete
            
            # 测试缓存读写
            test_key = '_health_check_test'
            test_value = {'timestamp': time.time()}
            
            cache_set(test_key, test_value, 10)
            retrieved = cache_get(test_key)
            cache_delete(test_key)
            
            if retrieved:
                result['status'] = 'healthy'
                result['message'] = '缓存服务正常'
                result['details'] = {
                    'type': 'memory' if not os.getenv('REDIS_URL') else 'redis'
                }
            else:
                result['status'] = 'degraded'
                result['message'] = '缓存读写测试失败'
        except Exception as e:
            result['status'] = 'unhealthy'
            result['message'] = f'缓存服务异常: {str(e)}'
            logger.error(f"缓存健康检查失败: {e}")
        finally:
            result['duration_ms'] = int((time.time() - start) * 1000)
        
        return result
    
    def check_disk_space(self) -> Dict[str, Any]:
        """检查磁盘空间"""
        result = {
            'name': 'disk',
            'status': 'unknown',
            'message': '',
            'details': {},
            'duration_ms': 0
        }
        
        start = time.time()
        try:
            usage = psutil.disk_usage('/')
            
            result['details'] = {
                'total_gb': round(usage.total / (1024**3), 2),
                'used_gb': round(usage.used / (1024**3), 2),
                'free_gb': round(usage.free / (1024**3), 2),
                'percent': usage.percent
            }
            
            if usage.percent > 95:
                result['status'] = 'unhealthy'
                result['message'] = f'磁盘空间严重不足 ({usage.percent}%)'
            elif usage.percent > 85:
                result['status'] = 'degraded'
                result['message'] = f'磁盘空间不足 ({usage.percent}%)'
            else:
                result['status'] = 'healthy'
                result['message'] = f'磁盘空间充足 ({usage.percent}% 已用)'
        except Exception as e:
            result['status'] = 'unknown'
            result['message'] = f'无法获取磁盘信息: {str(e)}'
            logger.error(f"磁盘健康检查失败: {e}")
        finally:
            result['duration_ms'] = int((time.time() - start) * 1000)
        
        return result
    
    def check_memory(self) -> Dict[str, Any]:
        """检查内存使用"""
        result = {
            'name': 'memory',
            'status': 'unknown',
            'message': '',
            'details': {},
            'duration_ms': 0
        }
        
        start = time.time()
        try:
            mem = psutil.virtual_memory()
            
            result['details'] = {
                'total_gb': round(mem.total / (1024**3), 2),
                'available_gb': round(mem.available / (1024**3), 2),
                'used_gb': round(mem.used / (1024**3), 2),
                'percent': mem.percent
            }
            
            if mem.percent > 95:
                result['status'] = 'unhealthy'
                result['message'] = f'内存严重不足 ({mem.percent}%)'
            elif mem.percent > 85:
                result['status'] = 'degraded'
                result['message'] = f'内存使用率高 ({mem.percent}%)'
            else:
                result['status'] = 'healthy'
                result['message'] = f'内存使用正常 ({mem.percent}%)'
        except Exception as e:
            result['status'] = 'unknown'
            result['message'] = f'无法获取内存信息: {str(e)}'
            logger.error(f"内存健康检查失败: {e}")
        finally:
            result['duration_ms'] = int((time.time() - start) * 1000)
        
        return result
    
    def check_cpu(self) -> Dict[str, Any]:
        """检查CPU使用"""
        result = {
            'name': 'cpu',
            'status': 'unknown',
            'message': '',
            'details': {},
            'duration_ms': 0
        }
        
        start = time.time()
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            
            result['details'] = {
                'percent': cpu_percent,
                'count': cpu_count,
                'physical_count': psutil.cpu_count(logical=False)
            }
            
            if cpu_percent > 95:
                result['status'] = 'unhealthy'
                result['message'] = f'CPU负载极高 ({cpu_percent}%)'
            elif cpu_percent > 85:
                result['status'] = 'degraded'
                result['message'] = f'CPU负载较高 ({cpu_percent}%)'
            else:
                result['status'] = 'healthy'
                result['message'] = f'CPU负载正常 ({cpu_percent}%)'
        except Exception as e:
            result['status'] = 'unknown'
            result['message'] = f'无法获取CPU信息: {str(e)}'
            logger.error(f"CPU健康检查失败: {e}")
        finally:
            result['duration_ms'] = int((time.time() - start) * 1000)
        
        return result
    
    def check_process(self) -> Dict[str, Any]:
        """检查当前进程"""
        result = {
            'name': 'process',
            'status': 'unknown',
            'message': '',
            'details': {},
            'duration_ms': 0
        }
        
        start = time.time()
        try:
            process = psutil.Process(os.getpid())
            
            result['details'] = {
                'pid': process.pid,
                'name': process.name(),
                'memory_mb': round(process.memory_info().rss / (1024**2), 2),
                'cpu_percent': process.cpu_percent(interval=0.1),
                'threads': process.num_threads(),
                'uptime_seconds': int(time.time() - process.create_time())
            }
            
            result['status'] = 'healthy'
            result['message'] = '进程运行正常'
        except Exception as e:
            result['status'] = 'unknown'
            result['message'] = f'无法获取进程信息: {str(e)}'
            logger.error(f"进程健康检查失败: {e}")
        finally:
            result['duration_ms'] = int((time.time() - start) * 1000)
        
        return result
    
    def check_dependencies(self) -> Dict[str, Any]:
        """检查依赖服务"""
        result = {
            'name': 'dependencies',
            'status': 'unknown',
            'message': '',
            'details': {},
            'duration_ms': 0
        }
        
        start = time.time()
        dependencies = []
        
        # 检查MySQL
        try:
            import pymysql
            dependencies.append({'name': 'pymysql', 'status': 'installed', 'version': pymysql.__version__})
        except ImportError:
            dependencies.append({'name': 'pymysql', 'status': 'missing'})
        
        # 检查Flask
        try:
            import flask
            dependencies.append({'name': 'flask', 'status': 'installed', 'version': flask.__version__})
        except ImportError:
            dependencies.append({'name': 'flask', 'status': 'missing'})
        
        # 检查Redis
        try:
            import redis
            dependencies.append({'name': 'redis', 'status': 'installed', 'version': redis.__version__})
        except ImportError:
            dependencies.append({'name': 'redis', 'status': 'missing'})
        
        result['details']['dependencies'] = dependencies
        
        missing = [d for d in dependencies if d['status'] == 'missing']
        if missing:
            result['status'] = 'degraded'
            result['message'] = f'{len(missing)}个依赖未安装'
        else:
            result['status'] = 'healthy'
            result['message'] = '所有依赖已安装'
        
        result['duration_ms'] = int((time.time() - start) * 1000)
        return result
    
    def run_all_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        checks = [
            self.check_database,
            self.check_cache,
            self.check_disk_space,
            self.check_memory,
            self.check_cpu,
            self.check_process,
            self.check_dependencies
        ]
        
        results = []
        for check in checks:
            try:
                result = check()
                results.append(result)
            except Exception as e:
                logger.error(f"健康检查 {check.__name__} 执行失败: {e}")
                results.append({
                    'name': check.__name__.replace('check_', ''),
                    'status': 'error',
                    'message': str(e),
                    'duration_ms': 0
                })
        
        # 计算总体状态
        statuses = [r['status'] for r in results]
        if 'unhealthy' in statuses:
            overall = 'unhealthy'
        elif 'degraded' in statuses:
            overall = 'degraded'
        elif 'error' in statuses:
            overall = 'error'
        else:
            overall = 'healthy'
        
        return {
            'status': overall,
            'timestamp': datetime.now().isoformat(),
            'duration_ms': int((time.time() - self.start_time) * 1000),
            'checks': results
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """获取健康检查摘要"""
        result = self.run_all_checks()
        
        summary = {
            'status': result['status'],
            'timestamp': result['timestamp'],
            'duration_ms': result['duration_ms'],
            'checks_total': len(result['checks']),
            'checks_passed': sum(1 for r in result['checks'] if r['status'] == 'healthy'),
            'checks_degraded': sum(1 for r in result['checks'] if r['status'] == 'degraded'),
            'checks_failed': sum(1 for r in result['checks'] if r['status'] in ('unhealthy', 'error')),
            'checks_skipped': sum(1 for r in result['checks'] if r['status'] == 'skipped')
        }
        
        return summary


def format_health_report(result: Dict) -> str:
    """格式化健康检查报告"""
    lines = []
    lines.append("=" * 60)
    lines.append("系统健康检查报告")
    lines.append("=" * 60)
    lines.append(f"检查时间: {result['timestamp']}")
    lines.append(f"总耗时: {result['duration_ms']}ms")
    lines.append(f"总体状态: {result['status'].upper()}")
    lines.append("-" * 60)
    
    for check in result.get('checks', []):
        icon = {
            'healthy': '[OK]',
            'degraded': '[WARN]',
            'unhealthy': '[FAIL]',
            'error': '[FAIL]',
            'unknown': '[?]',
            'skipped': '[-]'
        }.get(check['status'], '[?]')
        
        lines.append(f"{icon} [{check['name'].upper()}] {check['message']}")
        lines.append(f"    耗时: {check['duration_ms']}ms")
        
        if check.get('details'):
            for key, value in check['details'].items():
                if isinstance(value, dict):
                    for k, v in value.items():
                        lines.append(f"      {k}: {v}")
                else:
                    lines.append(f"    {key}: {value}")
        lines.append("")
    
    lines.append("=" * 60)
    return '\n'.join(lines)


if __name__ == '__main__':
    # 直接运行时执行健康检查
    checker = HealthCheck()
    result = checker.run_all_checks()
    print(format_health_report(result))
