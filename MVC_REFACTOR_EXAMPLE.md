# MVC 架构重构示例

本文档展示如何将原有代码重构为标准的 MVC 架构。

## 目录结构

```
business-common/
├── models/              # Model 实体层
│   ├── __init__.py
│   ├── base_model.py
│   ├── user.py
│   ├── application.py
│   ├── order.py
│   └── product.py
├── repositories/        # Repository 仓储层
│   ├── __init__.py
│   ├── base_repository.py
│   ├── user_repository.py
│   ├── application_repository.py
│   ├── order_repository.py
│   └── product_repository.py
└── services/            # Service 服务层
    ├── __init__.py
    ├── base_service.py
    ├── user_service.py
    ├── application_service.py
    ├── order_service.py
    └── product_service.py
```

---

## 重构示例

### 示例 1: 查询用户申请列表

#### ❌ 原有做法 (Controller 直接操作数据库)

```python
# business-userH5/app.py
@app.route('/api/user/applications', methods=['GET'])
@require_login
def get_user_applications(user):
    page      = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status    = request.args.get('status')
    app_type  = request.args.get('app_type')
    
    where  = "user_id=%s AND deleted=0"
    params = [user['user_id']]
    if status:
        where += " AND status=%s"; params.append(status)
    if app_type:
        where += " AND app_type=%s"; params.append(app_type)
    
    # ❌ 直接写 SQL
    total  = db.get_total("SELECT COUNT(*) FROM business_applications WHERE " + where, params)
    offset = (page - 1) * page_size
    items  = db.get_all(
        "SELECT id,app_no,app_type,title,status,priority,created_at FROM business_applications WHERE "
        + where + " ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params + [page_size, offset]
    )
    return jsonify({'success': True, 'data': {
        'items': items, 'total': total, 'page': page, 'page_size': page_size,
    }})
```

#### ✅ 重构后 (使用 MVC 架构)

```python
# business-userH5/controllers/application_controller.py
from business_common.services import ApplicationService

# 初始化服务
app_service = ApplicationService()

@app.route('/api/user/applications', methods=['GET'])
@require_login
def get_user_applications(user):
    # 1. 获取参数
    page = int(request.args.get('page', 1))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    status = request.args.get('status')
    type_code = request.args.get('type_code')
    
    # 2. 调用 Service 层
    result = app_service.get_user_applications(
        user_id=user['user_id'],
        status=status,
        type_code=type_code,
        page=page,
        page_size=page_size
    )
    
    # 3. 返回响应
    return jsonify(result)


# business-common/services/application_service.py
class ApplicationService(BaseService):
    def __init__(self):
        self.app_repo = ApplicationRepository()
    
    def get_user_applications(self, user_id, status=None, type_code=None, page=1, page_size=20):
        # 业务逻辑处理
        try:
            # 调用 Repository 层
            result = self.app_repo.find_by_user(
                user_id=user_id,
                status=status,
                type_code=type_code,
                page=page,
                page_size=page_size
            )
            return self.success(result)
        except Exception as e:
            self.logger.error(f"查询失败: {e}")
            return self.error('查询失败')


# business-common/repositories/application_repository.py
class ApplicationRepository(BaseRepository):
    TABLE_NAME = 'business_applications'
    
    def find_by_user(self, user_id, status=None, type_code=None, page=1, page_size=20):
        # 数据访问逻辑
        offset = (page - 1) * page_size
        conditions = ["user_id = %s", "deleted = 0"]
        params = [user_id]
        
        if status:
            conditions.append("status = %s")
            params.append(status)
        
        where_clause = " AND ".join(conditions)
        
        # SQL 只存在于 Repository 中
        count_sql = f"SELECT COUNT(*) as cnt FROM {self.TABLE_NAME} WHERE {where_clause}"
        count_result = self.db.get_one(count_sql, params.copy())
        total = count_result.get('cnt', 0)
        
        data_sql = f"""
            SELECT id, application_no, type_code, title, status, created_at
            FROM {self.TABLE_NAME}
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        items = self.db.get_all(data_sql, params + [page_size, offset])
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size
        }
```

---

### 示例 2: 创建申请

#### ❌ 原有做法

```python
# business-userH5/app.py
@app.route('/api/user/applications/v2', methods=['POST'])
@require_login
def create_application_v2(user):
    from business_common.application_service import ApplicationService
    
    data = request.get_json() or {}
    type_code = data.get('type_code')
    title = data.get('title', '').strip()
    form_data = data.get('form_data', {})
    
    if not type_code:
        return jsonify({'success': False, 'msg': '请选择申请类型'})
    if not title:
        return jsonify({'success': False, 'msg': '请输入申请标题'})
    
    # ❌ 直接调用旧 Service，没有分层
    result = ApplicationService.create_application(
        user_id=user.get('user_id'),
        user_name=user.get('user_name', ''),
        user_phone=user.get('phone', ''),
        type_code=type_code,
        title=title,
        form_data=form_data,
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id'),
    )
    return jsonify(result)
```

#### ✅ 重构后

```python
# business-userH5/controllers/application_controller.py
@app.route('/api/user/applications/v2', methods=['POST'])
@require_login
def create_application_v2(user):
    # 1. 获取参数
    data = request.get_json() or {}
    
    # 2. 调用 Service (参数校验在 Service 中处理)
    result = app_service.create_application(
        user_id=user.get('user_id'),
        user_name=user.get('user_name', ''),
        type_code=data.get('type_code'),
        title=data.get('title', '').strip(),
        form_data=data.get('form_data', {}),
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id'),
        attachments=data.get('attachments', []),
        remark=data.get('remark', '').strip()
    )
    
    # 3. 返回响应
    return jsonify(result)


# business-common/services/application_service.py
class ApplicationService(BaseService):
    def create_application(self, user_id, user_name, type_code, title, 
                          form_data=None, ec_id=None, project_id=None,
                          attachments=None, remark=None):
        # 1. 参数校验 (业务逻辑)
        if not type_code:
            return self.error('请选择申请类型')
        if not title or not title.strip():
            return self.error('请输入申请标题')
        if len(title) > 100:
            return self.error('标题不能超过100个字符')
        
        try:
            # 2. 生成业务数据
            fid = generate_business_fid('app')
            today = datetime.now().strftime('%Y%m%d')
            count = self.app_repo.count_by_user_and_status(user_id)
            application_no = f"APP{today}{count + 1:05d}"
            
            # 3. 构建数据
            data = {
                'fid': fid,
                'application_no': application_no,
                'type_code': type_code,
                'title': title.strip(),
                'user_id': user_id,
                'user_name': user_name,
                'ec_id': ec_id,
                'project_id': project_id,
                'status': Application.STATUS_PENDING,
            }
            
            if form_data:
                data['form_data'] = json.dumps(form_data, ensure_ascii=False)
            if attachments:
                data['attachments'] = json.dumps(attachments, ensure_ascii=False)
            if remark:
                data['remark'] = remark
            
            # 4. 调用 Repository 保存数据
            app_id = self.app_repo.insert(data)
            
            if not app_id:
                return self.error('创建申请失败')
            
            # 5. 返回结果
            return self.success({
                'id': app_id,
                'fid': fid,
                'application_no': application_no,
                'status': Application.STATUS_PENDING
            }, '申请提交成功')
            
        except Exception as e:
            self.logger.error(f"创建申请失败: {e}")
            return self.error(f'提交失败: {str(e)}')
```

---

## 使用新的 Service 层

### 用户端 (business-userH5)

```python
# business-userH5/app.py
from business_common.services import (
    ApplicationService,
    OrderService,
    ProductService,
    UserService
)

# 初始化服务
app_service = ApplicationService()
order_service = OrderService()
product_service = ProductService()
user_service = UserService()

# 路由只处理 HTTP 相关逻辑
@app.route('/api/user/applications/v2', methods=['GET'])
@require_login
def get_applications(user):
    result = app_service.get_user_applications(
        user_id=user['user_id'],
        status=request.args.get('status'),
        page=int(request.args.get('page', 1))
    )
    return jsonify(result)

@app.route('/api/user/applications/v2', methods=['POST'])
@require_login
def create_application(user):
    data = request.get_json() or {}
    result = app_service.create_application(
        user_id=user['user_id'],
        user_name=user.get('user_name', ''),
        type_code=data.get('type_code'),
        title=data.get('title'),
        form_data=data.get('form_data'),
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id')
    )
    return jsonify(result)

@app.route('/api/user/applications/v2/<int:app_id>', methods=['GET'])
@require_login
def get_application_detail(user, app_id):
    result = app_service.get_application_detail(
        app_id=app_id,
        user_id=user['user_id']
    )
    return jsonify(result)
```

### 管理后台 (business-admin)

```python
# business-admin/app.py
from business_common.services import ApplicationService

admin_app_service = ApplicationService()

@app.route('/api/admin/applications', methods=['GET'])
@require_admin
def admin_list_applications(user):
    result = admin_app_service.get_all_applications(
        ec_id=user.get('ec_id'),
        status=request.args.get('status'),
        keyword=request.args.get('keyword'),
        page=int(request.args.get('page', 1))
    )
    return jsonify(result)

@app.route('/api/admin/applications/<int:app_id>/status', methods=['PUT'])
@require_admin
def admin_update_application_status(user, app_id):
    data = request.get_json() or {}
    result = admin_app_service.update_status(
        app_id=app_id,
        status=data.get('status'),
        approver_id=user.get('user_id'),
        approver_name=user.get('user_name'),
        remark=data.get('remark')
    )
    return jsonify(result)
```

---

## 关键改进

| 方面 | 原有做法 | 重构后 |
|-----|---------|--------|
| **SQL 位置** | 分散在 Controller 中 | 集中在 Repository |
| **业务逻辑** | 混杂在路由中 | 封装在 Service |
| **数据实体** | 字典/无类型 | Model 类定义 |
| **复用性** | 难以复用 | Service 可复用 |
| **测试性** | 无法单元测试 | 可 Mock 测试 |
| **维护性** | 修改需多处 | 修改集中 |

---

## 迁移计划

### 阶段 1: 新建代码使用新架构
- 新功能必须使用新的 MVC 架构
- 旧代码逐步迁移

### 阶段 2: 高频接口优先重构
1. `/api/user/applications/*`
2. `/api/user/orders/*`
3. `/api/user/products/*`
4. `/api/admin/applications/*`

### 阶段 3: 完全替换旧代码
- 所有接口使用新架构
- 删除旧的 SQL 硬编码代码

---

**文档版本**: V50.0  
**更新日期**: 2026-04-20
