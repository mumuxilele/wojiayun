# service/wo_rule_service.py - SLA规则与派单规则服务
import json
from typing import Dict, List
from sqlalchemy.orm import Session

from service.base_service import BaseService
from db.models.wo_rule import WoSlaRule, WoDispatchRule, WoCategory
from utils.md5_fid_util import generate_fid
from utils.log_util import logger


class WoRuleService(BaseService):
    """SLA规则与派单规则服务"""

    # ========== SLA规则 ==========

    def list_sla_rules(self, fec_id: str, fproject_id: str) -> Dict:
        """获取SLA规则列表"""
        try:
            rules = WoSlaRule.active_query(self.db).filter(
                WoSlaRule.fec_id == fec_id,
                WoSlaRule.fproject_id == fproject_id
            ).order_by(WoSlaRule.fpriority.desc()).all()
            return self.success([self._sla_to_dict(r) for r in rules])
        except Exception as e:
            logger.error(f"查询SLA规则失败: {str(e)}", exc_info=True)
            return self.error(f"查询SLA规则失败: {str(e)}")

    def create_sla_rule(self, fec_id: str, fproject_id: str, **kwargs) -> Dict:
        """创建SLA规则"""
        try:
            self.begin()
            rule = WoSlaRule(
                fid=generate_fid(), fec_id=fec_id, fproject_id=fproject_id,
                frule_name=kwargs.get("frule_name", ""),
                fsla_level=kwargs.get("fsla_level", "L3"),
                flevel_name=kwargs.get("flevel_name", "中"),
                fpriority=kwargs.get("fpriority", "medium"),
                fresponse_minutes=kwargs.get("fresponse_minutes", 60),
                fcomplete_hours=kwargs.get("fcomplete_hours", 8),
                fescalate_minutes=kwargs.get("fescalate_minutes"),
                fescalate_count=kwargs.get("fescalate_count", 3),
                fescalate_to=kwargs.get("fescalate_to", ""),
                fis_enabled=kwargs.get("fis_enabled", 1),
                fremark=kwargs.get("fremark", ""),
            )
            self.db.add(rule)
            self.commit()
            return self.success(self._sla_to_dict(rule), message="SLA规则创建成功")
        except Exception as e:
            self.rollback()
            logger.error(f"创建SLA规则失败: {str(e)}", exc_info=True)
            return self.error(f"创建SLA规则失败: {str(e)}")

    def update_sla_rule(self, fec_id: str, fproject_id: str, fid: str, **kwargs) -> Dict:
        """更新SLA规则"""
        try:
            rule = WoSlaRule.active_query(self.db).filter(
                WoSlaRule.fid == fid, WoSlaRule.fec_id == fec_id,
                WoSlaRule.fproject_id == fproject_id
            ).first()
            if not rule:
                return self.error("SLA规则不存在", 404)
            self.begin()
            for key in ["frule_name", "fsla_level", "flevel_name", "fpriority",
                        "fresponse_minutes", "fcomplete_hours", "fescalate_minutes",
                        "fescalate_count", "fescalate_to", "fis_enabled", "fremark"]:
                if key in kwargs:
                    setattr(rule, key, kwargs[key])
            self.commit()
            return self.success(self._sla_to_dict(rule), message="SLA规则更新成功")
        except Exception as e:
            self.rollback()
            logger.error(f"更新SLA规则失败: {str(e)}", exc_info=True)
            return self.error(f"更新SLA规则失败: {str(e)}")

    # ========== 派单规则 ==========

    def list_dispatch_rules(self, fec_id: str, fproject_id: str) -> Dict:
        """获取派单规则列表"""
        try:
            rules = WoDispatchRule.active_query(self.db).filter(
                WoDispatchRule.fec_id == fec_id,
                WoDispatchRule.fproject_id == fproject_id
            ).order_by(WoDispatchRule.fpriority.desc()).all()
            return self.success([self._dispatch_to_dict(r) for r in rules])
        except Exception as e:
            logger.error(f"查询派单规则失败: {str(e)}", exc_info=True)
            return self.error(f"查询派单规则失败: {str(e)}")

    def create_dispatch_rule(self, fec_id: str, fproject_id: str, **kwargs) -> Dict:
        """创建派单规则"""
        try:
            self.begin()
            rule = WoDispatchRule(
                fid=generate_fid(), fec_id=fec_id, fproject_id=fproject_id,
                frule_name=kwargs.get("frule_name", ""),
                frule_type=kwargs.get("frule_type", "category"),
                fmatch_condition=json.dumps(kwargs.get("fmatch_condition", {}), ensure_ascii=False),
                fdispatch_action=kwargs.get("fdispatch_action", "assign_user"),
                fdispatch_target=json.dumps(kwargs.get("fdispatch_target", {}), ensure_ascii=False),
                fpriority=kwargs.get("fpriority", 0),
                fis_enabled=kwargs.get("fis_enabled", 1),
                fremark=kwargs.get("fremark", ""),
            )
            self.db.add(rule)
            self.commit()
            return self.success(self._dispatch_to_dict(rule), message="派单规则创建成功")
        except Exception as e:
            self.rollback()
            logger.error(f"创建派单规则失败: {str(e)}", exc_info=True)
            return self.error(f"创建派单规则失败: {str(e)}")

    def update_dispatch_rule(self, fec_id: str, fproject_id: str, fid: str, **kwargs) -> Dict:
        """更新派单规则"""
        try:
            rule = WoDispatchRule.active_query(self.db).filter(
                WoDispatchRule.fid == fid, WoDispatchRule.fec_id == fec_id,
                WoDispatchRule.fproject_id == fproject_id
            ).first()
            if not rule:
                return self.error("派单规则不存在", 404)
            self.begin()
            for key in ["frule_name", "frule_type", "fdispatch_action", "fpriority", "fis_enabled", "fremark"]:
                if key in kwargs:
                    setattr(rule, key, kwargs[key])
            if "fmatch_condition" in kwargs:
                rule.fmatch_condition = json.dumps(kwargs["fmatch_condition"], ensure_ascii=False)
            if "fdispatch_target" in kwargs:
                rule.fdispatch_target = json.dumps(kwargs["fdispatch_target"], ensure_ascii=False)
            self.commit()
            return self.success(self._dispatch_to_dict(rule), message="派单规则更新成功")
        except Exception as e:
            self.rollback()
            logger.error(f"更新派单规则失败: {str(e)}", exc_info=True)
            return self.error(f"更新派单规则失败: {str(e)}")

    def delete_dispatch_rule(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        """删除派单规则"""
        try:
            rule = WoDispatchRule.active_query(self.db).filter(
                WoDispatchRule.fid == fid, WoDispatchRule.fec_id == fec_id,
                WoDispatchRule.fproject_id == fproject_id
            ).first()
            if not rule:
                return self.error("派单规则不存在", 404)
            self.begin()
            rule.is_deleted = 1
            self.commit()
            return self.success(message="派单规则已删除")
        except Exception as e:
            self.rollback()
            logger.error(f"删除派单规则失败: {str(e)}", exc_info=True)
            return self.error(f"删除派单规则失败: {str(e)}")

    def auto_dispatch(self, fec_id: str, fproject_id: str,
                      category_id: str = "", location_type: str = "",
                      priority: str = "", keyword: str = "") -> Dict:
        """智能派单: 根据规则匹配派单目标"""
        try:
            rules = WoDispatchRule.active_query(self.db).filter(
                WoDispatchRule.fec_id == fec_id,
                WoDispatchRule.fproject_id == fproject_id,
                WoDispatchRule.fis_enabled == 1
            ).order_by(WoDispatchRule.fpriority.desc()).all()

            for rule in rules:
                condition = json.loads(rule.fmatch_condition) if rule.fmatch_condition else {}
                matched = True
                if rule.frule_type == "category" and category_id:
                    matched = category_id in condition.get("category_ids", [])
                elif rule.frule_type == "location" and location_type:
                    matched = location_type in condition.get("location_types", [])
                elif rule.frule_type == "priority" and priority:
                    matched = priority in condition.get("priorities", [])
                elif rule.frule_type == "keyword" and keyword:
                    matched = any(kw in keyword for kw in condition.get("keywords", []))

                if matched:
                    target = json.loads(rule.fdispatch_target) if rule.fdispatch_target else {}
                    return self.success({
                        "rule_id": rule.fid,
                        "rule_name": rule.frule_name,
                        "dispatch_action": rule.fdispatch_action,
                        "dispatch_target": target,
                    })

            return self.success(None, message="未匹配到派单规则")
        except Exception as e:
            logger.error(f"智能派单失败: {str(e)}", exc_info=True)
            return self.error(f"智能派单失败: {str(e)}")

    # ========== 工单分类 ==========

    def list_categories(self, fec_id: str, fproject_id: str,
                        category_type: str = "", parent_id: str = None) -> Dict:
        """获取分类列表(树形)"""
        try:
            q = WoCategory.active_query(self.db).filter(
                WoCategory.fec_id == fec_id,
                WoCategory.fproject_id == fproject_id,
                WoCategory.fis_enabled == 1
            )
            if category_type:
                q = q.filter(WoCategory.fcategory_type == category_type)
            if parent_id is not None:
                q = q.filter(WoCategory.fparent_id == parent_id if parent_id else WoCategory.fparent_id.is_(None))
            categories = q.order_by(WoCategory.fsort_order.asc()).all()
            return self.success([self._category_to_dict(c) for c in categories])
        except Exception as e:
            logger.error(f"查询分类失败: {str(e)}", exc_info=True)
            return self.error(f"查询分类失败: {str(e)}")

    def create_category(self, fec_id: str, fproject_id: str, **kwargs) -> Dict:
        """创建分类"""
        try:
            self.begin()
            cat = WoCategory(
                fid=generate_fid(), fec_id=fec_id, fproject_id=fproject_id,
                fparent_id=kwargs.get("fparent_id"),
                fcategory_name=kwargs.get("fcategory_name", ""),
                fcategory_code=kwargs.get("fcategory_code", ""),
                fcategory_type=kwargs.get("fcategory_type", "other"),
                ficon=kwargs.get("ficon", ""),
                fsort_order=kwargs.get("fsort_order", 0),
                fdescription=kwargs.get("fdescription", ""),
                fis_enabled=kwargs.get("fis_enabled", 1),
                fcreate_user_id=kwargs.get("fcreate_user_id", ""),
            )
            self.db.add(cat)
            self.commit()
            return self.success(self._category_to_dict(cat), message="分类创建成功")
        except Exception as e:
            self.rollback()
            logger.error(f"创建分类失败: {str(e)}", exc_info=True)
            return self.error(f"创建分类失败: {str(e)}")

    def update_category(self, fec_id: str, fproject_id: str, fid: str, **kwargs) -> Dict:
        """更新分类"""
        try:
            cat = WoCategory.active_query(self.db).filter(
                WoCategory.fid == fid, WoCategory.fec_id == fec_id,
                WoCategory.fproject_id == fproject_id
            ).first()
            if not cat:
                return self.error("分类不存在", 404)
            self.begin()
            for key in ["fcategory_name", "fcategory_code", "fcategory_type",
                        "ficon", "fsort_order", "fdescription", "fis_enabled"]:
                if key in kwargs:
                    setattr(cat, key, kwargs[key])
            self.commit()
            return self.success(self._category_to_dict(cat), message="分类更新成功")
        except Exception as e:
            self.rollback()
            logger.error(f"更新分类失败: {str(e)}", exc_info=True)
            return self.error(f"更新分类失败: {str(e)}")

    def delete_category(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        """删除分类"""
        try:
            cat = WoCategory.active_query(self.db).filter(
                WoCategory.fid == fid, WoCategory.fec_id == fec_id,
                WoCategory.fproject_id == fproject_id
            ).first()
            if not cat:
                return self.error("分类不存在", 404)
            self.begin()
            cat.is_deleted = 1
            self.commit()
            return self.success(message="分类已删除")
        except Exception as e:
            self.rollback()
            logger.error(f"删除分类失败: {str(e)}", exc_info=True)
            return self.error(f"删除分类失败: {str(e)}")

    @staticmethod
    def _sla_to_dict(r: WoSlaRule) -> dict:
        return {
            "fid": r.fid, "rule_name": r.frule_name, "sla_level": r.fsla_level,
            "level_name": r.flevel_name, "priority": r.fpriority,
            "response_minutes": r.fresponse_minutes, "complete_hours": r.fcomplete_hours,
            "escalate_minutes": r.fescalate_minutes, "escalate_count": r.fescalate_count,
            "escalate_to": r.fescalate_to, "is_enabled": r.fis_enabled,
        }

    @staticmethod
    def _dispatch_to_dict(r: WoDispatchRule) -> dict:
        return {
            "fid": r.fid, "rule_name": r.frule_name, "rule_type": r.frule_type,
            "match_condition": json.loads(r.fmatch_condition) if r.fmatch_condition else {},
            "dispatch_action": r.fdispatch_action,
            "dispatch_target": json.loads(r.fdispatch_target) if r.fdispatch_target else {},
            "priority": r.fpriority, "is_enabled": r.fis_enabled,
        }

    @staticmethod
    def _category_to_dict(c: WoCategory) -> dict:
        return {
            "fid": c.fid, "parent_id": c.fparent_id,
            "category_name": c.fcategory_name, "category_code": c.fcategory_code,
            "category_type": c.fcategory_type, "icon": c.ficon,
            "sort_order": c.fsort_order, "description": c.fdescription,
        }
