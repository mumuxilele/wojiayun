#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='localhost', port=3306, user='root',
    password='Wojiacloud$2023', database='visit_system', charset='utf8mb4'
)
cur = conn.cursor(pymysql.cursors.DictCursor)
cur.execute("SELECT form_schema FROM business_application_types WHERE type_code='overtime'")
row = cur.fetchone()
print('Raw form_schema value:', repr(row['form_schema']))
print('Type:', type(row['form_schema']))

import json
if isinstance(row['form_schema'], str):
    parsed = json.loads(row['form_schema'])
    print('Parsed fields:', len(parsed.get('fields', [])))
elif isinstance(row['form_schema'], dict):
    print('Already a dict, keys:', list(row['form_schema'].keys()))

conn.close()
