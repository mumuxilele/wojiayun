"""
地址管理增强服务 V44.0

功能:
1. 地址标签（家/公司/其他）
2. 智能地址解析（从粘贴文本自动提取收件人/手机/省市区/详细地址）
3. 地址有效性校验（手机格式/字段完整性）
4. 默认地址管理（设为默认/获取默认）
5. 地址使用频次统计
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from . import db
from .cache_service import cache_delete

logger = logging.getLogger(__name__)


# 省份列表（用于智能解析）
PROVINCES = [
    '北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江',
    '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南',
    '广东', '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海', '台湾',
    '内蒙古', '广西', '西藏', '宁夏', '新疆', '香港', '澳门',
]

# 地址标签
ADDRESS_TAGS = {
    'home': '家',
    'company': '公司',
    'school': '学校',
    'other': '其他',
}


class AddressEnhanceService:
    """地址管理增强服务"""

    def __init__(self):
        self._ensure_columns()

    def _ensure_columns(self):
        """确保地址表有增强字段"""
        try:
            cols = db.get_all("SHOW COLUMNS FROM business_user_addresses") or []
            col_names = {c['Field'] for c in cols}

            alter_sqls = []
            if 'address_tag' not in col_names:
                alter_sqls.append(
                    "ADD COLUMN address_tag VARCHAR(20) DEFAULT 'other' COMMENT '地址标签:home/company/school/other'"
                )
            if 'longitude' not in col_names:
                alter_sqls.append(
                    "ADD COLUMN longitude DECIMAL(10,6) COMMENT '经度'"
                )
            if 'latitude' not in col_names:
                alter_sqls.append(
                    "ADD COLUMN latitude DECIMAL(10,6) COMMENT '纬度'"
                )
            if 'use_count' not in col_names:
                alter_sqls.append(
                    "ADD COLUMN use_count INT DEFAULT 0 COMMENT '使用次数'"
                )
            if 'last_used_at' not in col_names:
                alter_sqls.append(
                    "ADD COLUMN last_used_at DATETIME COMMENT '最后使用时间'"
                )

            for sql in alter_sqls:
                try:
                    db.execute(f"ALTER TABLE business_user_addresses {sql}")
                except Exception as e:
                    logger.warning(f"ALTER TABLE失败（可能已存在）: {e}")

            if alter_sqls:
                logger.info(f"地址表已增强 {len(alter_sqls)} 个字段")
        except Exception as e:
            logger.warning(f"地址表增强失败: {e}")

    # ============ 地址CRUD ============

    def get_address_list(self, user_id: int) -> List[Dict]:
        """获取用户地址列表（按默认+使用频次排序）"""
        addresses = db.get_all("""
            SELECT id, contact_name, contact_phone, province, city, district, address,
                   is_default, address_tag, longitude, latitude, use_count, last_used_at
            FROM business_user_addresses
            WHERE user_id=%s AND deleted=0
            ORDER BY is_default DESC, use_count DESC, created_at DESC
        """, [user_id]) or []

        # 补充标签名称
        for addr in addresses:
            tag = addr.get('address_tag', 'other')
            addr['tag_name'] = ADDRESS_TAGS.get(tag, '其他')
            # 脱敏手机号展示
            phone = addr.get('contact_phone', '')
            addr['phone_masked'] = self._mask_phone(phone)
            # 拼接完整地址
            addr['full_address'] = self._format_full_address(addr)

        return addresses

    def create_address(self, user_id: int, data: Dict) -> Dict:
        """创建地址"""
        # 校验
        valid, msg = self._validate_address(data)
        if not valid:
            return {'success': False, 'msg': msg}

        try:
            # 若设为默认，先取消其他默认
            if data.get('is_default'):
                self._clear_default(user_id)

            # 如果是第一个地址，自动设为默认
            count = db.get_total(
                "SELECT COUNT(*) FROM business_user_addresses WHERE user_id=%s AND deleted=0",
                [user_id]
            )
            is_default = 1 if (data.get('is_default') or count == 0) else 0

            addr_id = db.insert("""
                INSERT INTO business_user_addresses
                (user_id, contact_name, contact_phone, province, city, district, address,
                 is_default, address_tag, longitude, latitude, use_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
            """, [
                user_id,
                data.get('contact_name', '').strip(),
                data.get('contact_phone', '').strip(),
                data.get('province', '').strip(),
                data.get('city', '').strip(),
                data.get('district', '').strip(),
                data.get('address', '').strip(),
                is_default,
                data.get('address_tag', 'other'),
                data.get('longitude'),
                data.get('latitude'),
            ])
            cache_delete(f"user_default_addr_{user_id}")
            return {'success': True, 'address_id': addr_id, 'msg': '地址添加成功'}
        except Exception as e:
            logger.error(f"创建地址失败: {e}")
            return {'success': False, 'msg': '添加失败，请重试'}

    def update_address(self, user_id: int, address_id: int, data: Dict) -> Dict:
        """更新地址"""
        addr = db.get_one(
            "SELECT id FROM business_user_addresses WHERE id=%s AND user_id=%s AND deleted=0",
            [address_id, user_id]
        )
        if not addr:
            return {'success': False, 'msg': '地址不存在'}

        valid, msg = self._validate_address(data)
        if not valid:
            return {'success': False, 'msg': msg}

        try:
            if data.get('is_default'):
                self._clear_default(user_id)

            db.execute("""
                UPDATE business_user_addresses
                SET contact_name=%s, contact_phone=%s, province=%s, city=%s, district=%s,
                    address=%s, is_default=%s, address_tag=%s, longitude=%s, latitude=%s,
                    updated_at=NOW()
                WHERE id=%s AND user_id=%s
            """, [
                data.get('contact_name', '').strip(),
                data.get('contact_phone', '').strip(),
                data.get('province', '').strip(),
                data.get('city', '').strip(),
                data.get('district', '').strip(),
                data.get('address', '').strip(),
                int(bool(data.get('is_default'))),
                data.get('address_tag', 'other'),
                data.get('longitude'),
                data.get('latitude'),
                address_id, user_id
            ])
            cache_delete(f"user_default_addr_{user_id}")
            return {'success': True, 'msg': '更新成功'}
        except Exception as e:
            logger.error(f"更新地址失败: {e}")
            return {'success': False, 'msg': '更新失败'}

    def delete_address(self, user_id: int, address_id: int) -> Dict:
        """软删除地址"""
        try:
            addr = db.get_one(
                "SELECT is_default FROM business_user_addresses WHERE id=%s AND user_id=%s AND deleted=0",
                [address_id, user_id]
            )
            if not addr:
                return {'success': False, 'msg': '地址不存在'}

            db.execute(
                "UPDATE business_user_addresses SET deleted=1, updated_at=NOW() WHERE id=%s AND user_id=%s",
                [address_id, user_id]
            )

            # 若删除的是默认地址，自动将最新的地址设为默认
            if addr.get('is_default'):
                remaining = db.get_one("""
                    SELECT id FROM business_user_addresses
                    WHERE user_id=%s AND deleted=0
                    ORDER BY use_count DESC, created_at DESC LIMIT 1
                """, [user_id])
                if remaining:
                    db.execute(
                        "UPDATE business_user_addresses SET is_default=1 WHERE id=%s",
                        [remaining['id']]
                    )

            cache_delete(f"user_default_addr_{user_id}")
            return {'success': True, 'msg': '地址已删除'}
        except Exception as e:
            return {'success': False, 'msg': str(e)}

    def set_default(self, user_id: int, address_id: int) -> Dict:
        """设置默认地址"""
        addr = db.get_one(
            "SELECT id FROM business_user_addresses WHERE id=%s AND user_id=%s AND deleted=0",
            [address_id, user_id]
        )
        if not addr:
            return {'success': False, 'msg': '地址不存在'}

        try:
            self._clear_default(user_id)
            db.execute(
                "UPDATE business_user_addresses SET is_default=1, updated_at=NOW() WHERE id=%s",
                [address_id]
            )
            cache_delete(f"user_default_addr_{user_id}")
            return {'success': True, 'msg': '默认地址已设置'}
        except Exception as e:
            return {'success': False, 'msg': str(e)}

    def get_default_address(self, user_id: int) -> Optional[Dict]:
        """获取默认地址"""
        addr = db.get_one("""
            SELECT id, contact_name, contact_phone, province, city, district, address,
                   is_default, address_tag, longitude, latitude
            FROM business_user_addresses
            WHERE user_id=%s AND is_default=1 AND deleted=0
            LIMIT 1
        """, [user_id])
        if not addr:
            # 回退到最近使用的地址
            addr = db.get_one("""
                SELECT id, contact_name, contact_phone, province, city, district, address,
                       is_default, address_tag, longitude, latitude
                FROM business_user_addresses
                WHERE user_id=%s AND deleted=0
                ORDER BY use_count DESC, created_at DESC
                LIMIT 1
            """, [user_id])

        if addr:
            addr['full_address'] = self._format_full_address(addr)
            addr['tag_name'] = ADDRESS_TAGS.get(addr.get('address_tag', 'other'), '其他')
        return addr

    def record_address_use(self, user_id: int, address_id: int):
        """记录地址使用（用于频次统计）"""
        try:
            db.execute("""
                UPDATE business_user_addresses
                SET use_count = COALESCE(use_count, 0) + 1, last_used_at=NOW()
                WHERE id=%s AND user_id=%s
            """, [address_id, user_id])
        except Exception as e:
            logger.warning(f"记录地址使用失败: {e}")

    # ============ 智能地址解析 ============

    def parse_address(self, raw_text: str) -> Dict:
        """
        智能地址解析
        输入: "张三 13800138000 广东省深圳市南山区科技园路123号"
        输出: {contact_name, contact_phone, province, city, district, address}
        """
        raw_text = raw_text.strip()
        if not raw_text:
            return {'success': False, 'msg': '请输入地址信息'}

        result = {
            'contact_name': '',
            'contact_phone': '',
            'province': '',
            'city': '',
            'district': '',
            'address': '',
        }

        # 提取手机号
        phone_pattern = r'1[3-9]\d{9}'
        phones = re.findall(phone_pattern, raw_text)
        if phones:
            result['contact_phone'] = phones[0]
            raw_text = raw_text.replace(phones[0], ' ')

        # 提取省份
        for province in PROVINCES:
            if province in raw_text:
                result['province'] = province
                idx = raw_text.index(province)

                # 提取省份前的姓名（通常是最前面的汉字）
                before = raw_text[:idx].strip()
                if before:
                    # 移除标点符号
                    name_candidate = re.sub(r'[，,\s\-/、]', '', before)
                    if 2 <= len(name_candidate) <= 6 and re.match(r'^[\u4e00-\u9fff]+$', name_candidate):
                        result['contact_name'] = name_candidate

                # 提取省份后的城市/区
                after = raw_text[idx + len(province):]
                after = after.lstrip('省')

                # 尝试提取城市（市/区结尾）
                city_match = re.match(r'^([\u4e00-\u9fff]{2,6}[市州盟]?)', after)
                if city_match:
                    result['city'] = city_match.group(1).rstrip('市')
                    after = after[city_match.end():]
                    after = after.lstrip('市')

                # 尝试提取区/县
                district_match = re.match(r'^([\u4e00-\u9fff]{2,6}[区县镇乡街道]?)', after)
                if district_match:
                    result['district'] = district_match.group(1).rstrip('区县')
                    after = after[district_match.end():]

                result['address'] = after.strip().lstrip('区县镇')
                break

        # 如果没有提取到姓名，尝试从开头提取
        if not result['contact_name']:
            name_match = re.match(r'^([^\d\s，,]{2,5})\s+', raw_text)
            if name_match:
                result['contact_name'] = name_match.group(1)

        return {
            'success': True,
            'data': result,
            'parsed_from': raw_text[:100],
        }

    # ============ 地址校验 ============

    def _validate_address(self, data: Dict) -> Tuple[bool, str]:
        """校验地址必填字段"""
        contact_name = (data.get('contact_name') or '').strip()
        contact_phone = (data.get('contact_phone') or '').strip()
        province = (data.get('province') or '').strip()
        address = (data.get('address') or '').strip()

        if not contact_name:
            return False, '请填写收件人姓名'
        if len(contact_name) < 2:
            return False, '姓名不能少于2个字符'

        if not contact_phone:
            return False, '请填写手机号'
        if not re.match(r'^1[3-9]\d{9}$', contact_phone):
            return False, '手机号格式不正确'

        if not province:
            return False, '请选择省份'

        if not address:
            return False, '请填写详细地址'
        if len(address) < 5:
            return False, '详细地址不能少于5个字符'

        return True, ''

    # ============ 工具函数 ============

    def _clear_default(self, user_id: int):
        """取消用户所有默认地址"""
        db.execute(
            "UPDATE business_user_addresses SET is_default=0 WHERE user_id=%s AND deleted=0",
            [user_id]
        )

    def _mask_phone(self, phone: str) -> str:
        """手机号脱敏：138****8000"""
        if phone and len(phone) == 11:
            return phone[:3] + '****' + phone[7:]
        return phone

    def _format_full_address(self, addr: Dict) -> str:
        """拼接完整地址"""
        parts = [
            addr.get('province', ''),
            addr.get('city', ''),
            addr.get('district', ''),
            addr.get('address', ''),
        ]
        return ''.join(p for p in parts if p)


# 全局单例
address_enhance = AddressEnhanceService()
