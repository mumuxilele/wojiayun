#!/usr/bin/env python3
"""批量更新 admin HTML 页面样式和交互"""

import os

# 1. 更新 list-style.css
css_path = '/www/wwwroot/wojiayun/business-common/list-style.css'
with open(css_path, 'r', encoding='utf-8') as f:
    css = f.read()

# 修改表格行高和间距
old_td = '.el-table__row td {\n    padding: 12px 10px;\n    border-bottom: 1px solid var(--el-border-color-light);\n    border-right: 1px solid var(--el-border-color-light);\n}'
new_td = '.el-table__row td {\n    padding: 16px 12px;\n    border-bottom: 1px solid var(--el-border-color);\n    border-right: 1px solid var(--el-border-color-light);\n}'
css = css.replace(old_td, new_td)

old_th = '.el-table__header th {\n    padding: 12px 10px;'
new_th = '.el-table__header th {\n    padding: 14px 12px;'
css = css.replace(old_th, new_th)

# 分页样式
old_pages = '''.wy-pages {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-left: auto;
}

.wy-pages_total {
    font-size: var(--el-font-size-small);
    color: var(--el-text-secondary);
}

.wy-pages_total em {
    color: var(--el-color-primary);
    font-style: normal;
    font-weight: 600;
    margin: 0 2px;
}

.wy-pages_prev,
.wy-pages_next {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--el-border-color);
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    color: var(--el-text-regular);
    transition: all 0.2s;
}

.wy-pages_prev:hover,
.wy-pages_next:hover {
    color: var(--el-color-primary);
    border-color: var(--el-color-primary);
}

.wy-pages_prev.disabled,
.wy-pages_next.disabled {
    opacity: 0.5;
    cursor: not-allowed;
}'''

new_pages = '''.wy-pages {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-left: auto;
}

.wy-pages_total {
    font-size: var(--el-font-size-small);
    color: var(--el-text-secondary);
    margin-right: 8px;
}

.wy-pages_total em {
    color: var(--el-color-primary);
    font-style: normal;
    font-weight: 600;
    margin: 0 2px;
}

.wy-pages_number {
    display: flex;
    align-items: center;
    gap: 4px;
}

.wy-pages_num {
    min-width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--el-border-color);
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    color: var(--el-text-regular);
    transition: all 0.2s;
    background: #fff;
}

.wy-pages_num:hover {
    color: var(--el-color-primary);
    border-color: var(--el-color-primary);
}

.wy-pages_num.active {
    background: var(--el-color-primary);
    border-color: var(--el-color-primary);
    color: #fff;
}

.wy-pages_num.disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.wy-pages_prev,
.wy-pages_next {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--el-border-color);
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    color: var(--el-text-regular);
    transition: all 0.2s;
    background: #fff;
}

.wy-pages_prev:hover,
.wy-pages_next:hover {
    color: var(--el-color-primary);
    border-color: var(--el-color-primary);
}

.wy-pages_prev.disabled,
.wy-pages_next.disabled {
    opacity: 0.4;
    cursor: not-allowed;
}'''

css = css.replace(old_pages, new_pages)

# Toast 样式
toast_style = '''
/* Toast 提示 */
.toast {
    position: fixed;
    top: 80px;
    left: 50%;
    transform: translateX(-50%) translateY(-20px);
    background: rgba(48, 49, 51, 0.9);
    color: #fff;
    padding: 12px 24px;
    border-radius: 6px;
    font-size: 14px;
    z-index: 9999;
    opacity: 0;
    transition: all 0.3s ease;
    pointer-events: none;
    white-space: nowrap;
    max-width: 80vw;
    overflow: hidden;
    text-overflow: ellipsis;
}

.toast.show {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
}

.toast.success {
    background: rgba(103, 194, 58, 0.95);
}

.toast.error {
    background: rgba(245, 108, 108, 0.95);
}

.toast.info {
    background: rgba(64, 158, 255, 0.95);
}

/* 按钮加载状态 */
.el-button.loading {
    pointer-events: none;
    opacity: 0.7;
}

.el-button.loading::after {
    content: '';
    display: inline-block;
    width: 12px;
    height: 12px;
    margin-left: 6px;
    border: 2px solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    animation: btn-spin 0.6s linear infinite;
    vertical-align: middle;
}

@keyframes btn-spin {
    to { transform: rotate(360deg); }
}

.el-button.confirm-btn {
    min-width: 80px;
}'''

css += toast_style

with open(css_path, 'w', encoding='utf-8') as f:
    f.write(css)
print('CSS updated')


# 2. 更新 applications.html
app_html = '/www/wwwroot/wojiayun/business-admin/applications.html'
with open(app_html, 'r', encoding='utf-8') as f:
    html = f.read()

# 2a. 修复列错位：表头加checkbox列
old_th = '<th><div class="cell">申请单号</div></th>'
new_th = '<th style="width:40px"><div class="cell"><input type="checkbox" id="checkAll" onchange="toggleAll(this)"></div></th>\n                    <th><div class="cell">申请单号</div></th>'
html = html.replace(old_th, new_th)

# 2b. 分页区域
old_pagination = '''<div class="wy-pages">
                <div class="wy-pages_total">第<em id="currentPage">1</em>/<em id="totalPages">1</em>页</div>
                <div class="wy-pages_prev el-icon-arrow-left" id="prevBtn" onclick="changePage(-1)"></div>
                <div class="wy-pages_next el-icon-arrow-right" id="nextBtn" onclick="changePage(1)"></div>
            </div>'''

new_pagination = '''<div class="wy-pages">
                <div class="wy-pages_total">第<em id="currentPage">1</em>/<em id="totalPages">1</em>页</div>
                <div class="wy-pages_number" id="pageNumbers"></div>
                <div class="wy-pages_jump">
                    <span>跳至</span>
                    <input type="number" class="wy-pages_jump-input" id="jumpPage" min="1" onkeydown="if(event.key===\'Enter\')doJump()">
                    <span>页</span>
                </div>
                <div class="wy-pages_prev el-icon-arrow-left" id="prevBtn" onclick="changePage(-1)"></div>
                <div class="wy-pages_next el-icon-arrow-right" id="nextBtn" onclick="changePage(1)"></div>
            </div>'''
html = html.replace(old_pagination, new_pagination)

# 2c. 添加 Toast 函数和分页渲染
old_loadlist = 'async function loadList(page) {'
new_loadlist = '''// ========== Toast ==========
        function showToast(msg, type) {
            type = type || 'info';
            var toast = document.getElementById('globalToast');
            if (!toast) {
                toast = document.createElement('div');
                toast.id = 'globalToast';
                toast.className = 'toast';
                document.body.appendChild(toast);
            }
            toast.className = 'toast ' + type;
            toast.textContent = msg;
            toast.classList.add('show');
            setTimeout(function() { toast.classList.remove('show'); }, 3000);
        }

        // ========== 渲染页码 ==========
        function renderPageNumbers() {
            var container = document.getElementById('pageNumbers');
            if (!container) return;
            var html = '';
            var maxShow = 5;
            var start = Math.max(1, currentPage - Math.floor(maxShow / 2));
            var end = Math.min(totalPages, start + maxShow - 1);
            if (end - start < maxShow - 1) start = Math.max(1, end - maxShow + 1);
            if (start > 1) {
                html += '<div class="wy-pages_num" onclick="loadList(1)">1</div>';
                if (start > 2) html += '<span style="color:#909399;padding:0 2px">...</span>';
            }
            for (var i = start; i <= end; i++) {
                html += '<div class="wy-pages_num' + (i === currentPage ? ' active' : '') + '" onclick="loadList(' + i + ')">' + i + '</div>';
            }
            if (end < totalPages) {
                if (end < totalPages - 1) html += '<span style="color:#909399;padding:0 2px">...</span>';
                html += '<div class="wy-pages_num" onclick="loadList(' + totalPages + ')">' + totalPages + '</div>';
            }
            container.innerHTML = html;
        }

        function doJump() {
            var input = document.getElementById('jumpPage');
            var page = parseInt(input && input.value);
            if (page && page >= 1 && page <= totalPages) {
                loadList(page);
                input.value = '';
            }
        }

        function toggleAll(el) {
            document.querySelectorAll('.row-check').forEach(function(cb) { cb.checked = el.checked; });
            updateBatchBar();
        }

        async function loadList(page) {'''

html = html.replace(old_loadlist, new_loadlist)

# 2d. 更新分页状态时渲染页码
old_update_pages = "document.getElementById('prevBtn').classList.toggle('disabled', currentPage <= 1);\n                    document.getElementById('nextBtn').classList.toggle('disabled', currentPage >= totalPages);"
new_update_pages = "document.getElementById('currentPage').textContent = currentPage;\n                    document.getElementById('totalPages').textContent = totalPages;\n                    document.getElementById('prevBtn').classList.toggle('disabled', currentPage <= 1);\n                    document.getElementById('nextBtn').classList.toggle('disabled', currentPage >= totalPages);\n                    renderPageNumbers();"
html = html.replace(old_update_pages, new_update_pages)

# 2e. 确认按钮添加 loading
old_confirm = '<button class="el-button el-button--primary el-button--small" onclick="submitEdit()">确认提交</button>'
new_confirm = '<button class="el-button el-button--primary el-button--small confirm-btn" id="confirmSubmitBtn" onclick="submitEdit()">确认提交</button>'
html = html.replace(old_confirm, new_confirm)

# 2f. 修改 submitEdit 添加防抖和 loading
old_submitedit = 'async function submitEdit() {\n            const id = document.getElementById(\'editAppId\').value;\n            const status = document.getElementById(\'editStatus\').value;\n            const result = document.getElementById(\'editResult\').value;'
new_submitedit = '''async function submitEdit() {
            var btn = document.getElementById('confirmSubmitBtn');
            if (btn && btn.classList.contains('loading')) return;
            btn.classList.add('loading');
            btn.textContent = '提交中...';
            var id = document.getElementById('editAppId').value;
            var status = document.getElementById('editStatus').value;
            var result = document.getElementById('editResult').value;'''
html = html.replace(old_submitedit, new_submitedit)

# 2g. submitEdit 成功/失败处理
old_success = '} catch (e) {\n                console.error(e);\n            }\n        }'
new_success = '''} catch (e) {
                console.error(e);
                showToast('提交失败: ' + e.message, 'error');
            } finally {
                if (btn) {
                    btn.classList.remove('loading');
                    btn.textContent = '确认提交';
                }
            }
        }'''
html = html.replace(old_success, new_success)

# 2h. closeEdit 恢复按钮
old_close = '''function closeEdit() {
            document.getElementById('editOverlay').style.display = 'none';
            document.getElementById('editModal').classList.remove('show');
        }'''
new_close = '''function closeEdit() {
            document.getElementById('editOverlay').style.display = 'none';
            document.getElementById('editModal').classList.remove('show');
            var btn = document.getElementById('confirmSubmitBtn');
            if (btn) {
                btn.classList.remove('loading');
                btn.textContent = '确认提交';
            }
        }'''
html = html.replace(old_close, new_close)

# 2i. deleteApp 添加 toast
old_del = "if (data.success) {\n                        loadList(currentPage);"
new_del = "if (data.success) {\n                        loadList(currentPage);\n                        showToast('删除成功', 'success');"
html = html.replace(old_del, new_del)

with open(app_html, 'w', encoding='utf-8') as f:
    f.write(html)
print('applications.html updated')
