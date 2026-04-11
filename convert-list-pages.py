#!/usr/bin/env python3
"""
列表页面样式批量转换脚本
将原有列表页面转换为参考文件的Element UI样式

使用方法:
    python convert-list-pages.py <input_file> [output_file]
    
示例:
    python convert-list-pages.py business-admin/users.html
    python convert-list-pages.py business-staffH5/members.html
"""

import re
import sys
import os

def extract_title(content):
    """提取页面标题"""
    match = re.search(r'<title>(.*?)</title>', content)
    return match.group(1) if match else '列表页面'

def extract_api_endpoint(content):
    """提取API端点"""
    match = re.search(r"url\s*=\s*['\"](/api/[^'\"]+)", content)
    return match.group(1) if match else '/api/admin/list'

def extract_columns(content):
    """提取表格列定义"""
    # 匹配表头th
    th_pattern = r'<th[^>]*>(.*?)</th>'
    ths = re.findall(th_pattern, content, re.DOTALL)
    columns = []
    for th in ths:
        # 清理标签
        text = re.sub(r'<[^>]+>', '', th).strip()
        if text:
            columns.append(text)
    return columns

def create_new_structure(title, content):
    """创建新的页面结构"""
    
    # 提取原有的JS逻辑
    js_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
    original_js = js_match.group(1) if js_match else ''
    
    # 提取原有的弹窗HTML
    modal_match = re.search(r'<!--.*弹窗.*-->(.*?)<script>', content, re.DOTALL)
    modal_html = modal_match.group(1) if modal_match else ''
    
    # 提取标题（去掉emoji）
    clean_title = re.sub(r'[^\w\s\-\u4e00-\u9fff]', '', title).strip()
    
    new_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="../business-common/list-style.css">
    <style>
        /* 页面特有样式 */
        .actions .link {{ color: var(--el-color-primary); cursor: pointer; margin-right: 10px; }}
        .actions .link:hover {{ text-decoration: underline; }}
        .actions .link.danger {{ color: var(--el-color-danger); }}
        /* 弹窗样式保留 */
        {extract_modal_styles(content)}
    </style>
</head>
<body class="wy-design-list">
    <!-- 顶部区域 -->
    <div class="wy-design-list_top">
        <div class="wy-design-list_top_title">
            <h1 class="wy-design-list_title">{title}</h1>
            <div class="wy-design-list_space"></div>
            <div class="wy-design-list_btn-group">
                <div class="wy-design-list_btn">
                    <button type="button" class="el-button el-button--primary el-button--small" onclick="loadList(1)">
                        <span>搜索</span>
                    </button>
                </div>
                <div class="wy-design-list_btn">
                    <button type="button" class="el-button el-button--small" onclick="resetSearch()">
                        <span>重置</span>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- 筛选区域 -->
    <div class="wy-design-list_filter">
        {extract_filters(content)}
    </div>

    <!-- 表格区域 -->
    <div class="wy-design-table wy-design-table_main wy-design-table_has-bar">
        <div class="wy-design-table_bar">
            <i class="wy-design-table_set el-icon-setting" title="列设置"></i>
            <span class="wy-design-table_total">共 <em id="totalCount">0</em> 条</span>
            <div class="wy-pages">
                <div class="wy-pages_total">第<em id="currentPage">1</em>/<em id="totalPages">1</em>页</div>
                <div class="wy-pages_prev el-icon-arrow-left" id="prevBtn" onclick="changePage(-1)"></div>
                <div class="wy-pages_next el-icon-arrow-right" id="nextBtn" onclick="changePage(1)"></div>
            </div>
        </div>
        <table class="el-table el-table--fit el-table--border el-table--enable-row-hover">
            <thead class="el-table__header">
                <tr>
                    {generate_table_headers(content)}
                </tr>
            </thead>
            <tbody class="el-table__body" id="listBody">
                <tr><td colspan="10" style="text-align: center; padding: 60px; color: var(--el-text-secondary);">加载中...</td></tr>
            </tbody>
        </table>
    </div>

    {modal_html}

    <script>
    {convert_js_logic(original_js)}
    </script>
</body>
</html>'''
    return new_html

def extract_modal_styles(content):
    """提取弹窗样式"""
    style_match = re.search(r'(/\*.*弹窗.*\*/|\.modal-overlay|\.modal)[^}]+\{[^}]+\}', content)
    return style_match.group(0) if style_match else '''
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,.45); z-index: 200; }
        .modal { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%); background: var(--el-bg-white); border-radius: 4px; width: 580px; max-width: 95vw; max-height: 85vh; flex-direction: column; z-index: 201; box-shadow: 0 4px 20px rgba(0,0,0,.18); }
        .modal.show { display: flex; }
        .modal-header { padding: 16px 20px; border-bottom: 1px solid var(--el-border-color-light); display: flex; justify-content: space-between; align-items: center; }
        .modal-title { font-size: 16px; font-weight: 600; color: var(--el-text-primary); }
        .modal-close { background: none; border: none; width: 32px; height: 32px; border-radius: 4px; cursor: pointer; font-size: 16px; color: var(--el-text-secondary); display: flex; align-items: center; justify-content: center; }
        .modal-close:hover { background: var(--el-bg-light); }
        .modal-body { padding: 20px; overflow-y: auto; flex: 1; }
        .modal-footer { padding: 12px 20px; border-top: 1px solid var(--el-border-color-light); display: flex; justify-content: flex-end; gap: 10px; }'''

def extract_filters(content):
    """提取筛选条件"""
    filters = []
    
    # 匹配搜索输入框
    search_match = re.search(r'<input[^>]*(?:search|keyword|kw)[^>]*>', content, re.IGNORECASE)
    if search_match:
        input_tag = search_match.group(0)
        placeholder = re.search(r'placeholder=["\']([^"\']+)["\']', input_tag)
        ph = placeholder.group(1) if placeholder else '搜索关键词'
        id_match = re.search(r'id=["\']([^"\']+)["\']', input_tag)
        id_attr = id_match.group(1) if id_match else 'keyword'
        filters.append(f'''<div class="wy-design-list_other">
            <div class="el-input el-input--small" style="width: 200px;">
                <input type="text" id="{id_attr}" placeholder="{ph}" class="el-input__inner">
            </div>
        </div>''')
    
    # 匹配select下拉框
    select_pattern = r'<select[^>]*>(.*?)</select>'
    selects = re.findall(select_pattern, content, re.DOTALL | re.IGNORECASE)
    for select_content in selects[:3]:  # 最多取3个筛选条件
        options = re.findall(r'<option[^>]*>(.*?)</option>', select_content, re.IGNORECASE)
        if len(options) > 1:
            id_match = re.search(r'id=["\']([^"\']+)["\']', select_content)
            id_attr = id_match.group(1) if id_match else f'filter{len(filters)}'
            filters.append(f'''<div class="wy-design-list_other">
            <select id="{id_attr}" class="el-input__inner" style="width: 130px;">
                {re.sub(r'<select[^>]*>|</select>', '', select_content, flags=re.IGNORECASE)}
            </select>
        </div>''')
    
    return '\n        '.join(filters) if filters else '''<div class="wy-design-list_other">
            <div class="el-input el-input--small" style="width: 200px;">
                <input type="text" id="keyword" placeholder="搜索关键词" class="el-input__inner">
            </div>
        </div>'''

def generate_table_headers(content):
    """生成表格表头"""
    ths = re.findall(r'<th[^>]*>(.*?)</th>', content, re.DOTALL | re.IGNORECASE)
    headers = []
    for th in ths[:10]:  # 最多10列
        text = re.sub(r'<[^>]+>', '', th).strip()
        if text:
            headers.append(f'<th><div class="cell">{text}</div></th>')
    if not headers:
        headers = ['<th><div class="cell">名称</div></th>', '<th><div class="cell">操作</div></th>']
    return '\n                    '.join(headers)

def convert_js_logic(js_content):
    """转换JS逻辑"""
    # 保留原有的JS，但做一些必要的替换
    js = js_content.strip()
    
    # 替换分页显示逻辑
    js = re.sub(
        r"document\.getElementById\(['\"](?:pageInfo|pagination)['\"]\)\.textContent\s*=\s*`[^`]+`",
        "document.getElementById('totalCount').textContent = total; document.getElementById('currentPage').textContent = currentPage; document.getElementById('totalPages').textContent = totalPages",
        js
    )
    
    # 替换按钮disabled逻辑
    js = re.sub(
        r"document\.getElementById\(['\"](?:prevBtn|nextBtn)['\"]\)\.disabled\s*=\s*(true|false)",
        lambda m: f"document.getElementById('{m.group(0).split('\\\'')[1] if '\\\'' in m.group(0) else m.group(0).split('\"')[1]}').classList.toggle('disabled', {m.group(1)})",
        js
    )
    
    # 替换空数据提示
    js = js.replace(
        'class="empty">暂无数据',
        'style="text-align: center; padding: 60px; color: var(--el-text-secondary);">暂无数据'
    )
    js = js.replace(
        'class="empty">加载中',
        'style="text-align: center; padding: 60px; color: var(--el-text-secondary);">加载中'
    )
    
    return js

def convert_file(input_path, output_path=None):
    """转换单个文件"""
    if not os.path.exists(input_path):
        print(f"错误: 文件不存在 {input_path}")
        return False
    
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    title = extract_title(content)
    new_content = create_new_structure(title, content)
    
    if output_path is None:
        # 备份原文件
        backup_path = input_path + '.backup'
        os.rename(input_path, backup_path)
        output_path = input_path
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"转换完成: {input_path} -> {output_path}")
    return True

def batch_convert(directory):
    """批量转换目录下的所有HTML文件"""
    files_to_convert = []
    
    # 需要转换的列表页面文件模式
    list_page_patterns = [
        'orders.html', 'users.html', 'products.html', 'applications.html',
        'venues.html', 'shops.html', 'coupons.html', 'points.html',
        'refunds.html', 'feedback.html', 'notices.html', 'notifications.html',
        'promotions.html', 'group-buy.html', 'member-levels.html',
        'order_list.html', 'application_list.html', 'members.html',
        'bookings.html', 'checkin_stats.html', 'reviews.html',
        'statistics.html', 'favorites.html', 'my_coupons.html',
        'points_mall.html', 'addresses.html', 'shops.html'
    ]
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html') and any(pattern in file for pattern in list_page_patterns):
                input_path = os.path.join(root, file)
                try:
                    convert_file(input_path)
                    files_to_convert.append(file)
                except Exception as e:
                    print(f"转换失败 {file}: {e}")
    
    print(f"\n共转换 {len(files_to_convert)} 个文件:")
    for f in files_to_convert:
        print(f"  - {f}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python convert-list-pages.py <input_file> [output_file]")
        print("   或: python convert-list-pages.py --batch <directory>")
        sys.exit(1)
    
    if sys.argv[1] == '--batch':
        if len(sys.argv) < 3:
            print("请指定要批量转换的目录")
            sys.exit(1)
        batch_convert(sys.argv[2])
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        convert_file(input_file, output_file)
