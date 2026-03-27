/**
 * SQL 加载器 - MyBatis 风格
 * 将 SQL 语句分离到配置文件中，支持命名参数
 */
const fs = require('fs');
const path = require('path');

class SqlLoader {
    constructor(sqlDir = 'sql') {
        this.sqlDir = sqlDir;
        this.queries = {};
        this.loadAll();
    }

    /**
     * 加载所有 SQL 配置文件
     */
    loadAll() {
        const sqlPath = path.join(__dirname, this.sqlDir);
        
        if (!fs.existsSync(sqlPath)) {
            console.log('SQL directory not found, using inline SQL');
            return;
        }

        const files = fs.readdirSync(sqlPath).filter(f => f.endsWith('.json'));
        
        for (const file of files) {
            try {
                const content = fs.readFileSync(path.join(sqlPath, file), 'utf8');
                const config = JSON.parse(content);
                
                if (config.queries) {
                    for (const [key, value] of Object.entries(config.queries)) {
                        const fullKey = config.namespace ? `${config.namespace}.${key}` : key;
                        this.queries[fullKey] = value;
                    }
                }
                console.log(`Loaded SQL from ${file}`);
            } catch (e) {
                console.error(`Error loading ${file}:`, e.message);
            }
        }
    }

    /**
     * 获取 SQL 模板
     */
    getSql(key) {
        const query = this.queries[key];
        if (!query) {
            throw new Error(`SQL query not found: ${key}`);
        }
        return typeof query === 'string' ? query : query.sql;
    }

    /**
     * 获取 SQL 配置信息
     */
    getConfig(key) {
        return this.queries[key];
    }

    /**
     * 解析 SQL，替换命名参数
     * 支持 #{paramName} 格式
     */
    parseSql(sql, params = {}) {
        let result = sql;
        const values = [];
        
        // 替换命名参数
        const paramRegex = /#\{(\w+)\}/g;
        let match;
        
        while ((match = paramRegex.exec(sql)) !== null) {
            const paramName = match[1];
            values.push(params[paramName]);
        }
        
        // 构建最终 SQL
        result = sql.replace(paramRegex, '?');
        
        return { sql: result, params: values };
    }

    /**
     * 构建 WHERE 子句
     */
    buildWhereClause(conditions = {}) {
        const clauses = [];
        const params = [];
        
        for (const [key, value] of Object.entries(conditions)) {
            if (value !== undefined && value !== null) {
                clauses.push(`${key} = ?`);
                params.push(value);
            }
        }
        
        return {
            clause: clauses.length > 0 ? 'AND ' + clauses.join(' AND ') : '',
            params
        };
    }
}

// 导出单例
module.exports = new SqlLoader();
