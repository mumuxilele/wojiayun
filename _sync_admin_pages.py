#!/usr/bin/env python3
"""同步更新其他 admin 列表页面的样式和交互"""

pages = [
    '/www/wwwroot/wojiayun/business-admin/members.html',
    '/www/wwwroot/wojiayun/business-admin/orders.html',
    '/www/wwwroot/wojiayun/business-admin/products.html',
    '/www/wwwroot/wojiayun/business-admin/coupons.html',
    '/www/wwwroot/wojiayun/business-admin/venues.html',
    '/www/wwwroot/wojiayun/business-admin/promotions.html',
    '/www/wwwroot/wojiayun/business-admin/refunds.html',
    '/www/wwwroot/wojiayun/business-admin/users.html',
]

for path in pages:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()
        if not html:
            continue

        changed = False

        # 如果有分页区域，添加页码按钮
        if 'id="pageNumbers"' not in html and '<div class="wy-pages">' in html:
            # 检查是否有现有页码渲染逻辑
            has_page_render = 'renderPageNumbers' in html or 'wy-pages_number' in html

            # 在 totalPages 附近添加页码容器
            if 'id="prevBtn"' in html and 'id="pageNumbers"' not in html:
                old_pag = '<div class="wy-pages_prev el-icon-arrow-left" id="prevBtn"'
                new_pag = '<div class="wy-pages_number" id="pageNumbers"></div>\n                <div class="wy-pages_prev el-icon-arrow-left" id="prevBtn"'
                if old_pag in html:
                    html = html.replace(old_pag, new_pag, 1)
                    changed = True

        # 如果有 loadList 且有 prevBtn/nextBtn，添加 showToast 和 renderPageNumbers
        if 'async function loadList' in html and "document.getElementById('prevBtn')" in html:
            # 添加 Toast 和 renderPageNumbers 注入点：在 loadList 函数开头
            toast_code = '''// Toast
        function showToast(msg, type) {
            type = type || 'info';
            var t = document.getElementById('globalToast');
            if (!t) { t = document.createElement('div'); t.id = 'globalToast'; t.className = 'toast'; document.body.appendChild(t); }
            t.className = 'toast ' + type; t.textContent = msg; t.classList.add('show');
            setTimeout(function() { t.classList.remove('show'); }, 3000);
        }

        // 渲染页码
        function renderPageNumbers() {
            var c = document.getElementById('pageNumbers');
            if (!c) return;
            var html = '', maxShow = 5;
            var start = Math.max(1, currentPage - Math.floor(maxShow / 2));
            var end = Math.min(totalPages, start + maxShow - 1);
            if (end - start < maxShow - 1) start = Math.max(1, end - maxShow + 1);
            if (start > 1) { html += '<div class="wy-pages_num" onclick="loadList(1)">1</div>'; if (start > 2) html += '<span style="color:#909399;padding:0 2px">...</span>'; }
            for (var i = start; i <= end; i++) html += '<div class="wy-pages_num' + (i === currentPage ? ' active' : '') + '" onclick="loadList(' + i + ')">' + i + '</div>';
            if (end < totalPages) { if (end < totalPages - 1) html += '<span style="color:#909399;padding:0 2px">...</span>'; html += '<div class="wy-pages_num" onclick="loadList(' + totalPages + ')">' + totalPages + '</div>'; }
            c.innerHTML = html;
        }

        // 跳转
        function doJump() {
            var inp = document.getElementById('jumpPage');
            var p = parseInt(inp && inp.value);
            if (p && p >= 1 && p <= totalPages) { loadList(p); inp.value = ''; }
        }
'''

            old_loadlist = 'async function loadList(page) {'
            if old_loadlist in html:
                html = html.replace(old_loadlist, toast_code + old_loadlist, 1)
                changed = True

            # 在 prevBtn/nextBtn 更新后添加 renderPageNumbers
            old_update = "document.getElementById('prevBtn').classList.toggle('disabled', currentPage <= 1);"
            new_update = "document.getElementById('prevBtn').classList.toggle('disabled', currentPage <= 1);\n                    document.getElementById('nextBtn').classList.toggle('disabled', currentPage >= totalPages);\n                    renderPageNumbers();"
            if old_update in html:
                # 找到实际的内容并替换（避免之前已替换的情况）
                if "renderPageNumbers();" not in html.split("toggle('disabled'")[0]:
                    html = html.replace(old_update, new_update, 1)
                    changed = True

        if changed:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            print('Updated: ' + path)
        else:
            print('No changes: ' + path)

    except Exception as e:
        print('Error on ' + path + ': ' + str(e))
