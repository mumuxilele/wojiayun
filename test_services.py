#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = []

try:
    import importlib
    mod = importlib.import_module('business-common.invoice_service')
    results.append("[OK] InvoiceService: " + mod.invoice_service.SERVICE_NAME)
except Exception as e:
    results.append("[FAIL] InvoiceService: " + str(e))

try:
    mod = importlib.import_module('business-common.backup_service')
    results.append("[OK] BackupService: " + mod.backup_service.SERVICE_NAME)
except Exception as e:
    results.append("[FAIL] BackupService: " + str(e))

try:
    mod = importlib.import_module('business-common.task_queue_service')
    results.append("[OK] TaskQueueService: " + mod.task_queue_service.SERVICE_NAME)
except Exception as e:
    results.append("[FAIL] TaskQueueService: " + str(e))

with open('service_test_results.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))
