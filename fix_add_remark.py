#!/usr/bin/env python3
"""添加remark字段到business_applications表"""
import sys
sys.path.insert(0, '/www/wwwroot/wojiayun')
from business_common import db

try:
    db.execute("ALTER TABLE business_applications ADD COLUMN remark TEXT NULL COMMENT '备注' AFTER form_data")
    print("remark字段添加成功")
except Exception as e:
    if "Duplicate column" in str(e):
        print("remark字段已存在")
    else:
        print(f"添加字段失败: {e}")
