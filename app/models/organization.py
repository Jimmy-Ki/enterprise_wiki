"""
组织架构模型 - Department, Project, Workspace, User relationships
"""

from datetime import datetime
from app import db
import json


class Department(db.Model):
    """部门模型 - 支持层级结构"""
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True, nullable=False)
    code = db.Column(db.String(32), unique=True, index=True, nullable=False)  # 部门代码
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)  # 部门负责人
    is_active = db.Column(db.Boolean, default=True, index=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # 关系 - 简化定义避免循环依赖
    parent = db.relationship('Department', remote_side=[id], backref='children')
    leader = db.relationship('User', foreign_keys=[leader_id])
    creator = db.relationship('User', foreign_keys=[created_by])
    projects = db.relationship('Project', backref='department', lazy='dynamic')
    workspaces = db.relationship('Workspace', backref='department', lazy='dynamic')
    members = db.relationship('UserDepartment', back_populates='department', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Department {self.name}>'

    def get_full_name(self):
        """获取部门完整路径名称"""
        if self.parent:
            return f'{self.parent.get_full_name()} > {self.name}'
        return self.name

    def get_ancestors(self):
        """获取所有上级部门"""
        ancestors = []
        current = self.parent
        visited = set()

        while current and current.id not in visited:
            ancestors.append(current)
            visited.add(current.id)
            current = current.parent

        return ancestors

    def get_descendants(self):
        """获取所有下级部门"""
        descendants = []
        stack = [self]
        visited = set()

        while stack:
            current = stack.pop()
            if current.id in visited:
                continue

            visited.add(current.id)
            for child in current.children:
                if child.id not in visited:
                    descendants.append(child)
                    stack.append(child)

        return descendants

    def would_create_cycle(self, parent_id):
        """检查设置父部门是否会造成循环依赖"""
        if parent_id is None or parent_id == 0:
            return False

        # 不能设置自己为父部门
        if parent_id == self.id:
            return True

        # 检查潜在的父部门是否是自己的子部门
        from app.models.user import User
        potential_parent = Department.query.get(parent_id)
        if not potential_parent:
            return False

        # DFS检查是否会造成循环
        stack = [potential_parent]
        visited = set()

        while stack:
            current = stack.pop()
            if current.id in visited:
                continue

            visited.add(current.id)
            if current.id == self.id:
                return True  # 会造成循环

            for child in current.children:
                if child.id not in visited:
                    stack.append(child)

        return False

    def get_all_members(self):
        """获取部门所有成员（包括子部门）"""
        all_members = []
        departments = [self] + self.get_descendants()

        for dept in departments:
            for member_rel in dept.members:
                all_members.append(member_rel.user)

        return list(set(all_members))  # 去重

    def can_user_manage(self, user):
        """检查用户是否可以管理此部门"""
        if user.is_administrator():
            return True
        if self.leader_id == user.id:
            return True

        # 检查是否是上级部门的领导
        ancestors = self.get_ancestors()
        for ancestor in ancestors:
            if ancestor.leader_id == user.id:
                return True

        return False


class Project(db.Model):
    """项目模型"""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, index=True)
    code = db.Column(db.String(32), unique=True, index=True, nullable=False)
    description = db.Column(db.Text)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    status = db.Column(db.String(20), default='active', index=True)  # active, completed, archived, on_hold
    priority = db.Column(db.String(10), default='medium')  # low, medium, high, critical
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # 关系 - 简化定义避免循环依赖
    manager = db.relationship('User', foreign_keys=[manager_id])
    creator = db.relationship('User', foreign_keys=[created_by])
    workspaces = db.relationship('Workspace', backref='project', lazy='dynamic')
    members = db.relationship('UserProject', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Project {self.name}>'

    def get_all_members(self):
        """获取项目所有成员"""
        return [member_rel.user for member_rel in self.members]

    def can_user_manage(self, user):
        """检查用户是否可以管理此项目"""
        if user.is_administrator():
            return True
        if self.manager_id == user.id:
            return True
        if self.department and self.department.leader_id == user.id:
            return True
        if self.department and self.department.can_user_manage(user):
            return True
        return False


class Workspace(db.Model):
    """工作区模型 - 用于隔离不同团队的知识库"""
    __tablename__ = 'workspaces'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, index=True)
    code = db.Column(db.String(32), unique=True, index=True, nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(20), default='department', index=True)  # department, project, cross_functional, personal
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_public = db.Column(db.Boolean, default=False)  # 是否对所有内部人员开放
    settings = db.Column(db.Text)  # JSON格式的设置
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系 - 简化定义避免循环依赖
    owner = db.relationship('User', backref='owned_workspaces')
    members = db.relationship('UserWorkspace', back_populates='workspace', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Workspace {self.name}>'

    def get_settings(self):
        """获取工作区设置"""
        if self.settings:
            try:
                return json.loads(self.settings)
            except (json.JSONDecodeError, TypeError):
                pass
        return {}

    def set_settings(self, settings_dict):
        """设置工作区配置"""
        self.settings = json.dumps(settings_dict)

    def can_user_access(self, user):
        """检查用户是否可以访问此工作区"""
        if user.is_administrator():
            return True
        if self.owner_id == user.id:
            return True
        if self.is_public and user.is_authenticated:
            return True

        # 检查成员关系
        member = UserWorkspace.query.filter_by(
            workspace_id=self.id,
            user_id=user.id
        ).first()
        if member:
            return True

        # 检查部门权限
        if self.department_id and self.department:
            if self.department.leader_id == user.id:
                return True
            # 检查是否是部门成员
            dept_member = UserDepartment.query.filter_by(
                department_id=self.department_id,
                user_id=user.id
            ).first()
            if dept_member:
                return True

        # 检查项目权限
        if self.project_id and self.project:
            if self.project.can_user_manage(user):
                return True
            project_member = UserProject.query.filter_by(
                project_id=self.project_id,
                user_id=user.id
            ).first()
            if project_member:
                return True

        return False


class UserDepartment(db.Model):
    """用户-部门关系模型"""
    __tablename__ = 'user_departments'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), primary_key=True)
    role = db.Column(db.String(20), default='member', index=True)  # member, manager, lead
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # 关系 - 明确指定外键避免冲突
    user = db.relationship('User', back_populates='department_memberships',
                         foreign_keys=[user_id])
    department = db.relationship('Department', back_populates='members')
    creator = db.relationship('User', foreign_keys=[created_by])

    def __repr__(self):
        return f'<UserDepartment {self.user_id}-{self.department_id}>'

    def can_manage_department(self):
        """检查是否可以管理部门"""
        return self.role in ['manager', 'lead'] and self.is_active


class UserProject(db.Model):
    """用户-项目关系模型"""
    __tablename__ = 'user_projects'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), primary_key=True)
    role = db.Column(db.String(20), default='member', index=True)  # member, manager, lead, developer
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # 关系 - 明确指定外键避免冲突
    user = db.relationship('User', back_populates='project_memberships',
                         foreign_keys=[user_id])
    project = db.relationship('Project', back_populates='members')
    creator = db.relationship('User', foreign_keys=[created_by])

    def __repr__(self):
        return f'<UserProject {self.user_id}-{self.project_id}>'

    def can_manage_project(self):
        """检查是否可以管理项目"""
        return self.role in ['manager', 'lead'] and self.is_active


class UserWorkspace(db.Model):
    """用户-工作区关系模型"""
    __tablename__ = 'user_workspaces'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspaces.id'), primary_key=True)
    role = db.Column(db.String(20), default='member', index=True)  # member, manager, admin
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    left_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # 关系 - 明确指定外键避免冲突
    user = db.relationship('User', back_populates='workspace_memberships',
                         foreign_keys=[user_id])
    workspace = db.relationship('Workspace', back_populates='members')
    creator = db.relationship('User', foreign_keys=[created_by])

    def __repr__(self):
        return f'<UserWorkspace {self.user_id}-{self.workspace_id}>'

    def can_manage_workspace(self):
        """检查是否可以管理工作区"""
        return self.role in ['manager', 'admin'] and self.is_active


class AccessLevel:
    """访问权限等级常量"""
    PUBLIC = 1      # 所有人可见
    INTERNAL = 2    # 内部人员可见
    DEPARTMENT = 3  # 部门可见
    PROJECT = 4     # 项目可见
    EXECUTIVE = 5   # 高层机密
    PRIVATE = 6     # 个人隐私

    @classmethod
    def get_choices(cls):
        return [
            (cls.PUBLIC, '公开'),
            (cls.INTERNAL, '内部'),
            (cls.DEPARTMENT, '部门'),
            (cls.PROJECT, '项目'),
            (cls.EXECUTIVE, '高层机密'),
            (cls.PRIVATE, '私人')
        ]

    @classmethod
    def get_label(cls, level):
        labels = dict(cls.get_choices())
        return labels.get(level, '未知')


# 权限检查服务类
class OrganizationService:
    """组织架构权限检查服务"""

    @staticmethod
    def get_user_leader_chain(user):
        """获取用户的领导链"""
        leaders = []
        visited = set()
        current_user = user

        while current_user and current_user.id not in visited:
            visited.add(current_user.id)

            # 检查部门领导
            dept_membership = UserDepartment.query.filter_by(
                user_id=current_user.id,
                is_active=True
            ).first()

            if dept_membership and dept_membership.department:
                dept_leader = dept_membership.department.leader
                if dept_leader and dept_leader.id not in visited:
                    leaders.append(dept_leader)
                    current_user = dept_leader
                    continue

            # 检查项目负责人
            proj_membership = UserProject.query.filter_by(
                user_id=current_user.id,
                is_active=True
            ).first()

            if proj_membership and proj_membership.project:
                proj_manager = proj_membership.project.manager
                if proj_manager and proj_manager.id not in visited:
                    leaders.append(proj_manager)
                    current_user = proj_manager
                    continue

            # 如果没有找到更高级的领导，跳出循环
            break

        return leaders

    @staticmethod
    def can_user_manage_user(manager, target_user):
        """检查manager是否可以管理target_user"""
        if manager.is_administrator():
            return True

        # 不能管理自己
        if manager.id == target_user.id:
            return False

        # 获取目标用户的领导链
        leader_chain = OrganizationService.get_user_leader_chain(target_user)
        return manager in leader_chain

    @staticmethod
    def check_hierarchy_integrity():
        """检查整个组织架构的完整性，发现潜在的循环依赖"""
        issues = []

        # 检查部门层级
        departments = Department.query.filter_by(is_active=True).all()
        for dept in departments:
            # 检查部门领导是否会造成循环
            if dept.leader:
                # 检查领导是否是此部门的成员
                leader_membership = UserDepartment.query.filter_by(
                    user_id=dept.leader_id,
                    department_id=dept.id,
                    is_active=True
                ).first()
                if not leader_membership:
                    issues.append(f"部门 {dept.name} 的领导 {dept.leader.username} 不是部门成员")

            # 检查层级循环
            if dept.parent_id:
                if dept.would_create_cycle(dept.parent_id):
                    issues.append(f"部门 {dept.name} 设置父部门会造成循环依赖")

        # 检查项目领导
        projects = Project.query.filter_by(is_active=True).all()
        for project in projects:
            if project.manager:
                manager_membership = UserProject.query.filter_by(
                    user_id=project.manager_id,
                    project_id=project.id,
                    is_active=True
                ).first()
                if not manager_membership:
                    issues.append(f"项目 {project.name} 的经理 {project.manager.username} 不是项目成员")

        return issues