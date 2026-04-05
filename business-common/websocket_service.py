"""
WebSocket实时消息推送服务 V14.0
支持: 实时通知推送、在线状态管理、心跳检测

使用方式:
    1. 在Flask app中初始化:
        from business_common.websocket_service import init_websocket, socketio
        init_websocket(app)

    2. 在业务代码中推送消息:
        from business_common.websocket_service import push_notification
        push_notification(user_id, title, content)

    3. 环境变量配置:
        REDIS_URL=redis://localhost:6379/0  # WebSocket消息队列（推荐）

依赖:
    pip install flask-socketio
    # 如需WebSocket消息队列（多进程）:
    pip install redis
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

# ============ 延迟导入，避免在不需要时不安装flask-socketio ============

_socketio = None
_redis_manager = None
_initialized = False


def init_websocket(app, cors_allowed_origins='*'):
    """
    初始化WebSocket服务

    Args:
        app: Flask应用实例
        cors_allowed_origins: 允许的跨域来源
    """
    global _socketio, _initialized, _redis_manager

    if _initialized:
        return _socketio

    try:
        from flask_socketio import SocketIO

        # 消息队列配置（多进程部署时需要）
        message_queue = None
        if os.environ.get('REDIS_URL'):
            message_queue = os.environ['REDIS_URL']
            logger.info(f"WebSocket使用Redis消息队列")

        _socketio = SocketIO(
            app,
            cors_allowed_origins=cors_allowed_origins,
            message_queue=message_queue,
            async_mode='threading',
            ping_timeout=30,
            ping_interval=25,
        )

        # 注册事件处理器
        _register_handlers(_socketio)

        _initialized = True
        logger.info("WebSocket服务初始化成功")
        return _socketio

    except ImportError:
        logger.warning("flask-socketio未安装，WebSocket功能不可用。请执行: pip install flask-socketio")
        return None
    except Exception as e:
        logger.error(f"WebSocket初始化失败: {e}")
        return None


def _register_handlers(socketio):
    """注册Socket.IO事件处理器"""

    # 在线用户存储 {sid: user_id}
    online_users = {}
    # 用户ID到SID的映射 {user_id: set(sids)}
    user_sids = {}

    @socketio.on('connect')
    def handle_connect():
        """客户端连接"""
        from flask import request
        token = request.args.get('access_token') or request.headers.get('Token', '')
        if not token:
            return False  # 拒绝无token连接

        # 验证token
        try:
            isdev = request.args.get('isdev', '0')
            from business_common import auth
            user = auth.verify_user(token, isdev)
            if not user:
                # 尝试员工验证
                user = auth.verify_staff(token, isdev)
            if not user:
                return False  # token无效

            user_id = user.get('user_id')
            online_users[request.sid] = user_id
            if user_id not in user_sids:
                user_sids[user_id] = set()
            user_sids[user_id].add(request.sid)

            # 加入用户专属房间
            from flask_socketio import join_room
            join_room(f"user_{user_id}")

            logger.info(f"WebSocket连接: user={user_id}, sid={request.sid}")
        except Exception as e:
            logger.warning(f"WebSocket连接验证失败: {e}")
            return False

    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开"""
        from flask import request
        sid = request.sid
        user_id = online_users.pop(sid, None)
        if user_id and user_id in user_sids:
            user_sids[user_id].discard(sid)
            if not user_sids[user_id]:
                del user_sids[user_id]
        logger.info(f"WebSocket断开: sid={sid}")

    @socketio.on('ping')
    def handle_ping():
        """心跳检测"""
        return {'pong': True, 'time': __import__('time').time()}

    @socketio.on('subscribe')
    def handle_subscribe(data):
        """订阅特定频道"""
        from flask_socketio import join_room
        channels = data.get('channels', []) if data else []
        for ch in channels:
            join_room(ch)
        return {'success': True, 'channels': channels}

    @socketio.on('unsubscribe')
    def handle_unsubscribe(data):
        """取消订阅频道"""
        from flask_socketio import leave_room
        channels = data.get('channels', []) if data else []
        for ch in channels:
            leave_room(ch)
        return {'success': True, 'channels': channels}

    # 保存引用供外部使用
    _socketio._online_users = online_users
    _socketio._user_sids = user_sids


def push_notification(user_id, title, content, notify_type='system', data=None):
    """
    推送实时通知给指定用户

    Args:
        user_id: 用户ID
        title: 通知标题
        content: 通知内容
        notify_type: 通知类型
        data: 附加数据
    """
    if not _socketio:
        # 降级：通过Redis pub/sub发布（如果有Redis）
        try:
            from business_common.redis_cache_service import CacheService
            CacheService.publish(f'notify_{user_id}', {
                'title': title,
                'content': content,
                'type': notify_type,
                'data': data
            })
        except Exception:
            pass
        return False

    try:
        _socketio.emit('notification', {
            'title': title,
            'content': content,
            'type': notify_type,
            'data': data,
            'timestamp': __import__('time').strftime('%Y-%m-%d %H:%M:%S')
        }, room=f"user_{user_id}")
        return True
    except Exception as e:
        logger.warning(f"推送通知失败: {e}")
        return False


def push_broadcast(title, content, data=None):
    """
    广播消息给所有在线用户

    Args:
        title: 消息标题
        content: 消息内容
        data: 附加数据
    """
    if not _socketio:
        return False

    try:
        _socketio.emit('broadcast', {
            'title': title,
            'content': content,
            'data': data,
            'timestamp': __import__('time').strftime('%Y-%m-%d %H:%M:%S')
        })
        return True
    except Exception as e:
        logger.warning(f"广播消息失败: {e}")
        return False


def get_online_count():
    """获取当前在线用户数"""
    if _socketio and hasattr(_socketio, '_user_sids'):
        return len(_socketio._user_sids)
    return 0


def is_user_online(user_id):
    """检查用户是否在线"""
    if _socketio and hasattr(_socketio, '_user_sids'):
        return user_id in _socketio._user_sids
    return False


def get_socketio():
    """获取SocketIO实例（用于run with socketio）"""
    return _socketio
