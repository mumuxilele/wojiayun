/**
 * V15 XSS防护公共工具
 * 统一escapeHtml函数，供所有HTML页面引入
 * 用法: <script src="xss-utils.js"></script>
 */
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/**
 * 转义HTML属性值（用于title、onclick等属性内部）
 */
function escapeAttr(text) {
    return escapeHtml(text);
}
