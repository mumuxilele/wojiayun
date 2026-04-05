import os
import sys
import importlib
import importlib.abc
import importlib.util
import types

# 项目根目录
_project_root = r'C:\Users\kingdee\WorkBuddy\Claw\wojiayun'
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Python不支持连字符作为模块名(business-common -> business_common)
# 使用自定义finder/loader映射
_alias_map = {
    'business_common': 'business-common',
    'business_admin': 'business-admin',
    'business_staffH5': 'business-staffH5',
    'business_userH5': 'business-userH5',
}

class _AliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        parts = fullname.split('.')
        alias = parts[0]
        if alias in _alias_map:
            real_dir = os.path.join(_project_root, _alias_map[alias])
            if not os.path.isdir(real_dir):
                return None
            if len(parts) == 1:
                init_path = os.path.join(real_dir, '__init__.py')
                if not os.path.exists(init_path):
                    return None
                spec = importlib.util.spec_from_file_location(
                    fullname, init_path,
                    submodule_search_locations=[real_dir]
                )
                spec.loader = _AliasLoader()
                return spec
            else:
                # 子模块查找 - 确保path包含正确的目录
                module_name = parts[-1]
                file_path = os.path.join(real_dir, module_name + '.py')
                if os.path.exists(file_path):
                    spec = importlib.util.spec_from_file_location(fullname, file_path)
                    spec.loader = _AliasLoader()
                    return spec
        return None

    def find_module(self, fullname, path=None):
        """Python 3.3 compatibility"""
        spec = self.find_spec(fullname, path)
        if spec:
            return _AliasLoader()
        return None

class _AliasLoader(importlib.abc.Loader):
    def load_module(self, fullname):
        parts = fullname.split('.')
        alias = parts[0]
        real_dir = os.path.join(_project_root, _alias_map[alias])
        if len(parts) == 1:
            # 顶级包
            init_path = os.path.join(real_dir, '__init__.py')
            spec = importlib.util.spec_from_file_location(fullname, init_path,
                submodule_search_locations=[real_dir])
            mod = importlib.util.module_from_spec(spec)
            sys.modules[fullname] = mod
            spec.loader.exec_module(mod)
            return mod
        else:
            # 子模块
            parent_name = '.'.join(parts[:-1])
            if parent_name not in sys.modules:
                __import__(parent_name)
            parent = sys.modules[parent_name]
            module_name = parts[-1]
            # 查找 .py 文件
            file_path = os.path.join(real_dir, module_name + '.py')
            if os.path.exists(file_path):
                spec = importlib.util.spec_from_file_location(fullname, file_path)
                mod = importlib.util.module_from_spec(spec)
                sys.modules[fullname] = mod
                setattr(parent, module_name, mod)
                spec.loader.exec_module(mod)
                return mod
        raise ImportError(f"No module named {fullname}")

sys.meta_path.insert(0, _AliasFinder())
