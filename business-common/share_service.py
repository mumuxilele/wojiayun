"""
V38.0 分享服务
提供分享记录追踪和分享海报生成

功能：
1. 分享记录追踪（点击、转化）
2. 分享海报生成（Canvas）
3. 分享来源订单绑定
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from . import db
from .service_base import BaseService

logger = logging.getLogger(__name__)


class ShareService(BaseService):
    """分享服务"""
    
    SERVICE_NAME = 'ShareService'
    
    # 分享渠道
    CHANNELS = ['wechat', 'moments', 'friend', 'poster', 'qrcode', 'link']
    
    # 分享类型
    SHARE_TYPES = ['product', 'order', 'coupon', 'page', 'invite']
    
    def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        base = super().health_check()
        try:
            result = db.get_one("SELECT COUNT(*) as cnt FROM business_share_logs")
            base['total_shares'] = result.get('cnt', 0) if result else 0
        except Exception as e:
            base['db_status'] = 'error'
            base['error'] = str(e)
        return base
    
    # ============ 分享记录 ============
    
    def record_share(self, user_id: int, share_type: str, target_id: int,
                    target_title: str = None, channel: str = 'link',
                    ec_id: int = 1, project_id: int = 1) -> Dict:
        """
        记录分享行为
        
        Args:
            user_id: 分享用户ID
            share_type: 分享类型 (product/order/coupon/page/invite)
            target_id: 被分享对象ID
            target_title: 分享标题
            channel: 分享渠道
            ec_id: 企业ID
            project_id: 项目ID
        
        Returns:
            {"success": True, "share_id": 123, "share_url": "..."}
        """
        try:
            # 生成唯一分享标识
            share_token = self._generate_share_token(user_id, target_id)
            
            db.execute("""
                INSERT INTO business_share_logs
                (user_id, share_type, target_id, target_title, share_channel, ec_id, project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [user_id, share_type, target_id, target_title, channel, ec_id, project_id])
            
            result = db.get_one("SELECT LAST_INSERT_ID() as id")
            share_id = result['id'] if result else 0
            
            # 生成分享链接
            share_url = self._generate_share_url(share_type, target_id, share_token)
            
            logger.info(f"[ShareService] 用户 {user_id} 分享了 {share_type}:{target_id}")
            
            return {
                'success': True,
                'share_id': share_id,
                'share_token': share_token,
                'share_url': share_url,
            }
            
        except Exception as e:
            logger.error(f"[ShareService] 记录分享失败: {e}")
            return {'success': False, 'msg': str(e)}
    
    def record_click(self, share_token: str) -> Dict:
        """
        记录分享链接点击
        
        Args:
            share_token: 分享标识
        
        Returns:
            {"success": True, "source_user_id": 123, "target_type": "product"}
        """
        try:
            # 解析分享标识获取来源用户
            source_user_id, target_id, target_type = self._parse_share_token(share_token)
            
            if not source_user_id:
                return {'success': False, 'msg': '无效的分享链接'}
            
            # 更新点击数
            db.execute("""
                UPDATE business_share_logs
                SET click_count = click_count + 1
                WHERE user_id = %s AND target_id = %s
                ORDER BY created_at DESC LIMIT 1
            """, [source_user_id, target_id])
            
            return {
                'success': True,
                'source_user_id': source_user_id,
                'target_type': target_type,
                'target_id': target_id,
            }
            
        except Exception as e:
            logger.error(f"[ShareService] 记录点击失败: {e}")
            return {'success': False, 'msg': str(e)}
    
    def record_conversion(self, order_id: int, share_token: str = None) -> Dict:
        """
        记录分享转化（下单）
        
        Args:
            order_id: 订单ID
            share_token: 分享标识（可选）
        
        Returns:
            {"success": True, "converted": True}
        """
        if not share_token:
            return {'success': True, 'converted': False}
        
        try:
            source_user_id, target_id, target_type = self._parse_share_token(share_token)
            
            if not source_user_id:
                return {'success': True, 'converted': False}
            
            # 获取订单金额
            order = db.get_one("""
                SELECT actual_amount FROM business_orders WHERE id = %s
            """, [order_id])
            
            amount = order['actual_amount'] if order else 0
            
            # 更新转化记录
            db.execute("""
                UPDATE business_share_logs
                SET convert_count = convert_count + 1,
                    convert_amount = convert_amount + %s
                WHERE user_id = %s AND target_id = %s
                ORDER BY created_at DESC LIMIT 1
            """, [amount, source_user_id, target_id])
            
            # 更新订单来源
            db.execute("""
                UPDATE business_orders
                SET share_from_user_id = %s
                WHERE id = %s
            """, [source_user_id, order_id])
            
            logger.info(f"[ShareService] 分享转化：用户通过 {source_user_id} 的分享下单")
            
            return {'success': True, 'converted': True, 'source_user_id': source_user_id}
            
        except Exception as e:
            logger.error(f"[ShareService] 记录转化失败: {e}")
            return {'success': False, 'msg': str(e)}
    
    def get_user_share_stats(self, user_id: int) -> Dict:
        """获取用户分享统计"""
        stats = db.get_one("""
            SELECT 
                COUNT(*) as total_shares,
                SUM(click_count) as total_clicks,
                SUM(convert_count) as total_converts,
                SUM(convert_amount) as total_amount
            FROM business_share_logs
            WHERE user_id = %s
        """, [user_id])
        
        # 获取各渠道统计
        channels = db.get_all("""
            SELECT share_channel, COUNT(*) as shares, SUM(click_count) as clicks
            FROM business_share_logs
            WHERE user_id = %s
            GROUP BY share_channel
        """, [user_id])
        
        channel_stats = {c['share_channel']: c for c in channels}
        
        return {
            'total_shares': stats.get('total_shares', 0) or 0,
            'total_clicks': stats.get('total_clicks', 0) or 0,
            'total_converts': stats.get('total_converts', 0) or 0,
            'total_convert_amount': float(stats.get('total_amount', 0) or 0),
            'click_rate': round(
                (stats.get('total_clicks', 0) or 0) / max(stats.get('total_shares', 1), 1) * 100, 1
            ),
            'convert_rate': round(
                (stats.get('total_converts', 0) or 0) / max(stats.get('total_shares', 1), 1) * 100, 1
            ),
            'channel_stats': channel_stats,
        }
    
    def get_share_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """获取用户分享历史"""
        shares = db.get_all("""
            SELECT id, share_type, target_id, target_title, share_channel,
                   click_count, convert_count, convert_amount, created_at
            FROM business_share_logs
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, [user_id, limit])
        
        return shares or []
    
    # ============ 分享链接生成 ============
    
    def _generate_share_token(self, user_id: int, target_id: int) -> str:
        """生成分享标识"""
        import hashlib
        import time
        
        data = f"{user_id}:{target_id}:{time.time()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    def _parse_share_token(self, token: str) -> tuple:
        """解析分享标识（简化版本，实际应存储完整映射）"""
        # 这里需要查询数据库获取完整的映射关系
        # 简化处理：根据token查找最近一条分享记录
        share = db.get_one("""
            SELECT user_id, target_id, share_type
            FROM business_share_logs
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        if share:
            return share['user_id'], share['target_id'], share['share_type']
        return None, None, None
    
    def _generate_share_url(self, share_type: str, target_id: int, token: str) -> str:
        """生成分享URL"""
        # 根据分享类型生成对应的URL
        base_url = "https://example.com"  # 实际应该从配置获取
        
        if share_type == 'product':
            return f"{base_url}/product/{target_id}?share={token}"
        elif share_type == 'order':
            return f"{base_url}/order/{target_id}?share={token}"
        elif share_type == 'coupon':
            return f"{base_url}/coupon/{target_id}?share={token}"
        elif share_type == 'invite':
            return f"{base_url}/invite?code={token}"
        else:
            return f"{base_url}/?share={token}"
    
    # ============ 分享海报生成 ============
    
    def generate_poster_config(self, share_type: str, target_id: int,
                              user_id: int, ec_id: int, project_id: int,
                              share_url: str = None) -> Dict:
        """
        生成分享海报配置（前端正渲染使用）
        
        Args:
            share_type: 分享类型
            target_id: 目标ID
            user_id: 用户ID
            ec_id: 企业ID
            project_id: 项目ID
            share_url: 已生成的真实分享链接（可选）
        
        Returns:
            海报渲染配置（前端Canvas使用）
        """
        poster_share_url = share_url or self._generate_share_url(share_type, target_id, '')
        config = {
            'width': 750,
            'height': 1000,
            'background': '#ffffff',
            'share_url': poster_share_url,
            'elements': [],
        }
        
        if share_type == 'product':
            # 获取商品信息
            product = db.get_one("""
                SELECT product_name, name, price, image FROM business_products WHERE id = %s
            """, [target_id])
            product_name = ''
            if product:
                product_name = product.get('product_name') or product.get('name') or '商品'
                config['elements'] = [
                    # 商品图片
                    {
                        'type': 'image',
                        'x': 0,
                        'y': 0,
                        'width': 750,
                        'height': 500,
                        'src': product.get('image', ''),
                    },
                    # 商品名称
                    {
                        'type': 'text',
                        'x': 30,
                        'y': 550,
                        'width': 690,
                        'fontSize': 32,
                        'color': '#333333',
                        'text': product_name,
                        'maxLines': 2,
                    },
                    # 价格
                    {
                        'type': 'text',
                        'x': 30,
                        'y': 650,
                        'fontSize': 48,
                        'color': '#f57c00',
                        'text': f'¥{float(product.get("price", 0)):.2f}',
                    },
                    # 二维码占位
                    {
                        'type': 'qrcode',
                        'x': 525,
                        'y': 700,
                        'width': 200,
                        'height': 200,
                        'url': poster_share_url,
                    },
                    # 提示文字
                    {
                        'type': 'text',
                        'x': 525,
                        'y': 920,
                        'width': 200,
                        'fontSize': 24,
                        'color': '#999999',
                        'text': '扫码购买',
                        'align': 'center',
                    },
                ]
            config['product_name'] = product_name or '商品'
        
        elif share_type == 'invite':
            # 邀请海报
            member = db.get_one("""
                SELECT nickname FROM business_members WHERE user_id = %s
            """, [user_id])
            
            config['elements'] = [
                # 背景
                {
                    'type': 'rect',
                    'x': 0,
                    'y': 0,
                    'width': 750,
                    'height': 1000,
                    'color': '#667eea',
                },
                # 标题
                {
                    'type': 'text',
                    'x': 0,
                    'y': 200,
                    'width': 750,
                    'fontSize': 48,
                    'color': '#ffffff',
                    'text': '邀请您加入',
                    'align': 'center',
                },
                # 用户昵称
                {
                    'type': 'text',
                    'x': 0,
                    'y': 300,
                    'width': 750,
                    'fontSize': 32,
                    'color': '#ffffff',
                    'text': member.get('nickname', '好友') if member else '好友',
                    'align': 'center',
                },
                # 二维码
                {
                    'type': 'qrcode',
                    'x': 275,
                    'y': 400,
                    'width': 200,
                    'height': 200,
                    'url': poster_share_url,
                },
                # 提示
                {
                    'type': 'text',
                    'x': 0,
                    'y': 650,
                    'width': 750,
                    'fontSize': 28,
                    'color': '#ffffff',
                    'text': '长按识别二维码',
                    'align': 'center',
                },
            ]
        
        return config



# 全局实例
share_service = ShareService()
