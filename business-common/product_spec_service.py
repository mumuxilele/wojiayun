"""
V42.0 商品多规格属性服务体系
功能：
  - 规格属性分组管理（颜色、尺码、版本等）
  - SKU矩阵组合生成与管理
  - 库存/价格按规格粒度独立管理
  - 前端规格选择联动（笛卡尔积）

依赖：
- db: 数据库模块
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from . import db
from .service_base import BaseService

logger = logging.getLogger(__name__)


class ProductSpecService(BaseService):
    """商品多规格属性服务"""

    SERVICE_NAME = 'ProductSpecService'

    def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        base = super().health_check()
        try:
            result = db.get_one("SELECT COUNT(*) as cnt FROM business_product_specs LIMIT 1")
            base['spec_count'] = result.get('cnt', 0) if result else 0
        except Exception as e:
            base['db_status'] = 'error'
            base['error'] = str(e)
        return base

    # ============ 规格组管理 ============

    def get_spec_groups(self, product_id: int) -> List[Dict]:
        """
        获取商品的所有规格组（颜色、尺码等）

        Args:
            product_id: 商品ID

        Returns:
            List[Dict]: 规格组列表，每个组包含规格名和规格值
        """
        try:
            groups = db.get_all("""
                SELECT id, spec_name, sort_order
                FROM business_product_specs
                WHERE product_id = %s AND deleted = 0
                ORDER BY sort_order ASC, id ASC
            """, [product_id])

            for group in groups:
                # 查询该组下的所有规格值
                values = db.get_all("""
                    SELECT sv.id, sv.spec_value, sv.sort_order, sv.extra_price
                    FROM business_product_spec_values sv
                    WHERE sv.spec_id = %s AND sv.deleted = 0
                    ORDER BY sv.sort_order ASC, sv.id ASC
                """, [group['id']])
                group['values'] = values or []
                group['value_count'] = len(values)

            return groups or []
        except Exception as e:
            logger.error(f"[ProductSpecService] 获取规格组失败: {e}")
            return []

    def add_spec_group(self, product_id: int, spec_name: str,
                      values: List[str] = None,
                      sort_order: int = 0) -> Dict[str, Any]:
        """
        添加规格组（支持批量添加规格值）

        Args:
            product_id: 商品ID
            spec_name: 规格组名称，如"颜色"、"尺码"、"版本"
            values: 规格值列表，如["红色","蓝色","黑色"]
            sort_order: 排序

        Returns:
            Dict: 创建结果
        """
        try:
            # 插入规格组
            group_id = db.execute("""
                INSERT INTO business_product_specs (product_id, spec_name, sort_order, created_at)
                VALUES (%s, %s, %s, NOW())
            """, [product_id, spec_name, sort_order])

            if not group_id:
                return {'success': False, 'msg': '规格组创建失败'}

            # 批量插入规格值
            if values:
                for i, value in enumerate(values):
                    extra_price = 0
                    # 支持 "红色:+10" 格式指定附加价格
                    if isinstance(value, str) and ':' in value:
                        parts = value.split(':', 1)
                        value = parts[0]
                        try:
                            extra_price = float(parts[1])
                        except ValueError:
                            extra_price = 0

                    db.execute("""
                        INSERT INTO business_product_spec_values (spec_id, spec_value, extra_price, sort_order)
                        VALUES (%s, %s, %s, %s)
                    """, [group_id, value, extra_price, i])

            logger.info(f"[ProductSpecService] 添加规格组: product_id={product_id}, spec_name={spec_name}")

            return {'success': True, 'spec_id': group_id, 'msg': '规格组创建成功'}
        except Exception as e:
            logger.error(f"[ProductSpecService] 添加规格组失败: {e}")
            return {'success': False, 'msg': str(e)}

    def update_spec_group(self, spec_id: int, spec_name: str = None,
                         sort_order: int = None) -> Dict[str, Any]:
        """更新规格组"""
        try:
            updates = []
            params = []
            if spec_name is not None:
                updates.append("spec_name = %s")
                params.append(spec_name)
            if sort_order is not None:
                updates.append("sort_order = %s")
                params.append(sort_order)

            if not updates:
                return {'success': False, 'msg': '没有需要更新的字段'}

            updates.append("updated_at = NOW()")
            params.append(spec_id)

            db.execute(
                f"UPDATE business_product_specs SET {', '.join(updates)} WHERE id = %s",
                params
            )
            return {'success': True, 'msg': '规格组更新成功'}
        except Exception as e:
            logger.error(f"[ProductSpecService] 更新规格组失败: {e}")
            return {'success': False, 'msg': str(e)}

    def delete_spec_group(self, spec_id: int) -> Dict[str, Any]:
        """删除规格组（软删除，同时删除所有规格值）"""
        try:
            db.execute(
                "UPDATE business_product_spec_values SET deleted=1 WHERE spec_id=%s",
                [spec_id]
            )
            db.execute(
                "UPDATE business_product_specs SET deleted=1 WHERE id=%s",
                [spec_id]
            )
            return {'success': True, 'msg': '规格组删除成功'}
        except Exception as e:
            logger.error(f"[ProductSpecService] 删除规格组失败: {e}")
            return {'success': False, 'msg': str(e)}

    # ============ 规格值管理 ============

    def add_spec_value(self, spec_id: int, spec_value: str,
                      extra_price: float = 0, sort_order: int = 0) -> Dict[str, Any]:
        """添加规格值"""
        try:
            # 支持 "红色:+10" 格式
            value = spec_value
            extra = extra_price
            if isinstance(spec_value, str) and ':' in spec_value:
                parts = spec_value.split(':', 1)
                value = parts[0]
                try:
                    extra = float(parts[1])
                except ValueError:
                    extra = 0

            spec_value_id = db.execute("""
                INSERT INTO business_product_spec_values (spec_id, spec_value, extra_price, sort_order)
                VALUES (%s, %s, %s, %s)
            """, [spec_id, value, extra, sort_order])

            return {'success': True, 'spec_value_id': spec_value_id, 'msg': '规格值添加成功'}
        except Exception as e:
            logger.error(f"[ProductSpecService] 添加规格值失败: {e}")
            return {'success': False, 'msg': str(e)}

    def delete_spec_value(self, spec_value_id: int) -> Dict[str, Any]:
        """删除规格值"""
        try:
            db.execute(
                "UPDATE business_product_spec_values SET deleted=1 WHERE id=%s",
                [spec_value_id]
            )
            return {'success': True, 'msg': '规格值删除成功'}
        except Exception as e:
            logger.error(f"[ProductSpecService] 删除规格值失败: {e}")
            return {'success': False, 'msg': str(e)}

    # ============ SKU矩阵管理 ============

    def generate_sku_matrix(self, product_id: int) -> List[Dict]:
        """
        生成SKU笛卡尔积矩阵

        根据所有规格组生成所有SKU组合，并补充已有的SKU信息。

        Args:
            product_id: 商品ID

        Returns:
            List[Dict]: SKU组合列表，每项包含规格组合、价格、库存
        """
        try:
            # 获取所有规格组及其值
            groups = self.get_spec_groups(product_id)

            if not groups:
                return []

            # 获取商品主信息
            product = db.get_one(
                "SELECT * FROM business_products WHERE id=%s AND deleted=0",
                [product_id]
            )
            if not product:
                return []

            base_price = float(product.get('price', 0))
            base_stock = int(product.get('stock', 0))

            # 获取已有SKU列表
            existing_skus = db.get_all("""
                SELECT * FROM business_product_skus
                WHERE product_id=%s AND deleted=0
            """, [product_id]) or []

            # 构建 SKU specs JSON -> SKU dict 映射
            sku_map = {}
            for sku in existing_skus:
                specs = sku.get('specs', '{}')
                if isinstance(specs, str):
                    try:
                        specs = json.loads(specs)
                    except:
                        specs = {}
                # 用规格值的ID组合作为key
                key = self._build_spec_key(specs)
                sku_map[key] = sku

            # 生成笛卡尔积
            spec_values_list = [g['values'] for g in groups]
            combinations = self._cartesian_product(spec_values_list)

            # 批量查询库存
            sku_ids = [s['id'] for s in existing_skus]
            stock_map = {}
            if sku_ids:
                stocks = db.get_all(
                    f"SELECT id, stock FROM business_product_skus WHERE id IN ({','.join(['%s']*len(sku_ids))})",
                    sku_ids
                ) or []
                stock_map = {s['id']: s['stock'] for s in stocks}

            # 构建SKU矩阵
            matrix = []
            for combo in combinations:
                # 计算规格组合key
                specs_dict = {}
                total_extra_price = 0
                for i, val in enumerate(combo):
                    group_name = groups[i]['spec_name']
                    specs_dict[group_name] = val['spec_value']
                    total_extra_price += float(val.get('extra_price') or 0)

                key = self._build_spec_key(specs_dict)
                sku_price = base_price + total_extra_price

                sku_record = sku_map.get(key, {})
                sku_id = sku_record.get('id')
                sku_stock = stock_map.get(sku_id, 0) if sku_id else 0
                sku_code = sku_record.get('sku_code', '')

                matrix.append({
                    'specs': specs_dict,
                    'spec_ids': [v['id'] for v in combo],
                    'sku_id': sku_id,
                    'sku_code': sku_record.get('sku_code', sku_code),
                    'price': float(sku_record.get('price', sku_price)),
                    'stock': sku_stock,
                    'status': sku_record.get('status', 'active') if sku_id else 'inactive',
                })

            return matrix

        except Exception as e:
            logger.error(f"[ProductSpecService] 生成SKU矩阵失败: {e}")
            return []

    def create_or_update_sku(self, product_id: int, specs: Dict[str, str],
                             price: float, stock: int = 0,
                             sku_code: str = None) -> Dict[str, Any]:
        """
        创建或更新SKU（按规格组合）

        Args:
            product_id: 商品ID
            specs: 规格组合，如 {"颜色": "红色", "尺码": "XL"}
            price: SKU价格
            stock: 库存
            sku_code: SKU编码（可选）

        Returns:
            Dict: 操作结果
        """
        try:
            product = db.get_one(
                "SELECT * FROM business_products WHERE id=%s AND deleted=0",
                [product_id]
            )
            if not product:
                return {'success': False, 'msg': '商品不存在'}

            # 检查是否已存在
            existing = self._find_sku_by_specs(product_id, specs)
            specs_json = json.dumps(specs, ensure_ascii=False)

            if existing:
                # 更新
                db.execute("""
                    UPDATE business_product_skus
                    SET price=%s, stock=%s, specs=%s, updated_at=NOW()
                    WHERE id=%s
                """, [price, stock, specs_json, existing['id']])
                logger.info(f"[ProductSpecService] 更新SKU: id={existing['id']}")
                return {'success': True, 'sku_id': existing['id'], 'msg': 'SKU更新成功', 'is_new': False}
            else:
                # 新建
                if not sku_code:
                    import time, random
                    sku_code = f"SKU{product_id}{int(time.time())}{random.randint(100,999)}"

                sku_id = db.execute("""
                    INSERT INTO business_product_skus
                    (product_id, sku_code, specs, price, original_price, stock, status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'active')
                """, [product_id, sku_code, specs_json, price, price, stock])

                logger.info(f"[ProductSpecService] 创建SKU: id={sku_id}")
                return {'success': True, 'sku_id': sku_id, 'msg': 'SKU创建成功', 'is_new': True}

        except Exception as e:
            logger.error(f"[ProductSpecService] 创建/更新SKU失败: {e}")
            return {'success': False, 'msg': str(e)}

    def update_sku_price_and_stock(self, sku_id: int, price: float = None,
                                   stock: int = None) -> Dict[str, Any]:
        """批量更新SKU的价格和库存"""
        try:
            updates = []
            params = []
            if price is not None:
                updates.append("price = %s")
                params.append(price)
            if stock is not None:
                updates.append("stock = %s")
                params.append(stock)

            if not updates:
                return {'success': False, 'msg': '没有需要更新的字段'}

            updates.append("updated_at = NOW()")
            params.append(sku_id)

            affected = db.execute(
                f"UPDATE business_product_skus SET {', '.join(updates)} WHERE id = %s",
                params
            )

            if affected == 0:
                return {'success': False, 'msg': 'SKU不存在'}

            return {'success': True, 'msg': 'SKU更新成功'}
        except Exception as e:
            logger.error(f"[ProductSpecService] 更新SKU失败: {e}")
            return {'success': False, 'msg': str(e)}

    # ============ 工具方法 ============

    def _build_spec_key(self, specs: Dict[str, str]) -> str:
        """构建规格组合的唯一key（排序后JSON序列化）"""
        sorted_specs = {k: specs[k] for k in sorted(specs.keys())}
        return json.dumps(sorted_specs, sort_keys=True, ensure_ascii=False)

    def _find_sku_by_specs(self, product_id: int, specs: Dict[str, str]) -> Optional[Dict]:
        """根据规格组合查找SKU"""
        skus = db.get_all("""
            SELECT * FROM business_product_skus
            WHERE product_id=%s AND deleted=0
        """, [product_id]) or []

        target_key = self._build_spec_key(specs)

        for sku in skus:
            sku_specs = sku.get('specs', '{}')
            if isinstance(sku_specs, str):
                try:
                    sku_specs = json.loads(sku_specs)
                except:
                    sku_specs = {}
            if self._build_spec_key(sku_specs) == target_key:
                return sku

        return None

    def _cartesian_product(self, lists: List[List]) -> List[List]:
        """计算笛卡尔积"""
        if not lists:
            return []
        result = [[]]
        for lst in lists:
            result = [x + [y] for x in result for y in lst]
        return result

    def get_sku_price_range(self, product_id: int) -> Dict[str, float]:
        """获取商品SKU价格区间"""
        skus = db.get_all("""
            SELECT price FROM business_product_skus
            WHERE product_id=%s AND deleted=0 AND status='active'
        """, [product_id]) or []

        if not skus:
            product = db.get_one(
                "SELECT price FROM business_products WHERE id=%s",
                [product_id]
            )
            if product:
                price = float(product.get('price', 0))
                return {'min': price, 'max': price}
            return {'min': 0, 'max': 0}

        prices = [float(s['price']) for s in skus]
        return {'min': min(prices), 'max': max(prices)}


# 单例实例
spec_service = ProductSpecService()
