# service/wo_template_service.py - 工单模板管理服务
import json
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from service.base_service import BaseService
from db.models.wo_template import WoTemplate, WoTemplateItem
from utils.md5_fid_util import generate_fid
from utils.log_util import logger


class WoTemplateService(BaseService):
    """工单模板管理服务"""

    def list_templates(self, fec_id: str, fproject_id: str,
                       wo_type: str = "", status: str = "",
                       keyword: str = "", page: int = 1, page_size: int = 20) -> Dict:
        """获取模板列表"""
        try:
            q = WoTemplate.active_query(self.db).filter(
                WoTemplate.fec_id == fec_id,
                WoTemplate.fproject_id == fproject_id
            )
            if wo_type:
                q = q.filter(WoTemplate.fwo_type == wo_type)
            if status:
                q = q.filter(WoTemplate.fstatus == status)
            if keyword:
                q = q.filter(
                    or_(
                        WoTemplate.ftemplate_name.like(f"%{keyword}%"),
                        WoTemplate.ftemplate_code.like(f"%{keyword}%"),
                    )
                )
            q = q.order_by(WoTemplate.fsort_order.asc(), WoTemplate.create_time.desc())
            total = q.count()
            items = q.offset((page - 1) * page_size).limit(page_size).all()
            return self.success({
                "total": total, "page": page, "page_size": page_size,
                "items": [self._template_to_dict(t) for t in items]
            })
        except Exception as e:
            logger.error(f"查询模板列表失败: {str(e)}", exc_info=True)
            return self.error(f"查询模板列表失败: {str(e)}")

    def get_template(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        """获取模板详情(含检查项)"""
        try:
            tpl = WoTemplate.active_query(self.db).filter(
                WoTemplate.fid == fid,
                WoTemplate.fec_id == fec_id,
                WoTemplate.fproject_id == fproject_id
            ).first()
            if not tpl:
                return self.error("模板不存在", 404)
            data = self._template_to_dict(tpl)
            # 查询检查项
            items = WoTemplateItem.active_query(self.db).filter(
                WoTemplateItem.ftemplate_id == fid,
                WoTemplateItem.is_deleted == 0
            ).order_by(WoTemplateItem.fsort_order.asc()).all()
            data["items"] = [self._item_to_dict(i) for i in items]
            return self.success(data)
        except Exception as e:
            logger.error(f"查询模板详情失败: {str(e)}", exc_info=True)
            return self.error(f"查询模板详情失败: {str(e)}")

    def create_template(self, fec_id: str, fproject_id: str, **kwargs) -> Dict:
        """创建模板"""
        try:
            self.begin()
            tpl = WoTemplate(
                fid=generate_fid(),
                fec_id=fec_id,
                fproject_id=fproject_id,
                ftemplate_name=kwargs.get("ftemplate_name", ""),
                ftemplate_code=kwargs.get("ftemplate_code", ""),
                fcategory_id=kwargs.get("fcategory_id", ""),
                fwo_type=kwargs.get("fwo_type", "quality"),
                fdescription=kwargs.get("fdescription", ""),
                fscope_type=kwargs.get("fscope_type", "project"),
                fscope_config=json.dumps(kwargs.get("fscope_config", {}), ensure_ascii=False),
                fcycle_type=kwargs.get("fcycle_type", "daily"),
                fcycle_value=kwargs.get("fcycle_value", 1),
                fexecute_time=kwargs.get("fexecute_time", "08:00"),
                fsla_level=kwargs.get("fsla_level", "L3"),
                fexecutor_config=json.dumps(kwargs.get("fexecutor_config", {}), ensure_ascii=False),
                fstatus=kwargs.get("fstatus", "active"),
                fversion=1,
                fremark=kwargs.get("fremark", ""),
                fcreate_user_id=kwargs.get("fcreate_user_id", ""),
            )
            self.db.add(tpl)

            # 创建检查项
            items = kwargs.get("items", [])
            for idx, item in enumerate(items):
                ti = WoTemplateItem(
                    fid=generate_fid(),
                    fec_id=fec_id,
                    fproject_id=fproject_id,
                    ftemplate_id=tpl.fid,
                    fitem_name=item.get("fitem_name", ""),
                    fitem_code=item.get("fitem_code", ""),
                    fitem_type=item.get("fitem_type", "check"),
                    fscore_weight=item.get("fscore_weight", 0),
                    fpass_score=item.get("fpass_score", 60),
                    foptions=json.dumps(item.get("foptions", []), ensure_ascii=False) if item.get("foptions") else None,
                    fsort_order=item.get("fsort_order", idx),
                    fis_required=item.get("fis_required", 1),
                    fremark=item.get("fremark", ""),
                )
                self.db.add(ti)

            self.commit()
            return self.success(self._template_to_dict(tpl), message="模板创建成功")
        except Exception as e:
            self.rollback()
            logger.error(f"创建模板失败: {str(e)}", exc_info=True)
            return self.error(f"创建模板失败: {str(e)}")

    def update_template(self, fec_id: str, fproject_id: str, fid: str, **kwargs) -> Dict:
        """更新模板"""
        try:
            tpl = WoTemplate.active_query(self.db).filter(
                WoTemplate.fid == fid,
                WoTemplate.fec_id == fec_id,
                WoTemplate.fproject_id == fproject_id
            ).first()
            if not tpl:
                return self.error("模板不存在", 404)

            self.begin()
            updatable = [
                "ftemplate_name", "ftemplate_code", "fcategory_id", "fwo_type",
                "fdescription", "fscope_type", "fcycle_type", "fcycle_value",
                "fexecute_time", "fsla_level", "fstatus", "fremark"
            ]
            for key in updatable:
                if key in kwargs:
                    setattr(tpl, key, kwargs[key])
            if "fscope_config" in kwargs:
                tpl.fscope_config = json.dumps(kwargs["fscope_config"], ensure_ascii=False)
            if "fexecutor_config" in kwargs:
                tpl.fexecutor_config = json.dumps(kwargs["fexecutor_config"], ensure_ascii=False)

            self.commit()
            return self.success(self._template_to_dict(tpl), message="模板更新成功")
        except Exception as e:
            self.rollback()
            logger.error(f"更新模板失败: {str(e)}", exc_info=True)
            return self.error(f"更新模板失败: {str(e)}")

    def delete_template(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        """删除模板(软删除)"""
        try:
            tpl = WoTemplate.active_query(self.db).filter(
                WoTemplate.fid == fid,
                WoTemplate.fec_id == fec_id,
                WoTemplate.fproject_id == fproject_id
            ).first()
            if not tpl:
                return self.error("模板不存在", 404)
            self.begin()
            tpl.is_deleted = 1
            tpl.delete_time = __import__("utils.time_util", fromlist=["now"]).now()
            self.commit()
            return self.success(message="模板已删除")
        except Exception as e:
            self.rollback()
            logger.error(f"删除模板失败: {str(e)}", exc_info=True)
            return self.error(f"删除模板失败: {str(e)}")

    @staticmethod
    def _template_to_dict(t: WoTemplate) -> dict:
        return {
            "fid": t.fid, "template_name": t.ftemplate_name,
            "template_code": t.ftemplate_code, "category_id": t.fcategory_id,
            "wo_type": t.fwo_type, "description": t.fdescription,
            "scope_type": t.fscope_type,
            "scope_config": json.loads(t.fscope_config) if t.fscope_config else {},
            "cycle_type": t.fcycle_type, "cycle_value": t.fcycle_value,
            "execute_time": t.fexecute_time, "sla_level": t.fsla_level,
            "executor_config": json.loads(t.fexecutor_config) if t.fexecutor_config else {},
            "status": t.fstatus, "version": t.version,
            "create_time": t.create_time.strftime("%Y-%m-%d %H:%M:%S") if t.create_time else "",
        }

    @staticmethod
    def _item_to_dict(i: WoTemplateItem) -> dict:
        return {
            "fid": i.fid, "item_name": i.fitem_name, "item_code": i.fitem_code,
            "item_type": i.fitem_type, "score_weight": float(i.fscore_weight) if i.fscore_weight else 0,
            "pass_score": float(i.fpass_score) if i.fpass_score else 60,
            "options": json.loads(i.foptions) if i.foptions else [],
            "sort_order": i.fsort_order, "is_required": i.fis_required,
            "remark": i.fremark,
        }
