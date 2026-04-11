# ============ V29.0 申请审批系统 (用户端) ============

@app.route('/api/user/application/types', methods=['GET'])
@require_login
def get_application_types_list(user):
    """V29.0: 获取申请类型列表"""
    from business_common.application_service import ApplicationService
    category = request.args.get('category')
    types = ApplicationService.get_application_types(category=category)
    return jsonify({'success': True, 'data': {'items': types}})


@app.route('/api/user/application/types/<type_code>', methods=['GET'])
@require_login
def get_application_type_detail(user, type_code):
    """V29.0: 获取申请类型详情"""
    from business_common.application_service import ApplicationService
    app_type = ApplicationService.get_application_type(type_code)
    if not app_type:
        return jsonify({'success': False, 'msg': '申请类型不存在'})
    return jsonify({'success': True, 'data': app_type})


@app.route('/api/user/applications/v2', methods=['POST'])
@require_login
def create_application_v2(user):
    """V29.0: 创建申请（支持8种业务类型）"""
    from business_common.application_service import ApplicationService
    
    data = request.get_json() or {}
    type_code = data.get('type_code')
    title = data.get('title', '').strip()
    form_data = data.get('form_data', {})
    remark = data.get('remark', '').strip()
    attachments = data.get('attachments', [])
    
    if not type_code:
        return jsonify({'success': False, 'msg': '请选择申请类型'})
    if not title:
        return jsonify({'success': False, 'msg': '请输入申请标题'})
    
    result = ApplicationService.create_application(
        user_id=user.get('user_id'),
        user_name=user.get('user_name', ''),
        user_phone=user.get('phone', ''),
        type_code=type_code,
        title=title,
        form_data=form_data,
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id'),
        attachments=attachments,
        remark=remark
    )
    return jsonify(result)


@app.route('/api/user/applications/v2', methods=['GET'])
@require_login
def get_user_applications_v2(user):
    """V29.0: 获取用户申请列表（支持筛选）"""
    from business_common.application_service import ApplicationService
    
    type_code = request.args.get('type_code')
    status = request.args.get('status')
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    result = ApplicationService.get_user_applications(
        user_id=user.get('user_id'),
        type_code=type_code,
        status=status,
        page=page,
        page_size=page_size
    )
    return jsonify({'success': True, 'data': result})


@app.route('/api/user/applications/v2/<int:app_id>', methods=['GET'])
@require_login
def get_application_detail_v2(user, app_id):
    """V29.0: 获取申请详情"""
    from business_common.application_service import ApplicationService
    
    app = ApplicationService.get_application_detail(
        app_id=app_id,
        user_id=user.get('user_id'),
        is_staff=False
    )
    
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    
    return jsonify({'success': True, 'data': app})


@app.route('/api/user/applications/v2/<int:app_id>/cancel', methods=['POST'])
@require_login
def cancel_application_v2(user, app_id):
    """V29.0: 取消申请"""
    from business_common.application_service import ApplicationService
    
    result = ApplicationService.cancel_application(
        app_id=app_id,
        user_id=user.get('user_id')
    )
    return jsonify(result)


@app.route('/api/user/applications/v2/favorites', methods=['GET'])
@require_login
def get_favorite_applications(user):
    """V29.0: 获取常用申请列表"""
    items = db.get_all(
        """SELECT id, app_no, app_type, title, form_data, created_at
           FROM business_applications
           WHERE user_id=%s AND is_favorite=1 AND deleted=0
           ORDER BY updated_at DESC
           LIMIT 20""",
        [user.get('user_id')]
    ) or []
    return jsonify({'success': True, 'data': {'items': items}})
