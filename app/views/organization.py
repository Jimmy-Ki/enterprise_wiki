"""
组织架构管理视图
"""

from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.user import User, Role
from app.models.organization import Department, Project, Workspace, UserDepartment, UserProject, UserWorkspace
from app.decorators import admin_required
from app import db
from datetime import datetime
import json
import re

organization = Blueprint('organization', __name__)


@organization.route('/admin/organization')
@login_required
@admin_required
def admin_organization():
    """管理员组织架构总览页面"""
    # 获取统计数据
    stats = {
        'total_departments': Department.query.count(),
        'active_departments': Department.query.filter_by(is_active=True).count(),
        'total_projects': Project.query.count(),
        'total_workspaces': Workspace.query.count(),
        'total_members': UserDepartment.query.filter_by(is_active=True).count(),
        'max_depth': 0  # 计算最大层级深度
    }

    # 计算组织架构最大深度
    root_departments = Department.query.filter_by(parent_id=None).all()
    for root_dept in root_departments:
        def get_depth(dept, current_depth=1):
            if not len(dept.children):
                return current_depth
            max_child_depth = current_depth
            for child in dept.children:
                child_depth = get_depth(child, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)
            return max_child_depth

        depth = get_depth(root_dept)
        stats['max_depth'] = max(stats['max_depth'], depth)

    # 获取最新数据
    recent_departments = Department.query.order_by(Department.created_at.desc()).limit(5).all()
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(5).all()
    recent_workspaces = Workspace.query.order_by(Workspace.created_at.desc()).limit(6).all()

    return render_template('admin/organization_standalone.html',
                         page_title='组织架构总览',
                         page_icon='fas fa-sitemap',
                         stats=stats,
                         recent_departments=recent_departments,
                         recent_projects=recent_projects,
                         recent_workspaces=recent_workspaces)


@organization.route('/admin/departments')
@login_required
@admin_required
def admin_departments():
    """管理员部门管理页面"""
    # 获取所有部门
    departments = Department.query.order_by(Department.sort_order, Department.name).all()
    users = User.query.filter_by(is_active=True).order_by(User.name).all()

    # 计算统计数据
    stats = {
        'total_departments': len(departments),
        'active_departments': len([d for d in departments if d.is_active]),
        'total_members': UserDepartment.query.filter_by(is_active=True).count(),
        'max_depth': 0
    }

    # 构建树形数据用于D3.js可视化
    def build_tree(dept):
        tree_data = {
            'name': dept.name,
            'code': dept.code,
            'leader': dept.leader.name if dept.leader else None,
            'member_count': dept.members.count()
        }

        children = Department.query.filter_by(parent_id=dept.id, is_active=True).order_by(Department.sort_order).all()
        if children:
            tree_data['children'] = [build_tree(child) for child in children]

        return tree_data

    # 构建树形数据 - 支持多个根部门
    root_departments = Department.query.filter_by(parent_id=None, is_active=True).order_by(Department.sort_order).all()

    if root_departments:
        if len(root_departments) == 1:
            # 如果只有一个根部门，直接使用该部门
            tree_data = build_tree(root_departments[0])
        else:
            # 如果有多个根部门，创建一个虚拟根节点
            tree_data = {
                'name': '组织架构',
                'code': 'ROOT',
                'leader': None,
                'member_count': sum(dept.members.count() for dept in root_departments),
                'children': [build_tree(dept) for dept in root_departments]
            }
    else:
        # 如果没有部门，创建一个空的根节点
        tree_data = {
            'name': '组织架构',
            'code': 'ROOT',
            'leader': None,
            'member_count': 0
        }

    return render_template('admin/departments_standalone.html',
                         page_title='部门管理',
                         page_icon='fas fa-building',
                         departments=departments,
                         users=users,
                         stats=stats,
                         tree_data=tree_data)


@organization.route('/admin/departments/<int:dept_id>')
@login_required
@admin_required
def view_department(dept_id):
    """查看部门详情"""
    try:
        department = Department.query.get_or_404(dept_id)

        # 获取部门成员
        members = []
        for membership in department.members:
            if membership.is_active:
                members.append({
                    'id': membership.user.id,
                    'name': membership.user.name,
                    'username': membership.user.username,
                    'email': membership.user.email,
                    'role': membership.role,
                    'joined_at': membership.joined_at
                })

        # 获取子部门
        children = department.children

        # 获取关联项目
        projects = []
        for project in department.projects:
            if project.is_active:
                projects.append(project)

        # 获取所有部门（用于上级部门选择）
        all_departments = Department.query.filter_by(is_active=True).all()

        # 获取所有用户（用于负责人选择）
        all_users = User.query.filter_by(is_active=True).all()

        # 构建部门层级路径
        hierarchy = []
        current = department
        hierarchy.insert(0, {
            'id': current.id,
            'name': current.name,
            'level': 0
        })

        level = 1
        ancestors = department.get_ancestors()
        for ancestor in reversed(ancestors):
            hierarchy.insert(0, {
                'id': ancestor.id,
                'name': ancestor.name,
                'level': level
            })
            level += 1

        # 统计信息
        stats = {
            'members_count': len(members),
            'active_members_count': len([m for m in members if m['role'] in ['manager', 'lead']]),
            'children_count': len(children),
            'projects_count': len(projects)
        }

        # 为子部门添加成员数量
        children_data = []
        for child in children:
            members_count = child.members.filter_by(is_active=True).count()
            children_data.append({
                'id': child.id,
                'name': child.name,
                'is_active': child.is_active,
                'members_count': members_count
            })

        return render_template('admin/department_view.html',
                             department=department,
                             members=members,
                             children=children_data,
                             projects=projects,
                             all_departments=all_departments,
                             all_users=all_users,
                             department_hierarchy=hierarchy,
                             stats=stats)

    except Exception as e:
        current_app.logger.error(f"查看部门详情失败: {e}")
        flash('查看部门详情失败', 'error')
        return redirect(url_for('admin.departments'))


@organization.route('/admin/departments/create', methods=['POST'])
@login_required
@admin_required
def admin_create_department():
    """创建部门"""
    try:
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '').strip()
        parent_id = request.form.get('parent_id')
        leader_id = request.form.get('leader_id')

        # 验证必填字段
        if not name or not code:
            flash('部门名称和代码为必填项', 'error')
            return redirect(url_for('organization.admin_departments'))

        # 检查代码是否已存在
        if Department.query.filter_by(code=code).first():
            flash('部门代码已存在', 'error')
            return redirect(url_for('organization.admin_departments'))

        # 创建部门
        department = Department(
            name=name,
            code=code,
            description=description,
            parent_id=int(parent_id) if parent_id else None,
            leader_id=int(leader_id) if leader_id else None,
            is_active=True,
            created_by=current_user.id
        )

        db.session.add(department)
        db.session.commit()

        flash(f'部门 "{name}" 创建成功', 'success')

    except Exception as e:
        current_app.logger.error(f"创建部门失败: {e}")
        flash('创建部门失败，请重试', 'error')

    return redirect(url_for('organization.admin_departments'))


@organization.route('/admin/projects')
@login_required
@admin_required
def admin_projects():
    """管理员项目管理页面"""
    # 获取所有项目
    projects = Project.query.order_by(Project.created_at.desc()).all()
    departments = Department.query.filter_by(is_active=True).order_by(Department.sort_order, Department.name).all()
    users = User.query.filter_by(is_active=True).order_by(User.name).all()

    # 计算统计数据
    stats = {
        'total_projects': len(projects),
        'active_projects': len([p for p in projects if p.status == 'active']),
        'completed_projects': len([p for p in projects if p.status == 'completed']),
        'total_members': UserProject.query.filter_by(is_active=True).count()
    }

    return render_template('admin/projects_standalone.html',
                         page_title='项目管理',
                         page_icon='fas fa-project-diagram',
                         projects=projects,
                         departments=departments,
                         users=users,
                         stats=stats)


@organization.route('/admin/projects/create', methods=['POST'])
@login_required
@admin_required
def admin_create_project():
    """创建项目"""
    try:
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '').strip()
        department_id = request.form.get('department_id')
        manager_id = request.form.get('manager_id')
        status = request.form.get('status', 'active')
        priority = request.form.get('priority', 'medium')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        # 验证必填字段
        if not name or not code:
            flash('项目名称和代码为必填项', 'error')
            return redirect(url_for('organization.admin_projects'))

        # 检查代码是否已存在
        if Project.query.filter_by(code=code).first():
            flash('项目代码已存在', 'error')
            return redirect(url_for('organization.admin_projects'))

        # 创建项目
        project = Project(
            name=name,
            code=code,
            description=description,
            department_id=int(department_id) if department_id else None,
            manager_id=int(manager_id) if manager_id else None,
            status=status,
            priority=priority,
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None,
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None,
            is_active=True
        )

        db.session.add(project)
        db.session.commit()

        flash(f'项目 "{name}" 创建成功', 'success')

    except Exception as e:
        current_app.logger.error(f"创建项目失败: {e}")
        flash('创建项目失败，请重试', 'error')

    return redirect(url_for('organization.admin_projects'))


@organization.route('/admin/workspaces')
@login_required
@admin_required
def admin_workspaces():
    """管理员工作区管理页面"""
    # 获取所有工作区
    workspaces = Workspace.query.order_by(Workspace.created_at.desc()).all()
    departments = Department.query.filter_by(is_active=True).order_by(Department.sort_order, Department.name).all()
    projects = Project.query.filter_by(is_active=True).order_by(Project.name).all()
    users = User.query.filter_by(is_active=True).order_by(User.name).all()

    # 计算统计数据
    stats = {
        'total_workspaces': len(workspaces),
        'active_workspaces': len([w for w in workspaces if w.is_active]),
        'public_workspaces': len([w for w in workspaces if w.is_public]),
        'total_members': UserWorkspace.query.filter_by(is_active=True).count()
    }

    return render_template('admin/workspaces_standalone.html',
                         page_title='工作区管理',
                         page_icon='fas fa-th-large',
                         workspaces=workspaces,
                         departments=departments,
                         projects=projects,
                         users=users,
                         stats=stats)


@organization.route('/admin/workspaces/create', methods=['POST'])
@login_required
@admin_required
def admin_create_workspace():
    """创建工作区"""
    try:
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()
        description = request.form.get('description', '').strip()
        workspace_type = request.form.get('type', 'department')
        department_id = request.form.get('department_id')
        project_id = request.form.get('project_id')
        owner_id = request.form.get('owner_id')
        is_public = request.form.get('is_public') == '1'

        # 验证必填字段
        if not name or not code:
            flash('工作区名称和代码为必填项', 'error')
            return redirect(url_for('organization.admin_workspaces'))

        # 检查代码是否已存在
        if Workspace.query.filter_by(code=code).first():
            flash('工作区代码已存在', 'error')
            return redirect(url_for('organization.admin_workspaces'))

        # 创建工作区
        workspace = Workspace(
            name=name,
            code=code,
            description=description,
            type=workspace_type,
            department_id=int(department_id) if department_id else None,
            project_id=int(project_id) if project_id else None,
            owner_id=int(owner_id) if owner_id else None,
            is_public=is_public,
            is_active=True
        )

        db.session.add(workspace)
        db.session.commit()

        flash(f'工作区 "{name}" 创建成功', 'success')

    except Exception as e:
        current_app.logger.error(f"创建工作区失败: {e}")
        flash('创建工作区失败，请重试', 'error')

    return redirect(url_for('organization.admin_workspaces'))


@organization.route('/api/organization/tree')
@login_required
def get_organization_tree():
    """获取组织架构树形数据"""
    try:
        # 获取根部门
        root_department = Department.query.filter_by(parent_id=None, is_active=True).first()

        if not root_department:
            return jsonify({})

        # 构建树形结构
        def build_tree_data(dept):
            tree_data = {
                'name': dept.name,
                'code': dept.code,
                'leader': dept.leader.name if dept.leader else None,
                'member_count': dept.members.count()
            }

            children = Department.query.filter_by(parent_id=dept.id, is_active=True).order_by(Department.sort_order).all()
            if children:
                tree_data['children'] = [build_tree_data(child) for child in children]

            return tree_data

        tree_data = build_tree_data(root_department)
        return jsonify(tree_data)

    except Exception as e:
        current_app.logger.error(f"获取组织架构数据失败: {e}")
        return jsonify({})


@organization.route('/admin/api/departments')
@login_required
@admin_required
def get_departments_api():
    """获取部门列表API"""
    try:
        departments = Department.query.order_by(Department.sort_order, Department.name).all()
        return jsonify([{
            'id': dept.id,
            'name': dept.name,
            'code': dept.code,
            'parent_id': dept.parent_id,
            'leader_id': dept.leader_id,
            'get_full_name': dept.get_full_name() if hasattr(dept, 'get_full_name') else dept.name
        } for dept in departments])
    except Exception as e:
        current_app.logger.error(f"获取部门列表失败: {e}")
        return jsonify({'error': str(e)}), 500


@organization.route('/admin/api/users')
@login_required
@admin_required
def get_users_api():
    """获取用户列表API"""
    try:
        users = User.query.filter_by(is_active=True).order_by(User.name).all()
        return jsonify([{
            'id': user.id,
            'name': user.name,
            'username': user.username,
            'email': user.email
        } for user in users])
    except Exception as e:
        current_app.logger.error(f"获取用户列表失败: {e}")
        return jsonify({'error': str(e)}), 500


@organization.route('/admin/api/batch-add-departments', methods=['POST'])
@login_required
@admin_required
def batch_add_departments():
    """批量添加部门API"""
    try:
        data = request.get_json()
        parent_id = data.get('parent_id')
        prefix = data.get('prefix', 'DEPT')
        dept_names = data.get('dept_names', [])
        description_template = data.get('description_template', '{name}，负责相关业务')

        if not dept_names:
            return jsonify({'success': False, 'message': '部门名称列表不能为空'})

        created_count = 0
        errors = []

        for dept_name in dept_names:
            try:
                dept_name = dept_name.strip()
                if not dept_name:
                    continue

                # 生成部门代码
                import re
                # 移除中文字符，只保留字母数字
                name_en = re.sub(r'[^\w\s]', '', dept_name)
                # 转换为拼音或简单英文缩写
                code_suffix = ''.join([word[0].upper() for word in name_en.split() if word])[:8]
                if not code_suffix:
                    code_suffix = f"DEPT{Department.query.count() + created_count + 1:03d}"

                dept_code = f"{prefix}_{code_suffix}"

                # 检查代码是否已存在
                while Department.query.filter_by(code=dept_code).first():
                    created_count += 1
                    dept_code = f"{prefix}_{code_suffix}{created_count:02d}"

                # 创建部门
                department = Department(
                    name=dept_name,
                    code=dept_code,
                    description=description_template.format(name=dept_name),
                    parent_id=int(parent_id) if parent_id else None,
                    is_active=True,
                    created_by=current_user.id
                )

                db.session.add(department)
                created_count += 1

            except Exception as e:
                errors.append(f"创建部门 '{dept_name}' 失败: {str(e)}")
                current_app.logger.error(f"创建部门失败: {e}")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'保存失败: {str(e)}'})

        return jsonify({
            'success': True,
            'created_count': created_count,
            'errors': errors
        })

    except Exception as e:
        current_app.logger.error(f"批量添加部门失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@organization.route('/admin/api/batch-assign-users', methods=['POST'])
@login_required
@admin_required
def batch_assign_users():
    """批量分配用户到部门API"""
    try:
        data = request.get_json()
        department_id = data.get('department_id')
        user_ids = data.get('user_ids', [])
        role = data.get('role', 'member')

        if not department_id or not user_ids:
            return jsonify({'success': False, 'message': '请选择部门和用户'})

        department = Department.query.get(department_id)
        if not department:
            return jsonify({'success': False, 'message': '部门不存在'})

        assigned_count = 0
        errors = []

        for user_id in user_ids:
            try:
                user = User.query.get(user_id)
                if not user:
                    errors.append(f"用户ID {user_id} 不存在")
                    continue

                # 检查是否已经在部门中
                existing = UserDepartment.query.filter_by(
                    user_id=user_id,
                    department_id=department_id
                ).first()

                if existing:
                    if not existing.is_active:
                        existing.is_active = True
                        existing.role = role
                        assigned_count += 1
                    continue

                # 创建新的部门用户关系
                user_dept = UserDepartment(
                    user_id=user_id,
                    department_id=department_id,
                    role=role,
                    is_active=True,
                    joined_at=datetime.utcnow(),
                    created_by=current_user.id
                )

                db.session.add(user_dept)
                assigned_count += 1

                # 如果是领导角色，更新部门领导
                if role == 'leader' and not department.leader_id:
                    department.leader_id = user_id

            except Exception as e:
                errors.append(f"分配用户 {user_id} 失败: {str(e)}")
                current_app.logger.error(f"分配用户失败: {e}")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'保存失败: {str(e)}'})

        return jsonify({
            'success': True,
            'assigned_count': assigned_count,
            'errors': errors
        })

    except Exception as e:
        current_app.logger.error(f"批量分配用户失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@organization.route('/admin/api/export-org-chart')
@login_required
@admin_required
def export_org_chart():
    """导出组织架构数据"""
    try:
        import io
        import xlsxwriter
        from flask import send_file

        # 创建内存中的Excel文件
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('组织架构')

        # 设置表头
        headers = ['部门名称', '部门代码', '上级部门', '部门领导', '成员数量', '创建时间']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        # 获取所有部门
        departments = Department.query.filter_by(is_active=True).order_by(Department.sort_order, Department.name).all()

        row = 1
        for dept in departments:
            worksheet.write(row, 0, dept.name)
            worksheet.write(row, 1, dept.code)
            worksheet.write(row, 2, dept.parent.name if dept.parent else '')
            worksheet.write(row, 3, dept.leader.name if dept.leader else '')
            worksheet.write(row, 4, dept.members.count())
            worksheet.write(row, 5, dept.created_at.strftime('%Y-%m-%d %H:%M:%S'))
            row += 1

        workbook.close()
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name=f'组织架构数据_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        current_app.logger.error(f"导出组织架构失败: {e}")
        return jsonify({'error': str(e)}), 500


@organization.route('/admin/api/download-org-template')
@login_required
@admin_required
def download_org_template():
    """下载组织架构导入模板"""
    try:
        import io
        import xlsxwriter
        from flask import send_file

        # 创建内存中的Excel文件
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('导入模板')

        # 设置表头
        headers = ['部门名称', '部门代码', '上级部门代码', '部门领导用户名', '部门描述']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        # 添加示例数据
        examples = [
            ['技术研发部', 'TECH_DEPT', '', 'admin', '负责技术研发工作'],
            ['产品设计部', 'DESIGN_DEPT', 'TECH_DEPT', '', '负责产品设计工作'],
            ['市场营销部', 'MARKETING_DEPT', '', '', '负责市场推广工作']
        ]

        for row, example in enumerate(examples, start=1):
            for col, value in enumerate(example):
                worksheet.write(row, col, value)

        workbook.close()
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name='组织架构导入模板.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        current_app.logger.error(f"下载模板失败: {e}")
        return jsonify({'error': str(e)}), 500




@organization.route('/admin/api/department/<int:dept_id>')
@login_required
@admin_required
def get_department_api(dept_id):
    """获取单个部门信息API"""
    try:
        department = Department.query.get_or_404(dept_id)

        return jsonify({
            'success': True,
            'department': {
                'id': department.id,
                'name': department.name,
                'code': department.code,
                'description': department.description,
                'parent_id': department.parent_id,
                'leader_id': department.leader_id,
                'is_active': department.is_active,
                'sort_order': department.sort_order,
                'created_at': department.created_at.isoformat() if department.created_at else None,
                'get_full_name': department.get_full_name() if hasattr(department, 'get_full_name') else department.name
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取部门信息失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@organization.route('/admin/api/department/update', methods=['POST'])
@login_required
@admin_required
def update_department_api():
    """更新部门API"""
    try:
        data = request.get_json()

        dept_id = data.get('id')
        name = data.get('name', '').strip()
        code = data.get('code', '').strip()
        description = data.get('description', '').strip()
        parent_id = data.get('parent_id')
        leader_id = data.get('leader_id')
        is_active = data.get('is_active', True)
        sort_order = data.get('sort_order', 0)

        # 验证必填字段
        if not name or not code:
            return jsonify({'success': False, 'message': '部门名称和代码为必填项'})

        # 验证代码格式
        import re
        if not re.match(r'^[A-Z0-9_]+$', code):
            return jsonify({'success': False, 'message': '部门代码只能使用大写字母、数字和下划线'})

        # 获取部门
        department = Department.query.get_or_404(dept_id)

        # 检查代码是否与其他部门冲突
        existing = Department.query.filter(
            Department.code == code,
            Department.id != dept_id
        ).first()
        if existing:
            return jsonify({'success': False, 'message': '部门代码已存在'})

        # 检查循环依赖
        if parent_id:
            parent_department = Department.query.get(parent_id)
            if parent_department and _would_create_cycle(department, parent_id):
                return jsonify({'success': False, 'message': '不能设置此部门为上级部门，会造成循环依赖'})

        # 更新部门信息
        department.name = name
        department.code = code
        department.description = description
        department.parent_id = int(parent_id) if parent_id else None
        department.leader_id = int(leader_id) if leader_id else None
        department.is_active = is_active
        department.sort_order = sort_order
        department.updated_at = datetime.utcnow()
        department.updated_by = current_user.id

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '部门更新成功'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新部门失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@organization.route('/admin/api/department/<int:dept_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_department_api(dept_id):
    """删除部门API"""
    try:
        department = Department.query.get_or_404(dept_id)

        # 检查是否有子部门
        children = Department.query.filter_by(parent_id=dept_id).all()
        if children:
            return jsonify({
                'success': False,
                'message': f'无法删除部门 "{department.name}"，因为它包含 {len(children)} 个子部门'
            })

        # 检查是否有成员
        if department.members.count() > 0:
            return jsonify({
                'success': False,
                'message': f'无法删除部门 "{department.name}"，因为它还有 {department.members.count()} 个成员'
            })

        # 检查有关联的项目
        projects = Project.query.filter_by(department_id=dept_id).all()
        if projects:
            return jsonify({
                'success': False,
                'message': f'无法删除部门 "{department.name}"，因为它还关联着 {len(projects)} 个项目'
            })

        # 检查有关联的工作区
        workspaces = Workspace.query.filter_by(department_id=dept_id).all()
        if workspaces:
            return jsonify({
                'success': False,
                'message': f'无法删除部门 "{department.name}"，因为它还关联着 {len(workspaces)} 个工作区'
            })

        # 删除部门
        db.session.delete(department)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '部门删除成功'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除部门失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


def _would_create_cycle(department, parent_id):
    """检查设置父部门是否会造成循环依赖"""
    if parent_id is None or parent_id == 0:
        return False
    if parent_id == department.id:
        return True

    # 使用DFS检查循环
    visited = set()
    stack = [parent_id]

    while stack:
        current_id = stack.pop()
        if current_id in visited:
            continue
        visited.add(current_id)

        if current_id == department.id:
            return True

        # 查找所有子部门
        children = Department.query.filter_by(parent_id=current_id).all()
        for child in children:
            stack.append(child.id)

    return False


@organization.route('/admin/api/project/<int:project_id>')
@login_required
@admin_required
def get_project_api(project_id):
    """获取单个项目信息API"""
    try:
        project = Project.query.get_or_404(project_id)

        return jsonify({
            'success': True,
            'project': {
                'id': project.id,
                'name': project.name,
                'code': project.code,
                'description': project.description or '',
                'department_id': project.department_id,
                'manager_id': project.manager_id,
                'status': project.status,
                'priority': project.priority,
                'start_date': project.start_date.isoformat() if project.start_date else None,
                'end_date': project.end_date.isoformat() if project.end_date else None,
                'is_active': project.is_active
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取项目信息失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@organization.route('/admin/api/project/<int:project_id>', methods=['POST'])
@login_required
@admin_required
def update_project_api(project_id):
    """更新项目信息API"""
    try:
        project = Project.query.get_or_404(project_id)

        # 获取表单数据
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400

        # 验证必填字段
        if not data.get('name') or not data.get('name').strip():
            return jsonify({'success': False, 'message': '项目名称不能为空'}), 400

        if not data.get('code') or not data.get('code').strip():
            return jsonify({'success': False, 'message': '项目代码不能为空'}), 400

        # 检查项目代码是否重复（排除自己）
        existing_project = Project.query.filter(
            Project.code == data['code'].strip(),
            Project.id != project_id
        ).first()
        if existing_project:
            return jsonify({'success': False, 'message': '项目代码已存在'}), 400

        # 更新项目信息
        project.name = data['name'].strip()
        project.code = data['code'].strip()
        project.description = data.get('description', '').strip()
        project.department_id = data.get('department_id') or None
        project.manager_id = data.get('manager_id') or None
        project.status = data.get('status', 'active')
        project.priority = data.get('priority', 'medium')
        project.is_active = data.get('is_active', True)

        # 处理日期
        if data.get('start_date'):
            try:
                project.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'message': '开始日期格式无效'}), 400
        else:
            project.start_date = None

        if data.get('end_date'):
            try:
                project.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'message': '结束日期格式无效'}), 400
        else:
            project.end_date = None

        # 验证日期逻辑
        if project.start_date and project.end_date and project.start_date > project.end_date:
            return jsonify({'success': False, 'message': '开始日期不能晚于结束日期'}), 400

        project.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '项目更新成功',
            'project': {
                'id': project.id,
                'name': project.name,
                'code': project.code,
                'status': project.status,
                'priority': project.priority
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新项目失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@organization.route('/admin/api/project/<int:project_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_project_api(project_id):
    """删除项目API"""
    try:
        project = Project.query.get_or_404(project_id)

        # 检查是否有关联的工作区
        workspaces = Workspace.query.filter_by(project_id=project_id).all()
        if workspaces:
            return jsonify({
                'success': False,
                'message': f'无法删除项目 "{project.name}"，因为它还关联着 {len(workspaces)} 个工作区'
            })

        # 检查是否有关联的成员
        member_count = project.members.count()
        if member_count > 0:
            return jsonify({
                'success': False,
                'message': f'无法删除项目 "{project.name}"，因为它还关联着 {member_count} 个成员'
            })

        # 删除项目
        db.session.delete(project)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '项目删除成功'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除项目失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@organization.route('/admin/api/workspace/<int:workspace_id>')
@login_required
@admin_required
def get_workspace_api(workspace_id):
    """获取单个工作区信息API"""
    try:
        workspace = Workspace.query.get_or_404(workspace_id)

        return jsonify({
            'success': True,
            'workspace': {
                'id': workspace.id,
                'name': workspace.name,
                'code': workspace.code,
                'description': workspace.description or '',
                'type': workspace.type,
                'department_id': workspace.department_id,
                'project_id': workspace.project_id,
                'owner_id': workspace.owner_id,
                'is_public': workspace.is_public,
                'is_active': workspace.is_active,
                'created_at': workspace.created_at.strftime('%Y-%m-%d') if workspace.created_at else None
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取工作区信息失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@organization.route('/admin/api/workspace/<int:workspace_id>', methods=['POST'])
@login_required
@admin_required
def update_workspace_api(workspace_id):
    """更新工作区信息API"""
    try:
        workspace = Workspace.query.get_or_404(workspace_id)

        # 获取表单数据
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400

        # 验证必填字段
        if not data.get('name') or not data.get('name').strip():
            return jsonify({'success': False, 'message': '工作区名称不能为空'}), 400

        if not data.get('code') or not data.get('code').strip():
            return jsonify({'success': False, 'message': '工作区代码不能为空'}), 400

        # 检查工作区代码是否重复（排除自己）
        existing_workspace = Workspace.query.filter(
            Workspace.code == data['code'].strip(),
            Workspace.id != workspace_id
        ).first()
        if existing_workspace:
            return jsonify({'success': False, 'message': '工作区代码已存在'}), 400

        # 验证工作区代码格式
        if not re.match(r'^[A-Z0-9_]+$', data['code'].strip()):
            return jsonify({'success': False, 'message': '工作区代码只能使用大写字母、数字和下划线'}), 400

        # 更新工作区信息
        workspace.name = data['name'].strip()
        workspace.code = data['code'].strip()
        workspace.description = data.get('description', '').strip()
        workspace.type = data.get('type', 'department')
        workspace.department_id = data.get('department_id') or None
        workspace.project_id = data.get('project_id') or None
        workspace.owner_id = data.get('owner_id') or None
        workspace.is_public = data.get('is_public', False)
        workspace.is_active = data.get('is_active', True)

        workspace.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '工作区更新成功',
            'workspace': {
                'id': workspace.id,
                'name': workspace.name,
                'code': workspace.code,
                'type': workspace.type,
                'is_active': workspace.is_active
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新工作区失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@organization.route('/admin/api/workspace/<int:workspace_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_workspace_api(workspace_id):
    """删除工作区API"""
    try:
        workspace = Workspace.query.get_or_404(workspace_id)

        # 检查是否有关联的成员
        member_count = workspace.members.count()
        if member_count > 0:
            return jsonify({
                'success': False,
                'message': f'无法删除工作区 "{workspace.name}"，因为它还关联着 {member_count} 个成员'
            })

        # 删除工作区
        db.session.delete(workspace)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '工作区删除成功'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除工作区失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@organization.route('/admin/workspaces/<int:workspace_id>')
@login_required
@admin_required
def view_workspace(workspace_id):
    """查看工作区详情"""
    try:
        workspace = Workspace.query.get_or_404(workspace_id)

        # 获取工作区成员
        members = UserWorkspace.query.filter_by(
            workspace_id=workspace_id,
            is_active=True
        ).all()

        # 获取所有可用用户（不在当前工作区中的活跃用户）
        current_member_ids = [m.user_id for m in members]
        available_users = User.query.filter(
            User.is_active == True,
            ~User.id.in_(current_member_ids) if current_member_ids else True
        ).all()

        # 获取关联项目
        projects = []
        if workspace.department:
            for project in workspace.department.projects:
                if project.is_active:
                    projects.append(project)

        # 统计信息
        stats = {
            'members_count': len(members),
            'projects_count': len(projects),
            'active_members_count': len([m for m in members if m.user.is_active])
        }

        return render_template('admin/workspace_view.html',
                             workspace=workspace,
                             members=members,
                             available_users=available_users,
                             projects=projects,
                             members_count=stats['members_count'],
                             projects_count=stats['projects_count'],
                             active_members_count=stats['active_members_count'])

    except Exception as e:
        current_app.logger.error(f"查看工作区详情失败: {e}")
        flash('查看工作区详情失败', 'error')
        return redirect(url_for('organization.workspaces_standalone'))


@organization.route('/admin/api/workspace/<int:workspace_id>/add_member', methods=['POST'])
@login_required
@admin_required
def add_workspace_member(workspace_id):
    """添加工作区成员"""
    try:
        workspace = Workspace.query.get_or_404(workspace_id)
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'message': '用户ID不能为空'}), 400

        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'}), 404

        # 检查是否已经是成员
        existing = UserWorkspace.query.filter_by(
            workspace_id=workspace_id,
            user_id=user_id
        ).first()

        if existing:
            if existing.is_active:
                return jsonify({'success': False, 'message': '用户已经是工作区成员'}), 400
            else:
                # 重新激活成员
                existing.is_active = True
                existing.joined_at = datetime.utcnow()
        else:
            # 添加新成员
            membership = UserWorkspace(
                workspace_id=workspace_id,
                user_id=user_id,
                role='member',
                joined_at=datetime.utcnow(),
                is_active=True
            )
            db.session.add(membership)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '成员添加成功'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"添加工作区成员失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@organization.route('/admin/api/workspace/<int:workspace_id>/remove_member', methods=['POST'])
@login_required
@admin_required
def remove_workspace_member(workspace_id):
    """移除工作区成员"""
    try:
        workspace = Workspace.query.get_or_404(workspace_id)
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'success': False, 'message': '用户ID不能为空'}), 400

        # 查找成员关系
        membership = UserWorkspace.query.filter_by(
            workspace_id=workspace_id,
            user_id=user_id
        ).first()

        if not membership:
            return jsonify({'success': False, 'message': '用户不是工作区成员'}), 404

        # 停用成员关系（而不是删除）
        membership.is_active = False
        membership.left_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '成员移除成功'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"移除工作区成员失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500