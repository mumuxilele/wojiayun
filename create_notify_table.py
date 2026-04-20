#!/usr/bin/env python3
import sys
sys.path.insert(0, '/www/wwwroot/wojiayun')

from business_common.db import get_db

db = get_db()

try:
    db.execute('''CREATE TABLE IF NOT EXISTS business_notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        title VARCHAR(200) NOT NULL DEFAULT '',
        content TEXT,
        type VARCHAR(50) DEFAULT 'system',
        is_read TINYINT DEFAULT 0,
        related_id INT DEFAULT NULL,
        related_type VARCHAR(50) DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
    print('Table business_notifications created OK')
except Exception as e:
    print(f'Error: {e}')
