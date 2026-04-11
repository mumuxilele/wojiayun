#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V33.0 验证脚本"""
import sys
import os
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("V33.0 Gongneng Yanzheng")
print("=" * 50)

# 1. Verify Invoice Service
print("\n1. Yanzheng Fapiao Fuwu...")
try:
    from business_common.invoice_service import invoice_service, InvoiceService
    print("   [OK] InvoiceService Daoru Chengong")
    print(f"   - SERVICE_NAME: {invoice_service.SERVICE_NAME}")
    print(f"   - TITLE_TYPES: {InvoiceService.TITLE_TYPES}")
    print(f"   - INVOICE_TYPES: {InvoiceService.INVOICE_TYPES}")
    print(f"   - STATUS_PENDING: {InvoiceService.STATUS_PENDING}")
except Exception as e:
    print(f"   [FAIL] Fapiao Fuwu Daoru Shibai: {e}")

# 2. Verify Backup Service
print("\n2. Yanzheng Beifen Fuwu...")
try:
    from business_common.backup_service import backup_service, BackupService
    print("   [OK] BackupService Daoru Chengong")
    print(f"   - SERVICE_NAME: {backup_service.SERVICE_NAME}")
    print(f"   - BACKUP_TYPE_FULL: {BackupService.BACKUP_TYPE_FULL}")
    print(f"   - BACKUP_TYPE_INCREMENTAL: {BackupService.BACKUP_TYPE_INCREMENTAL}")
except Exception as e:
    print(f"   [FAIL] Beifen Fuwu Daoru Shibai: {e}")

# 3. Verify Task Queue Service
print("\n3. Yanzheng Renwu Duidlie Fuwu...")
try:
    from business_common.task_queue_service import task_queue_service, TaskQueueService
    print("   [OK] TaskQueueService Daoru Chengong")
    print(f"   - SERVICE_NAME: {task_queue_service.SERVICE_NAME}")
    print(f"   - TASK_TYPES: {list(TaskQueueService.TASK_TYPES.keys())}")
    print(f"   - MAX_RETRIES: {TaskQueueService.MAX_RETRIES}")
except Exception as e:
    print(f"   [FAIL] Renwu Duidlie Fuwu Daoru Shibai: {e}")

# 4. Verify Database Tables
print("\n4. Yanzheng Shujuku Biao...")
try:
    from business_common import db
    tables_to_check = [
        'business_invoice_titles',
        'business_invoices',
        'business_tasks',
        'business_backups'
    ]
    for table in tables_to_check:
        result = db.get_one(f"""
            SELECT COUNT(*) as cnt FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_name = '{table}'
        """)
        if result and result.get('cnt', 0) > 0:
            print(f"   [OK] {table} Biao Cunzai")
        else:
            print(f"   [FAIL] {table} Biao Bu Cunzai")
except Exception as e:
    print(f"   [FAIL] Shujuku Yanzheng Shibai: {e}")

# 5. Verify Invoice Number Generation
print("\n5. Yanzheng Fapiao Hao Shengcheng...")
try:
    invoice_no = invoice_service._generate_invoice_no()
    print(f"   [OK] Fapiao Hao Shengcheng: {invoice_no}")
except Exception as e:
    print(f"   [FAIL] Fapiao Hao Shengcheng Shibai: {e}")

# 6. Verify Task ID Generation
print("\n6. Yanzheng Renwu ID Shengcheng...")
try:
    task_id = task_queue_service._generate_task_id()
    print(f"   [OK] Renwu ID Shengcheng: {task_id}")
except Exception as e:
    print(f"   [FAIL] Renwu ID Shengcheng Shibai: {e}")

# 7. Verify Backup ID Generation
print("\n7. Yanzheng Beifen ID Shengcheng...")
try:
    backup_id = backup_service._generate_backup_id()
    print(f"   [OK] Beifen ID Shengcheng: {backup_id}")
except Exception as e:
    print(f"   [FAIL] Beifen ID Shengcheng Shibai: {e}")

print("\n" + "=" * 50)
print("Yanzheng Wancheng")
print("=" * 50)
