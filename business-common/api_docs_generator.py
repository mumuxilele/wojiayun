#!/usr/bin/env python3
"""
API文档自动生成工具 - V17.0新增
功能：
  1. 自动扫描Flask路由，生成OpenAPI 3.0规范文档
  2. 支持用户端/员工端/管理端三套API
  3. 输出JSON格式供Swagger UI使用

使用方法：
  python business-common/api_docs_generator.py [--output ./output]
"""
import os
import sys
import re
import json
from datetime import datetime

# 项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_flask_routes(app_path):
    """解析Flask应用的路由"""
    routes = []
    
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 匹配路由装饰器
    route_pattern = r"@app\.route\(['\"]([^'\"]+)['\"](?:,\s*methods=\[([^\]]+)\])?\)"
    method_pattern = r"def\s+(\w+)\s*\([^)]*\):\s*\"\"\"([^\"]*?)\"\"\""
    
    # 找到所有路由定义
    route_matches = list(re.finditer(route_pattern, content))
    
    for i, match in enumerate(route_matches):
        path = match.group(1)
        methods_str = match.group(2) or "'GET'"
        
        # 解析方法列表
        methods = []
        for m in re.finditer(r"['\"](\w+)['\"]", methods_str):
            methods.append(m.group(1))
        
        # 查找对应的函数定义（在装饰器之后的下一个函数）
        start_pos = match.end()
        
        # 查找函数定义
        func_pattern = r"def\s+(\w+)\s*\(([^)]*)\):"
        func_match = re.search(func_pattern, content[start_pos:start_pos + 2000])
        
        if func_match:
            func_name = func_match.group(1)
            func_start = start_pos + func_match.start()
            func_end = content.find('\n\n', func_start)
            if func_end == -1:
                func_end = func_start + 2000
            
            func_block = content[func_start:func_end]
            
            # 提取文档字符串
            docstring = ""
            doc_match = re.search(r'"""(.*?)"""', func_block, re.DOTALL)
            if doc_match:
                docstring = doc_match.group(1).strip()
            
            # 提取参数
            params = []
            param_match = re.search(r'def\s+\w+\s*\(([^)]*)\)', func_block)
            if param_match:
                param_str = param_match.group(1)
                for p in param_str.split(','):
                    p = p.strip()
                    if p and not p.startswith('*'):
                        if '=' in p:
                            param_name = p.split('=')[0].strip()
                        else:
                            param_name = p.strip()
                        if param_name and param_name not in ('self', 'cls'):
                            params.append(param_name)
            
            # 生成路由信息
            route_info = {
                'path': path,
                'methods': methods,
                'function': func_name,
                'description': docstring.split('\n')[0] if docstring else '',
                'summary': docstring.split('\n')[0] if docstring else '',
                'parameters': params,
                'authenticated': 'require_' in content[func_start:func_start + 500] if func_start > 0 else False
            }
            routes.append(route_info)
    
    return routes


def generate_openapi_spec(routes, title, version, description):
    """生成OpenAPI 3.0规范文档"""
    spec = {
        'openapi': '3.0.3',
        'info': {
            'title': title,
            'description': description,
            'version': version,
            'contact': {
                'name': '技术支持',
                'email': 'support@wojiayun.com'
            }
        },
        'servers': [
            {
                'url': '/',
                'description': '当前服务'
            }
        ],
        'paths': {},
        'components': {
            'securitySchemes': {
                'BearerAuth': {
                    'type': 'http',
                    'scheme': 'bearer',
                    'bearerFormat': 'JWT',
                    'description': '在请求头中传递Token: Token YOUR_TOKEN'
                }
            },
            'schemas': {
                'ApiResponse': {
                    'type': 'object',
                    'properties': {
                        'success': {
                            'type': 'boolean',
                            'description': '请求是否成功'
                        },
                        'msg': {
                            'type': 'string',
                            'description': '返回消息'
                        },
                        'data': {
                            'type': 'object',
                            'description': '返回数据'
                        }
                    }
                },
                'Error': {
                    'type': 'object',
                    'properties': {
                        'success': {
                            'type': 'boolean',
                            'example': False
                        },
                        'msg': {
                            'type': 'string',
                            'example': '错误信息'
                        }
                    }
                }
            }
        },
        'tags': []
    }
    
    # 按路径前缀分组
    path_groups = {}
    for route in routes:
        path = route['path']
        
        # 提取标签
        if path.startswith('/api/user'):
            tag = '用户端API'
        elif path.startswith('/api/staff'):
            tag = '员工端API'
        elif path.startswith('/api/admin'):
            tag = '管理端API'
        elif path.startswith('/api/'):
            tag = '公共API'
        else:
            tag = '其他'
        
        if tag not in path_groups:
            path_groups[tag] = []
            spec['tags'].append({'name': tag, 'description': f'{tag}接口文档'})
        
        # 构建路径
        path_key = path
        if path_key not in spec['paths']:
            spec['paths'][path_key] = {}
        
        # 构建操作
        for method in route['methods']:
            method_lower = method.lower()
            spec['paths'][path_key][method_lower] = {
                'tags': [tag],
                'summary': route.get('summary', ''),
                'description': route.get('description', ''),
                'operationId': route.get('function', ''),
                'parameters': [],
                'requestBody': {},
                'responses': {
                    '200': {
                        'description': '成功',
                        'content': {
                            'application/json': {
                                'schema': {
                                    '$ref': '#/components/schemas/ApiResponse'
                                }
                            }
                        }
                    },
                    '401': {
                        'description': '未授权',
                        'content': {
                            'application/json': {
                                'schema': {
                                    '$ref': '#/components/schemas/Error'
                                }
                            }
                        }
                    }
                }
            }
            
            # 添加认证信息
            if route.get('authenticated'):
                spec['paths'][path_key][method_lower]['security'] = [{'BearerAuth': []}]
            
            # 添加路径参数
            path_params = re.findall(r'<(\w+)(?::[^>]+)?>', path)
            for param in path_params:
                spec['paths'][path_key][method_lower]['parameters'].append({
                    'name': param,
                    'in': 'path',
                    'required': True,
                    'schema': {
                        'type': 'string'
                    },
                    'description': f'路径参数: {param}'
                })
            
            # 添加查询参数检测（基于函数参数）
            func_params = route.get('parameters', [])
            for param in func_params:
                if param not in path_params and param != 'user':
                    spec['paths'][path_key][method_lower]['parameters'].append({
                        'name': param,
                        'in': 'query',
                        'required': False,
                        'schema': {
                            'type': 'string'
                        },
                        'description': f'查询参数: {param}'
                    })
    
    return spec


def generate_api_docs():
    """生成所有API文档"""
    apps = [
        {
            'name': '用户端H5',
            'file': os.path.join(PROJECT_ROOT, 'business-userH5', 'app.py'),
            'title': '社区商业 - 用户端API',
            'version': '1.0.0',
            'description': '用户端H5移动应用接口文档，包含用户中心、订单、预约、会员等功能'
        },
        {
            'name': '员工端H5',
            'file': os.path.join(PROJECT_ROOT, 'business-staffH5', 'app.py'),
            'title': '社区商业 - 员工端API',
            'version': '1.0.0',
            'description': '员工端H5移动应用接口文档，包含申请处理、订单管理、预约核销等功能'
        },
        {
            'name': '管理端PC',
            'file': os.path.join(PROJECT_ROOT, 'business-admin', 'app.py'),
            'title': '社区商业 - 管理端API',
            'version': '1.0.0',
            'description': '管理端PC Web应用接口文档，包含数据统计、用户管理、门店管理、商品管理等功能'
        }
    ]
    
    output_dir = os.path.join(PROJECT_ROOT, 'api-docs')
    os.makedirs(output_dir, exist_ok=True)
    
    all_docs = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': 'V17.0',
        'apps': []
    }
    
    for app in apps:
        print(f"正在生成 {app['name']} API文档...")
        
        if not os.path.exists(app['file']):
            print(f"  [跳过] 文件不存在: {app['file']}")
            continue
        
        routes = parse_flask_routes(app['file'])
        spec = generate_openapi_spec(routes, app['title'], app['version'], app['description'])
        
        # 输出JSON文件
        output_file = os.path.join(output_dir, f"{app['name']}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)
        print(f"  [生成] {output_file}")
        
        # 生成Markdown文档
        md_file = os.path.join(output_dir, f"{app['name']}.md")
        generate_markdown_doc(spec, md_file, app['title'])
        print(f"  [生成] {md_file}")
        
        all_docs['apps'].append({
            'name': app['name'],
            'title': app['title'],
            'routes_count': len(routes),
            'json_file': output_file,
            'md_file': md_file
        })
    
    # 生成汇总文档
    summary_file = os.path.join(output_dir, 'SUMMARY.md')
    generate_summary_doc(all_docs, summary_file)
    
    print(f"\nAPI文档生成完成！")
    print(f"输出目录: {output_dir}")
    print(f"共计 {len(all_docs['apps'])} 个应用的API文档")
    
    return all_docs


def generate_markdown_doc(spec, output_file, title):
    """生成Markdown格式的API文档"""
    md = []
    md.append(f"# {title}\n")
    md.append(f"**版本**: {spec.get('info', {}).get('version', '1.0.0')}\n")
    md.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    md.append("---\n\n")
    md.append("## 概述\n\n")
    md.append(f"{spec.get('info', {}).get('description', '')}\n\n")
    md.append("---\n\n")
    md.append("## 认证说明\n\n")
    md.append("大多数API接口需要认证，请在请求头中携带Token：\n")
    md.append("```\n")
    md.append("Token: YOUR_ACCESS_TOKEN\n")
    md.append("```\n\n")
    md.append("---\n\n")
    
    # 按标签分组
    paths_by_tag = {}
    for path, methods in spec.get('paths', {}).items():
        for method, operation in methods.items():
            tags = operation.get('tags', ['其他'])
            tag = tags[0]
            if tag not in paths_by_tag:
                paths_by_tag[tag] = []
            paths_by_tag[tag].append((path, method, operation))
    
    for tag, items in paths_by_tag.items():
        md.append(f"## {tag}\n\n")
        
        for path, method, operation in sorted(items):
            method_upper = method.upper()
            md.append(f"### `{method_upper} {path}`\n\n")
            md.append(f"**摘要**: {operation.get('summary', '')}\n\n")
            
            if operation.get('description'):
                md.append(f"**描述**: {operation.get('description', '')}\n\n")
            
            # 参数
            params = operation.get('parameters', [])
            if params:
                md.append("**参数**:\n\n")
                md.append("| 参数名 | 位置 | 类型 | 必填 | 描述 |\n")
                md.append("|--------|------|------|------|------|\n")
                for param in params:
                    required = '是' if param.get('required') else '否'
                    md.append(f"| {param.get('name', '')} | {param.get('in', '')} | {param.get('schema', {}).get('type', 'string')} | {required} | {param.get('description', '')} |\n")
                md.append("\n")
            
            # 认证
            if operation.get('security'):
                md.append("**认证**: 需要Token\n\n")
            
            # 响应
            md.append("**响应示例**:\n\n")
            md.append("```json\n")
            md.append('{"success": true, "msg": "操作成功", "data": {}}\n')
            md.append("```\n\n")
            md.append("---\n\n")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(md))


def generate_summary_doc(docs, output_file):
    """生成汇总文档"""
    md = []
    md.append("# API文档汇总\n\n")
    md.append(f"**生成时间**: {docs.get('generated_at', '')}\n")
    md.append(f"**版本**: {docs.get('version', '')}\n\n")
    md.append("---\n\n")
    md.append("## 文档列表\n\n")
    md.append("| 应用 | 接口数 | JSON | Markdown |\n")
    md.append("|------|--------|------|----------|\n")
    
    total_routes = 0
    for app in docs.get('apps', []):
        md.append(f"| {app.get('name', '')} | {app.get('routes_count', 0)} | [查看]({app.get('json_file', '')}) | [查看]({app.get('md_file', '')}) |\n")
        total_routes += app.get('routes_count', 0)
    
    md.append(f"\n**总计**: {len(docs.get('apps', []))} 个应用，{total_routes} 个接口\n\n")
    md.append("---\n\n")
    md.append("## 使用说明\n\n")
    md.append("### Swagger UI\n\n")
    md.append("1. 安装Swagger UI\n")
    md.append("2. 加载JSON格式的OpenAPI文档\n")
    md.append("3. 在线测试API接口\n\n")
    md.append("### 在线工具\n\n")
    md.append("- [Swagger Editor](https://editor.swagger.io/) - 在线API设计工具\n")
    md.append("- [Postman](https://www.postman.com/) - API调试工具\n\n")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(md))


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='API文档自动生成工具')
    parser.add_argument('--output', '-o', default='./api-docs', help='输出目录')
    parser.add_argument('--format', '-f', choices=['json', 'md', 'all'], default='all', help='输出格式')
    args = parser.parse_args()
    
    generate_api_docs()
