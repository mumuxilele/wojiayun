#!/usr/bin/env python3
import os
print(f"__file__: {__file__}")
print(f"dirname(__file__): {os.path.dirname(__file__)}")
print(f"dirname(dirname(__file__)): {os.path.dirname(os.path.dirname(__file__))}")
common_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'business-common')
print(f"common_dir: {common_dir}")
print(f"exists: {os.path.exists(common_dir)}")
if os.path.exists(common_dir):
    print(f"list: {os.listdir(common_dir)[:5]}")
