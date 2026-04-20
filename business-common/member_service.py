"""
V32.0 会员服务模块 → V35.0增强
提供统一的会员业务逻辑封装

功能清单:
- 会员注册/登录
- 会员信息管理
- 积分操作 (增减/查询/日志)
- 成长值计算
- 会员等级管理
- 签到打卡
- 会员画像

V35.0增强:
- 密码安全升级（bcrypt哈希 + 多版本兼容）
- 账户锁定机制（登录失败5次锁定30分钟）
- Token安全增强（JWT + Redis存储）

依赖:
- auth: 认证模块
- growth_service: 成长值服务
- points_scheduler: 积分调度服务
"""

import logging
import hashlib
import random
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from . import db
from .service_base import BaseService
from .decorators import require_login
from .fid_utils import generate_fid, generate_business_fid  # V47.0: FID生成工具

logger = logging.getLogger(__name__)

# V35.0新增：密码配置
PASSWORD_VERSION_CURRENT = 2  # 当前使用的密码版本：1-SHA256(旧), 2-bcrypt(新)
PASSWORD_ROUNDS = 12  # bcrypt rounds参数

# V35.0新增：账户安全配置
LOGIN_MAX_FAILURES = 5  # 最大登录失败次数
LOGIN_LOCK_DURATION = 30  # 锁定时长（分钟）


class MemberService(BaseService):
    """会员服务"""

    SERVICE_NAME = 'MemberService'

    # 签到积分配置
    CHECKIN_POINTS = 5
    CHECKIN_STREAK_BONUS = [0, 2, 3, 5, 8, 13]  # 连续1-6天额外奖励
    MAX_STREAK_BONUS = 13

    # 积分过期配置
    POINTS_EXPIRE_DAYS = 365  # 积分1年后过期

    def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        base = super().health_check()
        try:
            result = db.get_one("SELECT COUNT(*) as cnt FROM business_members LIMIT 1")
            base['db_status'] = 'connected'
            base['member_count'] = result.get('cnt', 0) if result else 0
        except Exception as e:
            base['db_status'] = 'error'
            base['error'] = str(e)
        return base

    # ============ 会员注册/登录 ============

    def register(self, phone: str, password: str = None,
                 nickname: str = None, ec_id: int = 1,
                 project_id: int = 1, **kwargs) -> Dict[str, Any]:
        """
        会员注册 - V35.0增强

        Args:
            phone: 手机号
            password: 密码(可选)
            nickname: 昵称(可选)
            ec_id: 企业ID
            project_id: 项目ID
            **kwargs: 其他参数

        Returns:
            Dict: {"success": True, "user_id": xxx, "token": "xxx"}
        """
        try:
            # 1. 检查手机号是否已注册
            existing = self.get_member_by_phone(phone, ec_id, project_id)
            if existing:
                return {'success': False, 'msg': '手机号已注册'}

            # V35.0新增：密码强度验证
            if password:
                strength_result = self._validate_password_strength(password)
                if not strength_result['valid']:
                    return {'success': False, 'msg': strength_result['msg']}

            # 2. 生成用户ID
            user_id = self._generate_user_id()

            # 3. 加密密码 - V35.0使用bcrypt
            hashed_password = self._hash_password(password, PASSWORD_VERSION_CURRENT) if password else None

            # 4. 创建会员记录 - V35.0新增password_version字段, V47.0新增fid字段
            now = datetime.now()
            member_fid = generate_business_fid('member')  # V47.0: 生成FID主键
            sql = """
                INSERT INTO business_members (
                    fid, user_id, phone, nickname, password, password_version,
                    ec_id, project_id, member_level, member_grade,
                    points, total_points, balance, growth_value,
                    created_at, updated_at,
                    last_checkin_date, checkin_streak
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # 默认初始积分
            initial_points = 100

            params = [
                member_fid, user_id, phone, nickname or f'用户{phone[-4:]}', hashed_password, PASSWORD_VERSION_CURRENT,
                ec_id, project_id, 1, '普通会员',
                initial_points, initial_points, 0, 0,
                now, now, None, 0
            ]

            db.execute(sql, params)

            # 5. 记录积分日志
            self.add_points_log(
                user_id=user_id,
                points=initial_points,
                change_type='register',
                change_reason='新用户注册奖励',
                ec_id=ec_id,
                project_id=project_id
            )

            # 6. 生成Token - V35.0使用JWT
            token = self._generate_token(user_id)

            logger.info(f"[MemberService] 会员注册成功: user_id={user_id}, phone={phone}, password_version={PASSWORD_VERSION_CURRENT}")

            return {
                'success': True,
                'user_id': user_id,
                'token': token,
                'phone': phone,
                'initial_points': initial_points,
                'msg': '注册成功'
            }

        except Exception as e:
            logger.error(f"[MemberService] 会员注册失败: {e}")
            return {'success': False, 'msg': f'注册失败: {str(e)}'}

    # ============ V35.0 密码强度验证 ============

    def _validate_password_strength(self, password: str) -> Dict[str, Any]:
        """
        验证密码强度 - V35.0新增
        
        要求：
        - 长度至少8位
        - 包含字母和数字
        - 不能是常见弱密码
        
        Args:
            password: 明文密码
        
        Returns:
            Dict: {"valid": bool, "msg": str}
        """
        if not password:
            return {'valid': False, 'msg': '密码不能为空'}
        
        # 检查长度
        if len(password) < 8:
            return {'valid': False, 'msg': '密码长度至少8位'}
        
        if len(password) > 32:
            return {'valid': False, 'msg': '密码长度不能超过32位'}
        
        # 检查是否包含字母
        has_letter = any(c.isalpha() for c in password)
        if not has_letter:
            return {'valid': False, 'msg': '密码必须包含字母'}
        
        # 检查是否包含数字
        has_digit = any(c.isdigit() for c in password)
        if not has_digit:
            return {'valid': False, 'msg': '密码必须包含数字'}
        
        # 检查常见弱密码
        weak_passwords = [
            '12345678', 'password', 'qwerty', 'abc123', '11111111',
            '123456789', 'password1', '1234567', '123123', '00000000'
        ]
        if password.lower() in weak_passwords:
            return {'valid': False, 'msg': '密码强度太弱，请使用更复杂的密码'}
        
        return {'valid': True, 'msg': '密码强度合格'}

    # ============ V35.0 密码重置 ============

    def reset_password(self, user_id: int, old_password: str, 
                       new_password: str) -> Dict[str, Any]:
        """
        重置密码 - V35.0新增
        
        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
        
        Returns:
            Dict: 操作结果
        """
        try:
            member = self.get_member(user_id)
            if not member:
                return {'success': False, 'msg': '用户不存在'}
            
            # 验证旧密码
            if not self._verify_password(old_password, member.get('password', '')):
                return {'success': False, 'msg': '旧密码错误'}
            
            # 验证新密码强度
            strength_result = self._validate_password_strength(new_password)
            if not strength_result['valid']:
                return {'success': False, 'msg': strength_result['msg']}
            
            # 不能与旧密码相同
            if old_password == new_password:
                return {'success': False, 'msg': '新密码不能与旧密码相同'}
            
            # 更新密码
            hashed = self._hash_password(new_password, PASSWORD_VERSION_CURRENT)
            db.execute("""
                UPDATE business_members 
                SET password=%s, password_version=%s, updated_at=NOW()
                WHERE user_id=%s
            """, [hashed, PASSWORD_VERSION_CURRENT, user_id])
            
            logger.info(f"[MemberService] 密码重置成功: user_id={user_id}")
            return {'success': True, 'msg': '密码修改成功'}
            
        except Exception as e:
            logger.error(f"[MemberService] 密码重置失败: {e}")
            return {'success': False, 'msg': f'密码重置失败: {str(e)}'}

    def force_reset_password(self, user_id: int, new_password: str) -> Dict[str, Any]:
        """
        强制重置密码（管理员用） - V35.0新增
        
        Args:
            user_id: 用户ID
            new_password: 新密码
        
        Returns:
            Dict: 操作结果
        """
        try:
            member = self.get_member(user_id)
            if not member:
                return {'success': False, 'msg': '用户不存在'}
            
            # 验证新密码强度
            strength_result = self._validate_password_strength(new_password)
            if not strength_result['valid']:
                return {'success': False, 'msg': strength_result['msg']}
            
            # 更新密码并重置登录失败计数
            hashed = self._hash_password(new_password, PASSWORD_VERSION_CURRENT)
            db.execute("""
                UPDATE business_members 
                SET password=%s, password_version=%s, 
                    login_fail_count=0, lock_until=NULL,
                    updated_at=NOW()
                WHERE user_id=%s
            """, [hashed, PASSWORD_VERSION_CURRENT, user_id])
            
            logger.info(f"[MemberService] 管理员重置密码成功: user_id={user_id}")
            return {'success': True, 'msg': '密码已重置'}
            
        except Exception as e:
            logger.error(f"[MemberService] 密码重置失败: {e}")
            return {'success': False, 'msg': f'密码重置失败: {str(e)}'}

    def login(self, phone: str, password: str = None,
              ec_id: int = 1, project_id: int = 1,
              login_type: str = 'password') -> Dict[str, Any]:
        """
        会员登录 - V35.0增强

        Args:
            phone: 手机号
            password: 密码
            ec_id: 企业ID
            project_id: 项目ID
            login_type: 登录方式 (password/sms/wechat)

        Returns:
            Dict: {"success": True, "user_id": xxx, "token": "xxx"}
        """
        try:
            # 1. 查询会员
            member = self.get_member_by_phone(phone, ec_id, project_id)
            if not member:
                return {'success': False, 'msg': '用户不存在'}

            # V35.0新增：检查账户是否被锁定
            is_locked, remaining = self._check_account_locked(member)
            if is_locked:
                minutes = remaining // 60
                seconds = remaining % 60
                return {
                    'success': False,
                    'msg': f'账户已锁定，请在{minutes}分{seconds}秒后重试',
                    'locked': True,
                    'remaining_seconds': remaining
                }

            # 2. 验证密码
            if login_type == 'password' and password:
                # V35.0使用新的密码验证方法
                if not self._verify_password(password, member.get('password', '')):
                    # V35.0新增：处理登录失败
                    self._handle_login_failure(member['user_id'])
                    logger.warning(f"[MemberService] 密码错误: user_id={member['user_id']}")
                    return {'success': False, 'msg': '密码错误'}

            # V35.0新增：登录成功，重置失败计数
            self._reset_login_failures(member['user_id'])

            # 3. 生成Token（V35.0使用JWT）
            token = self._generate_token(member['user_id'])

            # 4. 更新登录信息
            self._update_login_info(member['user_id'])

            # 5. 返回会员信息
            member_info = self.get_member_info(member['user_id'])

            logger.info(f"[MemberService] 会员登录成功: user_id={member['user_id']}")

            return {
                'success': True,
                'user_id': member['user_id'],
                'token': token,
                'member': member_info,
                'msg': '登录成功'
            }

        except Exception as e:
            logger.error(f"[MemberService] 会员登录失败: {e}")
            return {'success': False, 'msg': f'登录失败: {str(e)}'}

    # ============ V35.0 密码安全增强 ============

    def _hash_password(self, password: str, version: int = None) -> str:
        """
        密码哈希 - V35.0支持多版本
        
        Args:
            password: 明文密码
            version: 密码版本 (1=SHA256旧版, 2=bcrypt新版)
        
        Returns:
            str: 哈希后的密码
        """
        if version is None:
            version = PASSWORD_VERSION_CURRENT
        
        if version == 1:
            # 兼容旧版SHA256
            return hashlib.sha256(password.encode()).hexdigest()
        elif version == 2:
            # V35.0 bcrypt哈希
            try:
                import bcrypt
                salt = bcrypt.gensalt(rounds=PASSWORD_ROUNDS)
                hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
                return hashed.decode('utf-8')
            except ImportError:
                logger.warning("bcrypt未安装，降级到SHA256")
                return hashlib.sha256(password.encode()).hexdigest()
        else:
            raise ValueError(f"不支持的密码版本: {version}")

    def _verify_password(self, password: str, hashed: str) -> bool:
        """
        验证密码 - V35.0支持多版本验证
        
        Args:
            password: 明文密码
            hashed: 数据库中存储的哈希值
        
        Returns:
            bool: 验证是否通过
        """
        if not hashed:
            return False
        
        # bcrypt格式以$2开头
        if hashed.startswith('$2'):
            try:
                import bcrypt
                return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
            except Exception as e:
                logger.error(f"bcrypt验证失败: {e}")
                return False
        else:
            # 兼容旧SHA256
            return hashed == hashlib.sha256(password.encode()).hexdigest()

    def _check_account_locked(self, member: dict) -> tuple:
        """
        检查账户是否被锁定 - V35.0
        
        Args:
            member: 会员信息字典
        
        Returns:
            tuple: (是否锁定, 剩余锁定时间秒数)
        """
        lock_until = member.get('lock_until')
        if lock_until:
            if isinstance(lock_until, str):
                lock_until = datetime.strptime(lock_until, '%Y-%m-%d %H:%M:%S')
            
            if lock_until and lock_until > datetime.now():
                remaining = int((lock_until - datetime.now()).total_seconds())
                return True, remaining
        return False, 0

    def _handle_login_failure(self, user_id: int):
        """
        处理登录失败 - V35.0
        累计失败次数，达到阈值后锁定账户
        """
        member = self.get_member(user_id)
        if not member:
            return
        
        fail_count = (member.get('login_fail_count') or 0) + 1
        lock_until = None
        
        if fail_count >= LOGIN_MAX_FAILURES:
            lock_until = datetime.now() + timedelta(minutes=LOGIN_LOCK_DURATION)
            logger.warning(f"账户被锁定: user_id={user_id}, 失败次数={fail_count}")
        
        sql = """
            UPDATE business_members 
            SET login_fail_count = %s, lock_until = %s
            WHERE user_id = %s
        """
        db.execute(sql, [fail_count, lock_until, user_id])

    def _reset_login_failures(self, user_id: int):
        """
        重置登录失败计数 - V35.0
        登录成功后调用
        """
        sql = """
            UPDATE business_members 
            SET login_fail_count = 0, lock_until = NULL
            WHERE user_id = %s
        """
        db.execute(sql, [user_id])

    def _generate_user_id(self) -> int:
        """生成用户ID"""
        import time
        return int(time.time() * 1000) + random.randint(1, 999)

    # ============ V35.0 Token安全增强 ============

    def _generate_token(self, user_id: int, token_type: str = 'access') -> str:
        """
        生成访问令牌 - V35.0 JWT + Redis
        
        Args:
            user_id: 用户ID
            token_type: Token类型 (access/refresh)
        
        Returns:
            str: JWT Token
        """
        try:
            import jwt
            from datetime import datetime, timedelta
            
            jwt_secret = os.environ.get('JWT_SECRET', 'wojiayun-secret-key-v35')
            
            now = datetime.utcnow()
            if token_type == 'access':
                exp = now + timedelta(hours=2)  # 2小时有效期
            else:
                exp = now + timedelta(days=7)  # 7天有效期
            
            payload = {
                'user_id': user_id,
                'type': token_type,
                'iat': now,
                'exp': exp,
                'jti': f"{user_id}_{int(now.timestamp())}_{random.randint(1000, 9999)}"  # Token唯一ID
            }
            
            token = jwt.encode(payload, jwt_secret, algorithm='HS256')
            
            # 存储到Redis（用于主动失效）
            try:
                import redis
                redis_client = redis.Redis(
                    host=os.environ.get('REDIS_HOST', 'localhost'),
                    port=int(os.environ.get('REDIS_PORT', 6379)),
                    db=0,
                    decode_responses=True
                )
                ttl = int((exp - now).total_seconds())
                redis_client.setex(f"token:{payload['jti']}", ttl, str(user_id))
            except Exception as e:
                logger.warning(f"Token存储到Redis失败（非致命）: {e}")
            
            return token
            
        except ImportError:
            # JWT未安装，降级到简单Token
            logger.warning("PyJWT未安装，使用降级Token方案")
            import time
            raw = f"{user_id}_{token_type}_{time.time()}_{random.random()}"
            return hashlib.sha256(raw.encode()).hexdigest()

    def _verify_token(self, token: str) -> Optional[dict]:
        """
        验证Token - V35.0
        
        Args:
            token: JWT Token
        
        Returns:
            dict: Token payload，验证失败返回None
        """
        try:
            import jwt
            jwt_secret = os.environ.get('JWT_SECRET', 'wojiayun-secret-key-v35')
            
            payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
            
            # 检查Redis中是否存在（已主动失效的Token会被删除）
            try:
                import redis
                redis_client = redis.Redis(
                    host=os.environ.get('REDIS_HOST', 'localhost'),
                    port=int(os.environ.get('REDIS_PORT', 6379)),
                    db=0,
                    decode_responses=True
                )
                jti = payload.get('jti')
                if jti and not redis_client.exists(f"token:{jti}"):
                    logger.info(f"Token已失效: jti={jti}")
                    return None
            except Exception as e:
                logger.warning(f"Redis检查Token失败（非致命）: {e}")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.info("Token已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token无效: {e}")
            return None
        except ImportError:
            logger.warning("PyJWT未安装，跳过Token验证")
            return None

    def _revoke_token(self, token: str) -> bool:
        """
        主动失效Token - V35.0
        
        Args:
            token: JWT Token
        
        Returns:
            bool: 是否成功失效
        """
        try:
            import jwt
            jwt_secret = os.environ.get('JWT_SECRET', 'wojiayun-secret-key-v35')
            
            payload = jwt.decode(token, jwt_secret, algorithms=['HS256'], options={"verify_exp": False})
            jti = payload.get('jti')
            
            if jti:
                try:
                    import redis
                    redis_client = redis.Redis(
                        host=os.environ.get('REDIS_HOST', 'localhost'),
                        port=int(os.environ.get('REDIS_PORT', 6379)),
                        db=0
                    )
                    redis_client.delete(f"token:{jti}")
                except Exception as e:
                    logger.warning(f"Redis删除Token失败: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Token失效失败: {e}")
            return False

    def _update_login_info(self, user_id: int):
        """更新登录信息"""
        sql = """
            UPDATE business_members
            SET last_login_at = NOW(), login_count = login_count + 1
            WHERE user_id = %s
        """
        db.execute(sql, [user_id])

    # ============ 会员查询 ============

    def get_member_by_phone(self, phone: str, ec_id: int = None,
                           project_id: int = None) -> Optional[Dict]:
        """根据手机号查询会员"""
        sql = "SELECT * FROM business_members WHERE phone = %s"
        params = [phone]

        if ec_id:
            sql += " AND ec_id = %s"
            params.append(ec_id)
        if project_id:
            sql += " AND project_id = %s"
            params.append(project_id)

        sql += " LIMIT 1"
        return db.get_one(sql, params)

    def get_member(self, user_id: int, ec_id: int = None,
                  project_id: int = None) -> Optional[Dict]:
        """根据用户ID查询会员"""
        sql = "SELECT * FROM business_members WHERE user_id = %s"
        params = [user_id]

        if ec_id:
            sql += " AND ec_id = %s"
            params.append(ec_id)
        if project_id:
            sql += " AND project_id = %s"
            params.append(project_id)

        sql += " LIMIT 1"
        return db.get_one(sql, params)

    def get_member_info(self, user_id: int) -> Dict[str, Any]:
        """获取会员详细信息(含等级权益)"""
        member = self.get_member(user_id)
        if not member:
            return None

        # 获取等级信息
        level_sql = "SELECT * FROM business_member_levels WHERE level_id = %s"
        level = db.get_one(level_sql, [member.get('member_level', 1)])

        # 计算成长值进度
        next_level_sql = """
            SELECT * FROM business_member_levels
            WHERE level_id > %s
            ORDER BY level_id ASC LIMIT 1
        """
        next_level = db.get_one(next_level_sql, [member.get('member_level', 1)])

        current_growth = member.get('growth_value', 0)
        current_threshold = level.get('min_growth', 0) if level else 0
        next_threshold = next_level.get('min_growth', current_threshold + 1000) if next_level else current_threshold + 1000

        progress = 0
        if next_threshold > current_threshold:
            progress = min(100, int((current_growth - current_threshold) / (next_threshold - current_threshold) * 100))

        return {
            'user_id': member['user_id'],
            'phone': member['phone'],
            'nickname': member.get('nickname'),
            'avatar': member.get('avatar'),
            'member_level': member.get('member_level', 1),
            'member_grade': member.get('member_grade', '普通会员'),
            'points': member.get('points', 0),
            'total_points': member.get('total_points', 0),
            'balance': member.get('balance', 0),
            'growth_value': current_growth,
            'growth_progress': progress,
            'level_name': level.get('level_name', '普通会员') if level else '普通会员',
            'level_benefits': level.get('benefits', '').split(',') if level and level.get('benefits') else [],
            'next_level': next_level.get('level_name') if next_level else None,
            'next_growth': next_threshold - current_growth if next_level else 0,
            'checkin_streak': member.get('checkin_streak', 0),
            'total_consume': member.get('total_consume', 0),
            'created_at': member.get('created_at'),
            'last_login_at': member.get('last_login_at'),
        }

    def get_members(self, ec_id: int, project_id: int = None,
                   level: int = None, keyword: str = None,
                   page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """查询会员列表"""
        conditions = ["ec_id = %s"]
        params = [ec_id]

        if project_id:
            conditions.append("project_id = %s")
            params.append(project_id)

        if level:
            conditions.append("member_level = %s")
            params.append(level)

        if keyword:
            conditions.append("(phone LIKE %s OR nickname LIKE %s)")
            params.extend([f'%{keyword}%', f'%{keyword}%'])

        where = " AND ".join(conditions)

        # 统计总数
        count_sql = f"SELECT COUNT(*) as total FROM business_members WHERE {where}"
        count_result = db.get_one(count_sql, params)
        total = count_result.get('total', 0) if count_result else 0

        # 分页查询
        offset = (page - 1) * page_size
        query_sql = f"""
            SELECT * FROM business_members WHERE {where}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        members = db.get_all(query_sql, params) or []

        return {
            'members': members,
            'total': total,
            'page': page,
            'page_size': page_size,
            'pages': (total + page_size - 1) // page_size
        }

    # ============ 积分操作 ============

    def add_points(self, user_id: int, points: int, change_type: str,
                  change_reason: str, ec_id: int = 1,
                  project_id: int = 1, **kwargs) -> Dict[str, Any]:
        """增加会员积分"""
        if points <= 0:
            return {'success': False, 'msg': '积分必须为正数'}

        try:
            sql = """
                UPDATE business_members
                SET points = points + %s, total_points = total_points + %s, updated_at = NOW()
                WHERE user_id = %s
            """
            affected = db.execute(sql, [points, points, user_id])

            if affected == 0:
                return {'success': False, 'msg': '用户不存在'}

            member = self.get_member(user_id, ec_id, project_id)
            new_points = member.get('points', 0) if member else 0

            self.add_points_log(
                user_id=user_id,
                points=points,
                change_type=change_type,
                change_reason=change_reason,
                balance_before=new_points - points,
                balance_after=new_points,
                ec_id=ec_id,
                project_id=project_id,
                **kwargs
            )

            logger.info(f"[MemberService] 增加积分: user_id={user_id}, points={points}")

            return {'success': True, 'new_points': new_points}

        except Exception as e:
            logger.error(f"[MemberService] 增加积分失败: {e}")
            return {'success': False, 'msg': str(e)}

    def deduct_points(self, user_id: int, points: int, change_type: str,
                    change_reason: str, ec_id: int = 1,
                    project_id: int = 1, **kwargs) -> Dict[str, Any]:
        """扣减会员积分"""
        if points <= 0:
            return {'success': False, 'msg': '积分必须为正数'}

        try:
            member = self.get_member(user_id, ec_id, project_id)
            if not member:
                return {'success': False, 'msg': '用户不存在'}

            current_points = member.get('points', 0)
            if current_points < points:
                return {'success': False, 'msg': f'积分不足(当前:{current_points})'}

            sql = """
                UPDATE business_members
                SET points = points - %s, updated_at = NOW()
                WHERE user_id = %s
            """
            db.execute(sql, [points, user_id])

            member = self.get_member(user_id, ec_id, project_id)
            new_points = member.get('points', 0) if member else 0

            self.add_points_log(
                user_id=user_id,
                points=-points,
                change_type=change_type,
                change_reason=change_reason,
                balance_before=current_points,
                balance_after=new_points,
                ec_id=ec_id,
                project_id=project_id,
                **kwargs
            )

            logger.info(f"[MemberService] 扣减积分: user_id={user_id}, points={points}")

            return {'success': True, 'new_points': new_points}

        except Exception as e:
            logger.error(f"[MemberService] 扣减积分失败: {e}")
            return {'success': False, 'msg': str(e)}

    def add_points_log(self, user_id: int, points: int, change_type: str,
                      change_reason: str, balance_before: int = None,
                      balance_after: int = None, ec_id: int = 1,
                      project_id: int = 1, **kwargs) -> Dict[str, Any]:
        """记录积分变动日志 - V47.0: 添加fid字段"""
        try:
            log_fid = generate_fid()  # V47.0: 生成日志FID
            sql = """
                INSERT INTO business_points_log (
                    fid, user_id, points, change_type, change_reason,
                    balance_before, balance_after, order_no,
                    ec_id, project_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """

            params = [
                log_fid, user_id, points, change_type, change_reason,
                balance_before, balance_after, kwargs.get('order_no'),
                ec_id, project_id
            ]

            db.execute(sql, params)
            return {'success': True}

        except Exception as e:
            logger.error(f"[MemberService] 记录积分日志失败: {e}")
            return {'success': False, 'msg': str(e)}

    def get_points_history(self, user_id: int, page: int = 1,
                          page_size: int = 20) -> Dict[str, Any]:
        """获取积分变动历史"""
        count_sql = "SELECT COUNT(*) as total FROM business_points_log WHERE user_id = %s"
        count_result = db.get_one(count_sql, [user_id])
        total = count_result.get('total', 0) if count_result else 0

        offset = (page - 1) * page_size
        sql = """
            SELECT * FROM business_points_log
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        logs = db.get_all(sql, [user_id, page_size, offset]) or []

        for log in logs:
            log['type'] = log['change_type']

        return {
            'logs': logs,
            'total': total,
            'page': page,
            'page_size': page_size
        }

    # ============ 签到打卡 ============

    def checkin(self, user_id: int, ec_id: int = 1,
               project_id: int = 1) -> Dict[str, Any]:
        """会员签到"""
        try:
            member = self.get_member(user_id, ec_id, project_id)
            if not member:
                return {'success': False, 'msg': '用户不存在'}

            today = datetime.now().date()
            last_checkin = member.get('last_checkin_date')

            if last_checkin:
                last_checkin_date = last_checkin.date() if isinstance(last_checkin, datetime) else last_checkin
                if str(last_checkin_date) == str(today):
                    return {'success': False, 'msg': '今日已签到', 'already_checkin': True}

            current_streak = member.get('checkin_streak', 0)
            if last_checkin:
                last_checkin_date = last_checkin.date() if isinstance(last_checkin, datetime) else last_checkin
                yesterday = today - timedelta(days=1)
                if str(last_checkin_date) == str(yesterday):
                    current_streak += 1
                else:
                    current_streak = 1
            else:
                current_streak = 1

            base_points = self.CHECKIN_POINTS
            bonus_index = min(current_streak, len(self.CHECKIN_STREAK_BONUS)) - 1
            streak_bonus = self.CHECKIN_STREAK_BONUS[bonus_index] if bonus_index >= 0 else 0
            total_points = base_points + streak_bonus

            sql = """
                UPDATE business_members
                SET last_checkin_date = %s, checkin_streak = %s, updated_at = NOW()
                WHERE user_id = %s
            """
            db.execute(sql, [today, current_streak, user_id])

            self.add_points(
                user_id=user_id,
                points=total_points,
                change_type='checkin',
                change_reason=f'签到获得(连续签到{current_streak}天)',
                ec_id=ec_id,
                project_id=project_id
            )

            logger.info(f"[MemberService] 签到成功: user_id={user_id}, points={total_points}")

            return {
                'success': True,
                'points': total_points,
                'streak': current_streak,
                'bonus': streak_bonus,
                'msg': f'签到成功，获得{total_points}积分'
            }

        except Exception as e:
            logger.error(f"[MemberService] 签到失败: {e}")
            return {'success': False, 'msg': str(e)}

    def get_checkin_status(self, user_id: int) -> Dict[str, Any]:
        """获取签到状态"""
        member = self.get_member(user_id)
        if not member:
            return {'success': False, 'msg': '用户不存在'}

        today = datetime.now().date()
        last_checkin = member.get('last_checkin_date')

        already_checkin = False
        if last_checkin:
            last_checkin_date = last_checkin.date() if isinstance(last_checkin, datetime) else last_checkin
            already_checkin = str(last_checkin_date) == str(today)

        return {
            'success': True,
            'already_checkin': already_checkin,
            'current_streak': member.get('checkin_streak', 0),
            'next_bonus': self.CHECKIN_STREAK_BONUS[min(member.get('checkin_streak', 0), 5)]
        }

    # ============ 会员等级 ============

    def update_member_level(self, user_id: int) -> Dict[str, Any]:
        """根据成长值更新会员等级"""
        try:
            member = self.get_member(user_id)
            if not member:
                return {'success': False, 'msg': '用户不存在'}

            growth_value = member.get('growth_value', 0)

            sql = """
                SELECT * FROM business_member_levels
                WHERE min_growth <= %s
                ORDER BY level_id DESC LIMIT 1
            """
            level = db.get_one(sql, [growth_value])

            if level:
                new_level = level['level_id']
                new_grade = level['level_name']

                if new_level != member.get('member_level'):
                    update_sql = """
                        UPDATE business_members
                        SET member_level = %s, member_grade = %s, updated_at = NOW()
                        WHERE user_id = %s
                    """
                    db.execute(update_sql, [new_level, new_grade, user_id])

                    logger.info(f"[MemberService] 会员升级: user_id={user_id}, level={new_level}")

                    return {
                        'success': True,
                        'upgraded': True,
                        'new_level': new_level,
                        'new_grade': new_grade,
                        'msg': f'恭喜升级为{new_grade}'
                    }

            return {'success': True, 'upgraded': False}

        except Exception as e:
            logger.error(f"[MemberService] 更新会员等级失败: {e}")
            return {'success': False, 'msg': str(e)}

    def add_growth(self, user_id: int, growth: int,
                  reason: str, ec_id: int = 1,
                  project_id: int = 1) -> Dict[str, Any]:
        """增加成长值"""
        if growth <= 0:
            return {'success': False, 'msg': '成长值必须为正数'}

        try:
            sql = """
                UPDATE business_members
                SET growth_value = growth_value + %s, updated_at = NOW()
                WHERE user_id = %s
            """
            db.execute(sql, [growth, user_id])

            self.update_member_level(user_id)

            member = self.get_member(user_id, ec_id, project_id)

            return {
                'success': True,
                'new_growth': member.get('growth_value', 0) if member else growth,
                'msg': f'成长值+{growth}'
            }

        except Exception as e:
            logger.error(f"[MemberService] 增加成长值失败: {e}")
            return {'success': False, 'msg': str(e)}


# 单例实例
member_service = MemberService()
