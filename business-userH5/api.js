/**
 * 粤海物业管理系统 - 前端API工具库
 * 统一封装后端接口调用，管理认证状态和错误处理
 */

const API = (() => {
  // ── 配置 ──
  const BASE_URL = 'http://47.98.238.209:22307';
  const TOKEN_KEY = 'yuehai_token';
  const USER_KEY = 'yuehai_user';

  // ── 通用请求封装 ──
  async function request(path, options = {}) {
    const url = `${BASE_URL}${path}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    // 附加 token（如果有）
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const resp = await fetch(url, {
        ...options,
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.message || `请求失败: ${resp.status}`);
      }

      return data; // { code, message, data }
    } catch (err) {
      console.error(`[API] ${path} 请求失败:`, err);
      throw err;
    }
  }

  // ── HTTP 方法快捷方式 ──
  function get(path, params = {}) {
    const qs = new URLSearchParams(params).toString();
    return request(qs ? `${path}?${qs}` : path, { method: 'GET' });
  }

  function post(path, body = {}) {
    return request(path, { method: 'POST', body });
  }

  function put(path, body = {}) {
    return request(path, { method: 'PUT', body });
  }

  function del(path) {
    return request(path, { method: 'DELETE' });
  }

  // ── 认证管理 ──
  function saveUser(userInfo) {
    localStorage.setItem(USER_KEY, JSON.stringify(userInfo));
    // 后端当前无JWT，用用户信息模拟token
    localStorage.setItem(TOKEN_KEY, userInfo.fid || 'logged-in');
  }

  function getUser() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY));
    } catch {
      return null;
    }
  }

  function isLoggedIn() {
    return !!localStorage.getItem(TOKEN_KEY);
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  // ── 管理员认证 API ──
  const admin = {
    login(username, password) {
      return post('/api/admin/login', { username, password });
    },
    register(data) {
      return post('/api/admin/register', data);
    },
    changePassword(fid, oldPassword, newPassword) {
      return post('/api/admin/change-password', { fid, old_password: oldPassword, new_password: newPassword });
    },
    dashboard() {
      return get('/api/admin/dashboard');
    }
  };

  // ── 园区管理 API ──
  const enterprises = {
    list(keyword = '', page = 1, pageSize = 20) {
      return get('/api/enterprises', { keyword, page, page_size: pageSize });
    },
    get(fid) {
      return get(`/api/enterprises/${fid}`);
    },
    create(data) {
      return post('/api/enterprises', data);
    },
    update(fid, data) {
      return put(`/api/enterprises/${fid}`, data);
    },
    delete(fid) {
      return del(`/api/enterprises/${fid}`);
    }
  };

  // ── 楼栋管理 API ──
  const buildings = {
    list(enterpriseId = '', keyword = '', page = 1, pageSize = 20) {
      return get('/api/buildings', { enterprise_id: enterpriseId, keyword, page, page_size: pageSize });
    },
    get(fid) {
      return get(`/api/buildings/${fid}`);
    },
    create(data) {
      return post('/api/buildings', data);
    },
    update(fid, data) {
      return put(`/api/buildings/${fid}`, data);
    },
    delete(fid) {
      return del(`/api/buildings/${fid}`);
    }
  };

  // ── 住户管理 API ──
  const residents = {
    list(enterpriseId = '', buildingId = '', keyword = '', page = 1, pageSize = 20) {
      return get('/api/residents', {
        enterprise_id: enterpriseId, building_id: buildingId,
        keyword, page, page_size: pageSize
      });
    },
    get(fid) {
      return get(`/api/residents/${fid}`);
    },
    create(data) {
      return post('/api/residents', data);
    }
  };

  // ── 员工管理 API ──
  const staff = {
    list(department = '', keyword = '', page = 1, pageSize = 20) {
      return get('/api/staff', { department, keyword, page, page_size: pageSize });
    },
    get(fid) {
      return get(`/api/staff/${fid}`);
    },
    create(data) {
      return post('/api/staff', data);
    }
  };

  // ── 工单管理 API ──
  const workOrders = {
    list(status = '', level = '', keyword = '', enterpriseId = '', page = 1, pageSize = 20) {
      return get('/api/work-orders', {
        status, level, keyword,
        enterprise_id: enterpriseId, page, page_size: pageSize
      });
    },
    get(fid) {
      return get(`/api/work-orders/${fid}`);
    },
    create(data) {
      return post('/api/work-orders', data);
    },
    assign(fid, assigneeId, assigneeName) {
      return post(`/api/work-orders/${fid}/assign`, { assignee_id: assigneeId, assignee_name: assigneeName });
    },
    complete(fid, rating = 5) {
      return post(`/api/work-orders/${fid}/complete`, { rating });
    }
  };

  // ── 费用管理 API ──
  const bills = {
    list(type = '', status = '', keyword = '', enterpriseId = '', page = 1, pageSize = 20) {
      return get('/api/bills', {
        type, status, keyword,
        enterprise_id: enterpriseId, page, page_size: pageSize
      });
    },
    create(data) {
      return post('/api/bills', data);
    },
    pay(billId, data) {
      return post(`/api/bills/${billId}/pay`, data);
    }
  };

  // ── 统一返回 ──
  return {
    BASE_URL,
    request, get, post, put, del,
    admin, enterprises, buildings, residents, staff, workOrders, bills,
    auth: { saveUser, getUser, isLoggedIn, logout }
  };
})();

// 挂载到全局
window.API = API;
