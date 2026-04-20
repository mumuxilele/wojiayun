#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import jsonify
import json

# Test the dict syntax
d = {'success': True, 'data': {'stats': [], 'total': 0, 'overview': {}}}
print(json.dumps(d))
print("OK")
