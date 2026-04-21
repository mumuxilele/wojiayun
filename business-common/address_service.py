"""
Address Service - 收货地址业务逻辑层
V48.0: MVC架构批量改造
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AddressService:
    """收货地址服务类"""
    
    def __init__(self):
        from business_common import db
        self.db = db
    
    def get_addresses(self, user_id: str, ec_id: str = None, project_id: str = None) -> List[Dict]:
        """获取用户收货地址列表"""
        return self.db.get_all("""
            SELECT id, user_name, phone, province, city, area, address, is_default, tag,
                   created_at, updated_at
            FROM business_user_addresses WHERE user_id=%s AND deleted=0
            ORDER BY is_default DESC, created_at DESC
        """, [user_id]) or []
    
    def get_address(self, addr_id: int, user_id: str) -> Optional[Dict]:
        """获取单个收货地址"""
        return self.db.get_one(
            "SELECT * FROM business_user_addresses WHERE id=%s AND user_id=%s AND deleted=0",
            [addr_id, user_id]
        )
    
    def create_address(self, user_id: str, user_name: str, phone: str,
                       province: str, city: str, area: str, address: str,
                       is_default: int = 0, tag: str = '',
                       ec_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """创建收货地址"""
        try:
            # 如果设为默认，先取消其他默认
            if is_default:
                self.db.execute(
                    "UPDATE business_user_addresses SET is_default=0 WHERE user_id=%s AND deleted=0",
                    [user_id]
                )
            
            # 插入新地址
            addr_id = self.db.execute("""
                INSERT INTO business_user_addresses 
                (user_id, user_name, phone, province, city, area, address, is_default, tag, ec_id, project_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, [user_id, user_name, phone, province, city, area, address, is_default, tag, ec_id, project_id])
            
            return {'success': True, 'msg': '地址创建成功', 'address_id': addr_id}
        except Exception as e:
            logger.error(f"创建地址失败: {e}")
            return {'success': False, 'msg': f'创建失败: {str(e)}'}
    
    def update_address(self, addr_id: int, user_id: str,
                       user_name: str = None, phone: str = None,
                       province: str = None, city: str = None, area: str = None,
                       address: str = None, is_default: int = None, tag: str = None) -> Dict[str, Any]:
        """更新收货地址"""
        try:
            # 检查地址是否存在
            existing = self.get_address(addr_id, user_id)
            if not existing:
                return {'success': False, 'msg': '地址不存在'}
            
            # 构建更新字段
            updates = []
            values = []
            
            if user_name is not None:
                updates.append("user_name=%s"); values.append(user_name)
            if phone is not None:
                updates.append("phone=%s"); values.append(phone)
            if province is not None:
                updates.append("province=%s"); values.append(province)
            if city is not None:
                updates.append("city=%s"); values.append(city)
            if area is not None:
                updates.append("area=%s"); values.append(area)
            if address is not None:
                updates.append("address=%s"); values.append(address)
            if tag is not None:
                updates.append("tag=%s"); values.append(tag)
            if is_default is not None:
                updates.append("is_default=%s"); values.append(is_default)
            
            if not updates:
                return {'success': True, 'msg': '没有更新字段'}
            
            # 如果设为默认，先取消其他默认
            if is_default == 1:
                self.db.execute(
                    "UPDATE business_user_addresses SET is_default=0 WHERE user_id=%s AND deleted=0",
                    [user_id]
                )
            
            updates.append("updated_at=NOW()")
            values.extend([addr_id, user_id])
            
            self.db.execute(
                f"UPDATE business_user_addresses SET {', '.join(updates)} WHERE id=%s AND user_id=%s",
                values
            )
            
            return {'success': True, 'msg': '地址更新成功'}
        except Exception as e:
            logger.error(f"更新地址失败: {e}")
            return {'success': False, 'msg': f'更新失败: {str(e)}'}
    
    def delete_address(self, addr_id: int, user_id: str) -> Dict[str, Any]:
        """删除收货地址（软删除）"""
        try:
            affected = self.db.execute(
                "UPDATE business_user_addresses SET deleted=1, updated_at=NOW() WHERE id=%s AND user_id=%s",
                [addr_id, user_id]
            )
            if affected > 0:
                return {'success': True, 'msg': '地址已删除'}
            return {'success': False, 'msg': '地址不存在'}
        except Exception as e:
            logger.error(f"删除地址失败: {e}")
            return {'success': False, 'msg': f'删除失败: {str(e)}'}
    
    def set_default(self, addr_id: int, user_id: str) -> Dict[str, Any]:
        """设为默认地址"""
        try:
            # 先取消所有默认
            self.db.execute(
                "UPDATE business_user_addresses SET is_default=0 WHERE user_id=%s AND deleted=0",
                [user_id]
            )
            # 设置新的默认
            self.db.execute(
                "UPDATE business_user_addresses SET is_default=1, updated_at=NOW() WHERE id=%s AND user_id=%s",
                [addr_id, user_id]
            )
            return {'success': True, 'msg': '已设为默认地址'}
        except Exception as e:
            logger.error(f"设置默认地址失败: {e}")
            return {'success': False, 'msg': f'设置失败: {str(e)}'}


_address_service = None

def get_address_service() -> AddressService:
    global _address_service
    if _address_service is None:
        _address_service = AddressService()
    return _address_service