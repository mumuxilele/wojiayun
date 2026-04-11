# ============ V29.0 申请审批系统 (员工端) ============

@app.route('/api/staff/applications/v2/pending', methods=['GET'])
@require_staff
def get_pending_applications_v2(user):
    """V29.0: 获取待审批申请列表"""
    from business_common.application_service import ApplicationService
    
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    result = ApplicationService.get_pending_applications(
        approver_id=user.get('user_id'),
        ec_id=user.get('ec_id'),
        project_id=user.get('project_id'),
        page=page,
        page_size=page_size
    )
    return jsonify({'success': True, 'data': result})


@app.route('/api/staff/applications/v2/all', methods=['GET'])
@require_staff
def get_all_applications_v2(user):
    """V29.0: 获取所有申请列表"""
    from business_common.application_service import ApplicationService
    
    type_code = request.args.get('type_code')
    status = request.args.get('status')
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(int(request.args.get('page_size', 20)), 50)
    
    where = "deleted=0"
    params = []
    
    if user.get('ec_id'):
        where += " AND ec_id=%s"
        params.append(user.get('ec_id'))
    if user.get('project_id'):
        where += " AND project_id=%s"
        params.append(user.get('project_id'))
    if type_code:
        where += " AND app_type=%s"
        params.append(type_code)
    if status:
        where += " AND status=%s"
        params.append(status)
    
    total = db.get_total(f"SELECT COUNT(*) FROM business_applications WHERE {where}", params)
    offset = (page - 1) * page_size
    
    items = db.get_all(
        f"""SELECT id, app_no, app_type, title, user_name, status, created_at
           FROM business_applications
           WHERE {where}
           ORDER BY created_at DESC
           LIMIT %s OFFSET %s""",
        params + [page_size, offset]
    ) or []
    
    return jsonify({'success': True, 'data': {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size
    }})


@app.route('/api/staff/applications/v2/<int:app_id>', methods=['GET'])
@require_staff
def get_application_detail_staff_v2(user, app_id):
    """V29.0: 员工获取申请详情"""
    from business_common.application_service import ApplicationService
    
    app = ApplicationService.get_application_detail(
        app_id=app_id,
        is_staff=True
    )
    
    if not app:
        return jsonify({'success': False, 'msg': '申请不存在'})
    
    return jsonify({'success': True, 'data': app})


@app.route('/api/staff/applications/v2/<int:app_id>/approve', methods=['POST'])
@require_staff
def approve_application_v2(user, app_id):
    """V29.0: 审批申请"""
    from business_common.application_service import ApplicationService
    
    data = request.get_json() or {}
    action = data.get('action')
    remark = data.get('remark', '').strip()
    
    if action not in ['approve', 'reject']:
        return jsonify({'success': False, 'msg': '无效的操作类型'})
    
    result = ApplicationService.approve_application(
        app_id=app_id,
        approver_id=user.get('user_id'),
        approver_name=user.get('user_name', ''),
        action=action,
        remark=remark
    )
    return jsonify(result)


@app.route('/api/staff/applications/v2/stats', methods=['GET'])
@require_staff
def get_application_stats_v2(user):
    """V29.0: 获取申请统计"""
    ec_id = user.get('ec_id')
    project_id = user.get('project_id')
    
    where = "deleted=0"
    params = []
    if ec_id:
        where += " AND ec_id=%s"
        params.append(ec_id)
    if project_id:
        where += " AND project_id=%s"
        params.append(project_id)
    
    pending_count = db.get_total(
        f"SELECT COUNT(*) FROM business_applications WHERE {where} AND status='pending'",
        params.copy()
    )
    
    today_count = db.get_total(
        f"SELECT COUNT(*) FROM business_applications WHERE {where} AND DATE(created_at)=CURDATE()",
        params.copy()
    )
    
    total_count = db.get_total(
        f"SELECT COUNT(*) FROM business_applications WHERE {where}",
        params.copy()
    )
    
    return jsonify({'success': True, 'data': {
        'pending_count': pending_count,
        'today_count': today_count,
        'total_count': total_count
    }})


@app.route('/api/staff/applications/v2/types', methods=['GET'])
@require_staff
def get_application_types_staff_v2(user):
    """V29.0: 员工获取申请类型列表"""
    from business_common.application_service import ApplicationService
    
    types = ApplicationService.get_application_types()
    return jsonify({'success': True, 'data': {'items': types}})
