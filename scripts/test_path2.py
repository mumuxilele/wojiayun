#!/usr/bin/env python3
import os
base = os.path.dirname(os.path.abspath("app.py"))
print("base:", base)
print("common:", os.path.join(os.path.dirname(base), "business-common"))
print("exists:", os.path.exists(os.path.join(os.path.dirname(base), "business-common")))
