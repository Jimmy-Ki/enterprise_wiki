#!/usr/bin/env python3
"""
创建测试数据脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Page, Category
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_test_users():
    """创建测试用户"""
    print("创建测试用户...")

    # 获取管理员角色
    from app.models.user import Role
    admin_role = Role.query.filter_by(name='Administrator').first()
    if not admin_role:
        admin_role = Role(name='Administrator', permissions='admin')
        db.session.add(admin_role)
        db.session.commit()
        print("✓ 创建管理员角色")

    user_role = Role.query.filter_by(name='User').first()
    if not user_role:
        user_role = Role(name='User', permissions='user')
        db.session.add(user_role)
        db.session.commit()
        print("✓ 创建用户角色")

    # Admin用户
    admin = User.query.filter_by(email='admin@jimmyki.com').first()
    if not admin:
        admin = User(
            email='admin@jimmyki.com',
            username='admin',
            password_hash=generate_password_hash('jG679322'),
            role_id=admin_role.id,
            confirmed=True,
            name='Administrator'
        )
        db.session.add(admin)
        print("✓ 创建管理员用户: admin@jimmyki.com")
    else:
        print("✓ 管理员用户已存在: admin@jimmyki.com")

    # 江梦琦用户
    jiang_mengqi = User.query.filter_by(email='jimmyki@qq.com').first()
    if not jiang_mengqi:
        jiang_mengqi = User(
            email='jimmyki@qq.com',
            username='江梦琦',
            password_hash=generate_password_hash('jG679322'),
            role_id=user_role.id,
            confirmed=True,
            name='江梦琦'
        )
        db.session.add(jiang_mengqi)
        print("✓ 创建用户: 江梦琦 (jimmyki@qq.com)")
    else:
        print("✓ 用户已存在: 江梦琦 (jimmyki@qq.com)")

    # 创建更多测试用户
    test_users = [
        {
            'email': 'zhangsan@company.com',
            'username': '张三',
            'password': 'password123',
            'name': '张三'
        },
        {
            'email': 'lisi@company.com',
            'username': '李四',
            'password': 'password123',
            'name': '李四'
        },
        {
            'email': 'wangwu@company.com',
            'username': '王五',
            'password': 'password123',
            'name': '王五'
        },
        {
            'email': 'editor@company.com',
            'username': '编辑员',
            'password': 'password123',
            'name': '编辑员'
        },
        {
            'email': 'viewer@company.com',
            'username': '查看者',
            'password': 'password123',
            'name': '查看者'
        }
    ]

    for user_data in test_users:
        existing_user = User.query.filter_by(email=user_data['email']).first()
        if not existing_user:
            user = User(
                email=user_data['email'],
                username=user_data['username'],
                password_hash=generate_password_hash(user_data['password']),
                role_id=user_role.id,
                confirmed=True,
                name=user_data['name']
            )
            db.session.add(user)
            print(f"✓ 创建用户: {user_data['username']} ({user_data['email']})")
        else:
            print(f"✓ 用户已存在: {user_data['username']} ({user_data['email']})")

    db.session.commit()
    print("用户创建完成！")

def create_test_categories():
    """创建测试分类"""
    print("\n创建测试分类...")

    categories_data = [
        {
            'name': '产品文档',
            'description': '产品相关文档和说明'
        },
        {
            'name': '技术文档',
            'description': '技术开发和架构文档'
        },
        {
            'name': '项目文档',
            'description': '项目管理和进度文档'
        },
        {
            'name': '会议记录',
            'description': '各类会议纪要和记录'
        },
        {
            'name': '培训资料',
            'description': '培训和学习材料'
        },
        {
            'name': '公司制度',
            'description': '公司规章制度和流程'
        }
    ]

    for cat_data in categories_data:
        existing_cat = Category.query.filter_by(name=cat_data['name']).first()
        if not existing_cat:
            category = Category(
                name=cat_data['name'],
                description=cat_data['description'],
                is_public=True
            )
            db.session.add(category)
            print(f"✓ 创建分类: {cat_data['name']}")
        else:
            print(f"✓ 分类已存在: {cat_data['name']}")

    db.session.commit()
    print("分类创建完成！")

def create_test_pages():
    """创建测试文章"""
    print("\n创建测试文章...")

    # 获取用户和分类
    admin = User.query.filter_by(email='admin@jimmyki.com').first()
    jiang_mengqi = User.query.filter_by(email='jimmyki@qq.com').first()
    zhangsan = User.query.filter_by(email='zhangsan@company.com').first()

    tech_cat = Category.query.filter_by(name='技术文档').first()
    product_cat = Category.query.filter_by(name='产品文档').first()
    project_cat = Category.query.filter_by(name='项目文档').first()
    meeting_cat = Category.query.filter_by(name='会议记录').first()

    # 创建测试文章
    pages_data = [
        {
            'title': '系统架构设计文档',
            'content': '''# 系统架构设计文档

## 概述

本文档描述了企业Wiki系统的整体架构设计，包括技术选型、模块划分和部署方案。

## 技术栈

- **后端框架**: Flask + SQLAlchemy
- **前端框架**: Bootstrap + jQuery
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **认证**: Flask-Login
- **缓存**: Redis (可选)

## 系统架构

```mermaid
graph TD
    A[用户界面] --> B[Flask Web服务]
    B --> C[业务逻辑层]
    C --> D[数据访问层]
    D --> E[数据库]

    F[文件存储] --> G[本地文件系统]
    H[搜索引擎] --> I[数据库全文搜索]
```

## 核心模块

### 1. 用户管理模块
- 用户注册、登录、权限管理
- 支持多种用户角色
- 密码加密和会话管理

### 2. 文档管理模块
- 页面创建、编辑、版本控制
- 分类管理和组织
- 权限控制

### 3. 搜索模块
- 全文搜索功能
- 分类筛选
- 标签系统

### 4. 文件管理模块
- 附件上传和下载
- 文件类型检查
- 存储空间管理

## 安全考虑

1. **认证安全**: 密码哈希存储，会话管理
2. **授权控制**: 基于角色的访问控制
3. **数据验证**: 输入验证和XSS防护
4. **文件安全**: 文件类型检查和路径安全

## 部署方案

### 开发环境
- SQLite数据库
- 本地文件存储
- 开发服务器

### 生产环境
- PostgreSQL数据库
- 分布式文件存储
- Nginx + Gunicorn

## 监控和日志

- 应用性能监控
- 错误日志记录
- 用户行为分析

## 总结

本系统采用模块化设计，具有良好的可扩展性和维护性。通过合理的架构设计，确保系统的稳定性和安全性。
''',
            'author': admin,
            'category': tech_cat,
            'summary': '企业Wiki系统整体架构设计文档',
            'is_published': True,
            'is_public': True
        },
        {
            'title': '产品需求文档模板',
            'content': '''# 产品需求文档模板

## 文档信息

- **文档版本**: v1.0
- **创建日期**: 2024-01-01
- **作者**: 产品经理
- **状态**: 草案

## 1. 项目背景

### 1.1 项目概述
简要描述项目的背景、目标和意义。

### 1.2 市场分析
- 目标用户群体
- 市场规模和趋势
- 竞品分析

## 2. 产品定位

### 2.1 目标用户
- 用户画像
- 用户需求分析
- 使用场景

### 2.2 产品价值
- 核心价值主张
- 差异化优势
- 商业模式

## 3. 功能需求

### 3.1 核心功能
1. **用户管理**
   - 用户注册和登录
   - 权限管理
   - 个人资料管理

2. **内容管理**
   - 文档创建和编辑
   - 版本控制
   - 分类管理

3. **协作功能**
   - 评论和讨论
   - 实时编辑
   - 通知系统

### 3.2 辅助功能
- 搜索功能
- 文件上传
- 导出功能
- 移动端支持

## 4. 非功能性需求

### 4.1 性能要求
- 页面加载时间 < 3秒
- 支持1000并发用户
- 数据库响应时间 < 100ms

### 4.2 安全要求
- 用户数据加密
- 访问权限控制
- 防SQL注入和XSS攻击

### 4.3 可用性要求
- 系统可用性 > 99.5%
- 数据备份和恢复
- 错误处理和日志

## 5. 技术方案

### 5.1 技术架构
- 前端：React + TypeScript
- 后端：Node.js + Express
- 数据库：MongoDB
- 缓存：Redis

### 5.2 部署方案
- 容器化部署
- 微服务架构
- CI/CD流水线

## 6. 项目计划

### 6.1 里程碑
1. 需求确认：2周
2. 设计阶段：3周
3. 开发阶段：8周
4. 测试阶段：2周
5. 上线部署：1周

### 6.2 资源需求
- 开发人员：4人
- 测试人员：2人
- 运维人员：1人

## 7. 风险评估

### 7.1 技术风险
- 新技术学习成本
- 第三方依赖风险
- 性能优化挑战

### 7.2 业务风险
- 市场接受度
- 竞争对手反应
- 用户需求变化

## 8. 成功指标

### 8.1 用户指标
- 用户注册数量
- 日活跃用户数
- 用户留存率

### 8.2 业务指标
- 功能使用率
- 用户满意度
- 系统稳定性

## 9. 附录

### 9.1 参考资料
- 相关技术文档
- 行业标准
- 竞品分析报告

### 9.2 术语表
- 术语定义和解释
''',
            'author': jiang_mengqi,
            'category': product_cat,
            'summary': '标准的产品需求文档模板，包含完整的产品规划流程',
            'is_published': True,
            'is_public': True
        },
        {
            'title': '项目开发流程规范',
            'content': '''# 项目开发流程规范

## 1. 项目启动阶段

### 1.1 需求分析
- 召开需求评审会议
- 编写需求文档
- 确定项目范围和时间表

### 1.2 技术方案设计
- 架构设计评审
- 技术选型确认
- 开发环境搭建

## 2. 开发阶段

### 2.1 代码规范
- 统一代码风格
- 编写注释和文档
- 代码审查流程

### 2.2 版本控制
- Git工作流程
- 分支管理策略
- 提交信息规范

### 2.3 测试规范
- 单元测试要求
- 集成测试流程
- 用户验收测试

## 3. 部署上线

### 3.1 部署流程
- 环境准备
- 数据迁移
- 功能验证

### 3.2 监控和维护
- 性能监控
- 日志分析
- 问题处理流程

## 4. 项目总结

- 项目复盘会议
- 经验总结
- 流程优化建议
''',
            'author': zhangsan,
            'category': project_cat,
            'summary': '规范化的项目开发流程，确保项目质量和进度',
            'is_published': True,
            'is_public': True
        },
        {
            'title': '周例会会议纪要',
            'content': '''# 技术团队周例会纪要

**会议时间**: 2024年10月25日 14:00-15:00
**会议地点**: 3楼会议室A
**主持人**: 技术总监
**参会人员**: 技术团队全体成员

## 1. 上周工作回顾

### 1.1 完成的工作
- ✅ 完成用户管理模块开发
- ✅ 修复了5个线上bug
- ✅ 优化了数据库查询性能
- ✅ 更新了API文档

### 1.2 遇到的问题
- 数据库性能瓶颈需要优化
- 前端兼容性问题需要解决
- 测试覆盖率有待提高

## 2. 本周工作计划

### 2.1 开发任务
- [ ] 开发文件上传功能
- [ ] 实现实时通知系统
- [ ] 完成移动端适配
- [ ] 优化搜索算法

### 2.2 技术改进
- [ ] 重构代码结构
- [ ] 增加单元测试
- [ ] 完善监控指标
- [ ] 更新部署脚本

## 3. 技术分享

### 3.1 新技术调研
- 微服务架构调研报告
- 容器化部署方案
- 前端框架对比分析

### 3.2 最佳实践分享
- 代码审查要点
- 性能优化技巧
- 安全防护措施

## 4. 问题讨论

### 4.1 技术难点
- 如何处理高并发场景
- 数据库分库分表策略
- 缓存方案选择

### 4.2 解决方案
- 采用消息队列处理异步任务
- 实施读写分离和分表策略
- 使用Redis集群作为缓存

## 5. 下周安排

- 继续推进本周计划任务
- 准备下个迭代的需求评审
- 组织技术培训活动

## 6. 会议总结

本次会议明确了本周的工作重点，解决了几个关键技术问题。团队将继续保持良好的沟通和协作，确保项目按时交付。

**下次会议时间**: 2024年11月1日 14:00
''',
            'author': admin,
            'category': meeting_cat,
            'summary': '技术团队周例会，回顾工作进展并制定下周计划',
            'is_published': True,
            'is_public': False
        },
        {
            'title': 'API接口设计规范',
            'content': '''# API接口设计规范

## 1. 基本原则

### 1.1 RESTful设计
- 使用HTTP动词表示操作：GET、POST、PUT、DELETE
- 使用名词表示资源
- 使用复数形式表示资源集合

### 1.2 URL设计规范
```
GET    /api/v1/users          # 获取用户列表
POST   /api/v1/users          # 创建用户
GET    /api/v1/users/{id}     # 获取单个用户
PUT    /api/v1/users/{id}     # 更新用户
DELETE /api/v1/users/{id}     # 删除用户
```

## 2. 请求规范

### 2.1 请求头
```
Content-Type: application/json
Authorization: Bearer {token}
Accept: application/json
```

### 2.2 请求体格式
```json
{
  "data": {
    "name": "张三",
    "email": "zhangsan@example.com"
  },
  "meta": {
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

## 3. 响应规范

### 3.1 成功响应
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "张三",
    "email": "zhangsan@example.com"
  },
  "meta": {
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "v1"
  }
}
```

### 3.2 错误响应
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "参数验证失败",
    "details": {
      "email": "邮箱格式不正确"
    }
  },
  "meta": {
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

## 4. 状态码规范

- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未授权访问
- `403 Forbidden`: 禁止访问
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误

## 5. 分页规范

### 5.1 请求参数
```
GET /api/v1/users?page=1&per_page=20&sort=created_at&order=desc
```

### 5.2 响应格式
```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 100,
      "pages": 5
    }
  }
}
```

## 6. 版本控制

### 6.1 版本策略
- 使用URL路径版本控制：`/api/v1/`
- 向后兼容原则
- 废弃API的通知机制

### 6.2 版本升级
- 新版本发布前进行充分测试
- 提供版本迁移指南
- 保持旧版本一段时间支持

## 7. 安全规范

### 7.1 认证授权
- 使用JWT令牌认证
- 实现角色权限控制
- API访问频率限制

### 7.2 数据安全
- 敏感数据加密传输
- 输入参数验证
- SQL注入防护

## 8. 文档规范

### 8.1 接口文档
- 使用Swagger/OpenAPI规范
- 提供请求/响应示例
- 包含错误码说明

### 8.2 更新日志
- 记录API变更历史
- 标注破坏性变更
- 提供迁移指南
''',
            'author': jiang_mengqi,
            'category': tech_cat,
            'summary': '完整的API接口设计规范，确保接口的一致性和可维护性',
            'is_published': True,
            'is_public': True
        },
        {
            'title': 'Git工作流程指南',
            'content': '''# Git工作流程指南

## 1. 分支策略

### 1.1 主要分支
- **master**: 生产环境代码
- **develop**: 开发环境代码
- **feature/***: 功能开发分支
- **hotfix/***: 紧急修复分支
- **release/***: 发布准备分支

### 1.2 分支命名规范
```
feature/user-authentication
feature/file-upload
hotfix/login-bug-fix
release/v1.2.0
```

## 2. 工作流程

### 2.1 功能开发流程
1. 从develop分支创建feature分支
2. 在feature分支上进行开发
3. 提交代码并推送到远程仓库
4. 创建Pull Request到develop分支
5. 代码审查通过后合并

### 2.2 紧急修复流程
1. 从master分支创建hotfix分支
2. 修复问题并测试
3. 合并到master和develop分支
4. 创建标签并发布

## 3. 提交规范

### 3.1 提交信息格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

### 3.2 提交类型
- **feat**: 新功能
- **fix**: 修复bug
- **docs**: 文档更新
- **style**: 代码格式调整
- **refactor**: 代码重构
- **test**: 测试相关
- **chore**: 构建或工具相关

### 3.3 提交示例
```
feat(auth): add user registration functionality

- Add registration form validation
- Implement email verification
- Create user profile page

Closes #123
```

## 4. 代码审查

### 4.1 审查要点
- 代码逻辑正确性
- 性能影响评估
- 安全性检查
- 测试覆盖率

### 4.2 审查流程
1. 创建Pull Request
2. 指定审查人员
3. 根据反馈修改代码
4. 审查通过后合并

## 5. 冲突解决

### 5.1 常见冲突类型
- 同一文件的不同修改
- 分支合并冲突
- 依赖版本冲突

### 5.2 解决策略
- 定期同步主分支
- 小步提交，避免大量修改
- 使用图形化工具辅助解决

## 6. 最佳实践

### 6.1 分支管理
- 保持分支简短生命周期
- 及时删除已合并分支
- 使用描述性分支名称

### 6.2 提交管理
- 原子性提交，一次提交一个功能点
- 编写清晰的提交信息
- 避免提交敏感信息

### 6.3 团队协作
- 建立统一的Git配置
- 定期进行代码同步
- 使用Issue跟踪任务

## 7. 工具推荐

### 7.1 Git客户端
- SourceTree
- GitKraken
- VS Code Git插件

### 7.2 辅助工具
- Git Hooks
- CI/CD集成
- 代码质量检查工具
''',
            'author': zhangsan,
            'category': tech_cat,
            'summary': '团队Git工作流程标准化指南，提高协作效率',
            'is_published': True,
            'is_public': True
        }
    ]

    for page_data in pages_data:
        existing_page = Page.query.filter_by(title=page_data['title']).first()
        if not existing_page:
            page = Page(
                title=page_data['title'],
                content=page_data['content'],
                summary=page_data['summary'],
                author_id=page_data['author'].id,
                category_id=page_data['category'].id if page_data['category'] else None,
                is_published=page_data['is_published'],
                is_public=page_data['is_public']
            )

            # 生成slug
            page.generate_slug()

            # 生成HTML内容
            if page.content:
                page.on_changed_content(page, page.content, None, None)

            db.session.add(page)
            print(f"✓ 创建文章: {page_data['title']}")

            # 创建版本
            page.create_version(page_data['author'].id, '初始版本')
        else:
            print(f"✓ 文章已存在: {page_data['title']}")

    db.session.commit()
    print("文章创建完成！")

def main():
    """主函数"""
    print("开始创建测试数据...")

    app = create_app()
    with app.app_context():
        try:
            create_test_users()
            create_test_categories()
            create_test_pages()

            print("\n✅ 所有测试数据创建完成！")
            print("\n用户账号信息：")
            print("- 管理员: admin@jimmyki.com / jG679322")
            print("- 江梦琦: jimmyki@qq.com / jG679322")
            print("- 张三: zhangsan@company.com / password123")
            print("- 李四: lisi@company.com / password123")
            print("- 王五: wangwu@company.com / password123")
            print("- 编辑员: editor@company.com / password123")
            print("- 查看者: viewer@company.com / password123")

        except Exception as e:
            print(f"❌ 创建数据时出错: {e}")
            db.session.rollback()

if __name__ == '__main__':
    main()