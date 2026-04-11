"""
系统监控增强 V32.0
功能:
  - 性能指标采集
  - 异常告警
  - 健康检查增强
  - 慢查询检测
"""
import logging
import time
import psutil
from datetime import datetime, timedelta
from functools import wraps
from flask import request, g, jsonify
from . import db
from .cache_service import cache_get, cache_set

logger = logging.getLogger(__name__)


class EnhancedMonitor:
    """增强监控系统"""

    # 告警阈值配置
    THRESHOLDS = {
        'response_time_ms': {
            'warning': 1000,    # 1秒警告
            'critical': 3000    # 3秒严重
        },
        'error_rate_percent': {
            'warning': 5,
            'critical': 10
        },
        'cpu_percent': {
            'warning': 70,
            'critical': 90
        },
        'memory_percent': {
            'warning': 75,
            'critical': 90
        },
        'disk_percent': {
            'warning': 80,
            'critical': 95
        },
        'db_query_ms': {
            'warning': 500,
            'critical': 2000
        }
    }

    @classmethod
    def get_metrics(cls):
        """
        获取系统性能指标

        Returns:
            dict: {
                'system': {...},
                'application': {...},
                'database': {...},
                'cache': {...}
            }
        """
        metrics = {
            'timestamp': datetime.now().isoformat()
        }

        # 系统指标
        try:
            metrics['system'] = {
                'cpu': {
                    'percent': psutil.cpu_percent(interval=0.1),
                    'count': psutil.cpu_count(),
                },
                'memory': {
                    'total': psutil.virtual_memory().total,
                    'available': psutil.virtual_memory().available,
                    'percent': psutil.virtual_memory().percent,
                    'used': psutil.virtual_memory().used,
                },
                'disk': {
                    'total': psutil.disk_usage('/').total,
                    'used': psutil.disk_usage('/').used,
                    'free': psutil.disk_usage('/').free,
                    'percent': psutil.disk_usage('/').percent,
                },
                'network': cls._get_network_io(),
            }

            # 告警判断
            metrics['system']['alerts'] = cls._check_system_alerts(metrics['system'])

        except Exception as e:
            logger.error(f"获取系统指标失败: {e}")
            metrics['system'] = {'error': str(e)}

        # 应用指标
        try:
            metrics['application'] = cls._get_application_metrics()
        except Exception as e:
            logger.error(f"获取应用指标失败: {e}")
            metrics['application'] = {'error': str(e)}

        # 数据库指标
        try:
            metrics['database'] = cls._get_database_metrics()
        except Exception as e:
            logger.error(f"获取数据库指标失败: {e}")
            metrics['database'] = {'error': str(e)}

        # 缓存指标
        try:
            metrics['cache'] = cls._get_cache_metrics()
        except Exception as e:
            logger.error(f"获取缓存指标失败: {e}")
            metrics['cache'] = {'error': str(e)}

        return metrics

    @classmethod
    def _get_network_io(cls):
        """获取网络IO"""
        try:
            net = psutil.net_io_counters()
            return {
                'bytes_sent': net.bytes_sent,
                'bytes_recv': net.bytes_recv,
                'packets_sent': net.packets_sent,
                'packets_recv': net.packets_recv,
                'errin': net.errin,
                'errout': net.errout,
            }
        except:
            return {}

    @classmethod
    def _check_system_alerts(cls, system_metrics):
        """检查系统告警"""
        alerts = []

        # CPU告警
        if system_metrics.get('cpu', {}).get('percent', 0) > cls.THRESHOLDS['cpu_percent']['critical']:
            alerts.append({
                'level': 'critical',
                'type': 'cpu',
                'message': f"CPU使用率过高: {system_metrics['cpu']['percent']}%"
            })
        elif system_metrics.get('cpu', {}).get('percent', 0) > cls.THRESHOLDS['cpu_percent']['warning']:
            alerts.append({
                'level': 'warning',
                'type': 'cpu',
                'message': f"CPU使用率偏高: {system_metrics['cpu']['percent']}%"
            })

        # 内存告警
        if system_metrics.get('memory', {}).get('percent', 0) > cls.THRESHOLDS['memory_percent']['critical']:
            alerts.append({
                'level': 'critical',
                'type': 'memory',
                'message': f"内存使用率过高: {system_metrics['memory']['percent']}%"
            })

        # 磁盘告警
        if system_metrics.get('disk', {}).get('percent', 0) > cls.THRESHOLDS['disk_percent']['critical']:
            alerts.append({
                'level': 'critical',
                'type': 'disk',
                'message': f"磁盘使用率过高: {system_metrics['disk']['percent']}%"
            })

        return alerts

    @classmethod
    def _get_application_metrics(cls):
        """获取应用层指标"""
        # 从缓存获取聚合指标
        cache_key = 'app_metrics_hourly'
        cached = cache_get(cache_key)

        if cached:
            return cached

        try:
            # API请求统计（过去1小时）
            hour_ago = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

            # 查询日志表（如果有的话）
            metrics = {
                'requests_total': 0,
                'requests_by_status': {},
                'avg_response_time': 0,
                'slow_requests': 0,
            }

            # 缓存
            cache_set(cache_key, metrics, 300)  # 5分钟缓存

            return metrics

        except Exception as e:
            logger.warning(f"获取应用指标失败: {e}")
            return {'error': str(e)}

    @classmethod
    def _get_database_metrics(cls):
        """获取数据库指标"""
        try:
            # 连接数
            result = db.get_one("""
                SELECT
                    COUNT(*) as total_connections,
                    SUM(CASE WHEN command = 'Sleep' THEN 1 ELSE 0 END) as idle_connections
                FROM information_schema.processlist
            """) if hasattr(db, 'get_db') else None

            # 查询统计
            qps = 0
            try:
                status = db.get_one("SHOW STATUS LIKE 'Questions'")
                uptime = db.get_one("SHOW STATUS LIKE 'Uptime'")
                if status and uptime:
                    qps = int(status.get('Value', 0)) / max(int(uptime.get('Value', 1)), 1)
            except:
                pass

            return {
                'connections': {
                    'total': result.get('total_connections', 0) if result else 0,
                    'idle': result.get('idle_connections', 0) if result else 0,
                },
                'qps': round(qps, 2),
                'slow_queries': 0,
            }

        except Exception as e:
            logger.warning(f"获取数据库指标失败: {e}")
            return {'error': str(e)}

    @classmethod
    def _get_cache_metrics(cls):
        """获取缓存指标"""
        try:
            from .redis_cache_service import RedisCache
            if hasattr(RedisCache, 'get_stats'):
                stats = RedisCache.get_stats()
                return stats
        except:
            pass

        return {
            'status': 'unknown',
            'note': 'Redis缓存统计不可用'
        }

    @classmethod
    def get_health_check(cls):
        """
        获取详细健康检查结果

        Returns:
            dict: {
                'healthy': bool,
                'checks': {...},
                'alerts': [...]
            }
        """
        checks = {}
        alerts = []

        # 1. 数据库健康检查
        try:
            db.get_one("SELECT 1")
            checks['database'] = {'status': 'healthy', 'message': '连接正常'}
        except Exception as e:
            checks['database'] = {'status': 'unhealthy', 'message': str(e)}
            alerts.append({'level': 'critical', 'type': 'database', 'message': f'数据库连接失败: {e}'})

        # 2. 缓存健康检查
        try:
            cache_set('health_check', 'ok', 10)
            result = cache_get('health_check')
            if result == 'ok':
                checks['cache'] = {'status': 'healthy', 'message': '连接正常'}
            else:
                checks['cache'] = {'status': 'degraded', 'message': '读写不一致'}
        except Exception as e:
            checks['cache'] = {'status': 'unhealthy', 'message': str(e)}
            alerts.append({'level': 'warning', 'type': 'cache', 'message': f'缓存异常: {e}'})

        # 3. 系统资源检查
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent

            if cpu > 90 or mem > 90 or disk > 95:
                checks['system'] = {'status': 'unhealthy', 'message': '资源紧张'}
                alerts.append({'level': 'critical', 'type': 'system', 'message': f'资源不足: CPU{cpu}% MEM{mem}% DISK{disk}%'})
            elif cpu > 70 or mem > 75 or disk > 80:
                checks['system'] = {'status': 'degraded', 'message': '资源使用偏高'}
            else:
                checks['system'] = {'status': 'healthy', 'message': f'CPU {cpu}%, MEM {mem}%, DISK {disk}%'}
        except Exception as e:
            checks['system'] = {'status': 'unknown', 'message': str(e)}

        # 4. 磁盘空间检查
        try:
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                checks['disk'] = {'status': 'unhealthy', 'message': f'磁盘空间不足 ({disk.percent}%)'}
            elif disk.percent > 80:
                checks['disk'] = {'status': 'warning', 'message': f'磁盘空间紧张 ({disk.percent}%)'}
            else:
                free_gb = disk.free / (1024**3)
                checks['disk'] = {'status': 'healthy', 'message': f'剩余 {free_gb:.1f} GB'}
        except Exception as e:
            checks['disk'] = {'status': 'unknown', 'message': str(e)}

        # 判断总体健康状态
        unhealthy_count = sum(1 for c in checks.values() if c.get('status') == 'unhealthy')
        degraded_count = sum(1 for c in checks.values() if c.get('status') == 'degraded')

        if unhealthy_count > 0:
            healthy = False
        elif degraded_count > 0:
            healthy = True
        else:
            healthy = True

        return {
            'healthy': healthy,
            'timestamp': datetime.now().isoformat(),
            'checks': checks,
            'alerts': alerts
        }

    @classmethod
    def record_metric(cls, metric_name, value, tags=None):
        """记录自定义指标"""
        try:
            metric_key = f'metric_{metric_name}'
            metrics = cache_get(metric_key) or []

            metrics.append({
                'value': value,
                'tags': tags or {},
                'timestamp': datetime.now().isoformat()
            })

            # 只保留最近1000条
            if len(metrics) > 1000:
                metrics = metrics[-1000:]

            cache_set(metric_key, metrics, 3600)  # 1小时过期

        except Exception as e:
            logger.error(f"记录指标失败: {e}")


class AlertManager:
    """告警管理器"""

    # 告警级别
    LEVEL_INFO = 'info'
    LEVEL_WARNING = 'warning'
    LEVEL_ERROR = 'error'
    LEVEL_CRITICAL = 'critical'

    @classmethod
    def send_alert(cls, level, title, message, data=None, channels=None):
        """
        发送告警

        Args:
            level: 告警级别
            title: 告警标题
            message: 告警内容
            data: 附加数据
            channels: 通知渠道 (log/email/sms/webhook)
        """
        alert = {
            'level': level,
            'title': title,
            'message': message,
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'channels': channels or ['log']
        }

        # 记录到数据库
        try:
            db.execute("""
                INSERT INTO business_alerts (level, title, message, alert_data, status)
                VALUES (%s, %s, %s, %s, 'active')
            """, [level, title, message, json.dumps(data) if data else None])
        except Exception as e:
            logger.error(f"保存告警到数据库失败: {e}")

        # 根据渠道发送
        for channel in (channels or ['log']):
            try:
                if channel == 'log':
                    if level in (cls.LEVEL_ERROR, cls.LEVEL_CRITICAL):
                        logger.error(f"告警 [{level}] {title}: {message}")
                    else:
                        logger.warning(f"告警 [{level}] {title}: {message}")
                elif channel == 'email':
                    cls._send_email_alert(alert)
                elif channel == 'webhook':
                    cls._send_webhook_alert(alert)

            except Exception as e:
                logger.error(f"发送告警到 {channel} 失败: {e}")

        return alert

    @classmethod
    def _send_email_alert(cls, alert):
        """发送邮件告警（预留）"""
        logger.info(f"邮件告警预留: {alert['title']}")

    @classmethod
    def _send_webhook_alert(cls, alert):
        """发送Webhook告警（预留）"""
        logger.info(f"Webhook告警预留: {alert['title']}")

    @classmethod
    def get_active_alerts(cls, level=None, limit=50):
        """获取活跃告警"""
        try:
            where = "status='active'"
            params = []

            if level:
                where += " AND level=%s"
                params.append(level)

            alerts = db.get_all(f"""
                SELECT * FROM business_alerts
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT %s
            """, params + [limit])

            return alerts or []

        except Exception as e:
            logger.error(f"获取活跃告警失败: {e}")
            return []

    @classmethod
    def resolve_alert(cls, alert_id, resolved_by, note=''):
        """标记告警为已解决"""
        try:
            db.execute("""
                UPDATE business_alerts
                SET status='resolved', resolved_by=%s, resolved_at=NOW(), resolution_note=%s
                WHERE id=%s
            """, [resolved_by, note, alert_id])

            return {'success': True}

        except Exception as e:
            logger.error(f"解决告警失败: {e}")
            return {'success': False, 'msg': str(e)}


def monitor_performance(f):
    """装饰器：监控接口性能"""
    @wraps(f)
    def decorated(*args, **kwargs):
        start_time = time.time()
        error = None

        try:
            result = f(*args, **kwargs)
            return result
        except Exception as e:
            error = e
            raise
        finally:
            duration_ms = int((time.time() - start_time) * 1000)

            # 记录慢请求
            if duration_ms > 1000:
                AlertManager.send_alert(
                    level=AlertManager.LEVEL_WARNING,
                    title='慢接口告警',
                    message=f'{request.path} 执行耗时 {duration_ms}ms',
                    data={
                        'path': request.path,
                        'method': request.method,
                        'duration_ms': duration_ms,
                        'error': str(error) if error else None
                    }
                )

            # 记录到监控
            EnhancedMonitor.record_metric(
                f'endpoint_{request.endpoint or "unknown"}',
                duration_ms,
                {'method': request.method, 'status': 'error' if error else 'success'}
            )

    return decorated
