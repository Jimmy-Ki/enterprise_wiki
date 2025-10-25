#!/usr/bin/env python3
"""
批量创建随机文章的脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Page, Category
from datetime import datetime, timedelta
import random
import secrets

# 文章标题模板
ARTICLE_TITLES = [
    # 技术类
    "Python开发最佳实践指南",
    "微服务架构设计与实现",
    "Docker容器化部署完全教程",
    "Vue.js前端开发进阶",
    "数据库性能优化技巧",
    "API接口设计规范",
    "代码审查checklist",
    "持续集成CI/CD流程",
    "系统监控与日志管理",
    "安全编码实践指南",

    # 管理类
    "项目管理最佳实践",
    "敏捷开发方法论",
    "团队协作工具选择指南",
    "远程办公管理策略",
    "绩效考核体系设计",
    "知识管理系统建设",
    "客户关系管理CRM实施",
    "供应链优化方案",
    "预算编制与成本控制",
    "风险管理与应对策略",

    # 业务类
    "产品需求文档PRD模板",
    "用户体验设计原则",
    "市场营销策略分析",
    "数据分析方法与工具",
    "商业计划书撰写指南",
    "竞品分析框架",
    "用户调研方法论",
    "内容营销策略",
    "SEO优化实战指南",
    "社交媒体运营技巧",

    # 通用类
    "会议纪要模板大全",
    "工作报告写作技巧",
    "时间管理方法",
    "沟通技巧提升指南",
    "职业发展规划",
    "学习方法论总结",
    "健康工作生活习惯",
    "团队建设活动策划",
    "新员工入职手册",
    "企业文化建设实践"
]

# 文章内容模板
ARTICLE_CONTENTS = {
    "技术": [
        """## 概述

本文介绍了{topic}的核心概念和实现方法。通过详细的代码示例和实践经验，帮助开发者快速掌握相关技能。

### 核心要点

- **基础概念**: 了解{topic}的基本原理和架构设计
- **实践应用**: 通过实际案例学习{topic}的应用场景
- **最佳实践**: 总结业界常用的{topic}开发规范和技巧
- **常见问题**: 解决{topic}开发过程中遇到的典型问题

## 详细内容

### 1. 环境准备

在开始{topic}之前，我们需要准备相应的开发环境：

```bash
# 安装必要的依赖
pip install {package}

# 配置开发环境
export {env_var}=true
```

### 2. 核心实现

{topic}的核心实现包括以下几个关键步骤：

1. **初始化配置**
   - 设置基础参数
   - 配置运行环境
   - 验证系统依赖

2. **核心功能开发**
   - 实现主要业务逻辑
   - 添加错误处理机制
   - 优化性能表现

3. **测试与验证**
   - 单元测试覆盖
   - 集成测试验证
   - 性能测试评估

### 3. 常见问题解决

在{topic}的实施过程中，可能会遇到以下常见问题：

- **配置问题**: 环境配置不正确导致的运行错误
- **兼容性问题**: 不同版本之间的兼容性冲突
- **性能问题**: 大规模数据处理的性能瓶颈

## 总结

{topic}作为现代软件开发的重要组成部分，掌握其核心要点对于提升开发效率和代码质量具有重要意义。通过本文的介绍，相信读者能够对{topic}有更深入的理解，并在实际项目中加以应用。

## 参考资料

- 官方文档：https://docs.example.com/{topic_lower}
- 社区论坛：https://forum.example.com/{topic_lower}
- GitHub仓库：https://github.com/example/{topic_lower}
""",

        """# {topic}完全指南

## 引言

{topic}是当前软件开发领域的重要技术之一。本文将全面介绍{topic}的概念、原理和实践应用。

## 什么是{topic}

{topic}是一种{description}，它具有以下特点：

- ✅ 高性能：优化的执行效率
- ✅ 可扩展：支持水平扩展
- ✅ 易维护：清晰的代码结构
- ✅ 安全性：完善的安全机制

## 应用场景

{topic}主要适用于以下场景：

1. **企业级应用**: 大型企业的业务系统
2. **互联网产品**: 高并发的Web应用
3. **移动应用**: 跨平台的移动解决方案
4. **数据分析**: 大数据处理和分析

## 实施步骤

### 第一步：需求分析

明确业务需求和技术要求，制定详细的实施计划。

### 第二步：技术选型

根据项目特点选择合适的技术栈和工具。

### 第三步：架构设计

设计系统架构，确定各模块的职责和接口。

### 第四步：开发实现

按照设计文档进行编码实现，确保代码质量。

### 第五步：测试部署

进行全面的测试验证，确保系统稳定运行。

## 最佳实践

### 代码规范

```python
def {function_name}():
    \"\"\"函数功能描述\"\"\"
    # 代码实现
    pass
```

### 性能优化

- 使用缓存机制
- 优化数据库查询
- 实现异步处理
- 监控系统性能

## 结论

{topic}为现代软件开发提供了强大的技术支持。通过合理的设计和实施，可以构建高质量、高性能的应用系统。

---

*本文最后更新时间：{update_date}*
"""
    ],

    "管理": [
        """# {topic}管理指南

## 背景

在当今快速变化的商业环境中，{topic}变得越来越重要。有效的{topic}能够帮助组织提高效率，降低成本，增强竞争力。

## 核心概念

### 定义
{topic}是指{description}，它涉及组织管理的各个方面。

### 重要性
- **提升效率**: 通过标准化流程提高工作效率
- **降低风险**: 识别和管理潜在风险
- **增强协作**: 改善团队协作和沟通
- **持续改进**: 建立反馈机制，持续优化

## 实施框架

### 1. 规划阶段
- 设定目标和指标
- 分析现状和差距
- 制定实施计划
- 分配资源和责任

### 2. 执行阶段
- 按计划推进各项工作
- 监控进度和质量
- 及时调整和优化
- 保持沟通和协调

### 3. 评估阶段
- 收集数据和反馈
- 评估效果和影响
- 总结经验教训
- 制定改进措施

## 工具和方法

### 常用工具
- **项目管理工具**: JIRA, Trello, Asana
- **沟通协作工具**: Slack, Microsoft Teams, 钉钉
- **文档管理工具**: Confluence, Notion, 语雀
- **分析报告工具**: Excel, Tableau, PowerBI

### 管理方法
- **PDCA循环**: Plan-Do-Check-Act
- **SMART原则**: 具体的、可衡量的、可达成的、相关的、有时限的
- **SWOT分析**: 优势、劣势、机会、威胁分析
- **5W1H方法**: What, Who, When, Where, Why, How

## 成功案例

### 案例一：{company_name}
通过实施{topic}，该公司在{time_period}内实现了：
- 效率提升{percentage}%
- 成本降低{percentage}%
- 员工满意度提升{percentage}%

### 案例二：{company_name}
采用{topic}后，获得了以下收益：
- 项目交付周期缩短{percentage}%
- 质量事故减少{percentage}%
- 客户满意度达到{percentage}%

## 常见挑战

### 实施难点
1. **变革阻力**: 员工对变化的抵触情绪
2. **资源不足**: 时间、预算、人力限制
3. **技能缺乏**: 相关技能和经验不足
4. **文化障碍**: 组织文化不支持新方法

### 应对策略
- 加强培训和沟通
- 循序渐进推进
- 寻求领导支持
- 建立激励机制

## 总结

{topic}是组织管理的重要工具，需要系统性的规划和执行。通过科学的框架、合适的工具和持续改进，组织可以充分发挥{topic}的价值，实现管理目标。

## 行动建议

1. **评估现状**: 分析当前{topic}的成熟度
2. **制定计划**: 确定实施路线图和时间表
3. **培养能力**: 提升团队相关技能
4. **持续改进**: 建立反馈和优化机制

---

*本文适用于各级管理者和项目团队成员*
"""
    ],

    "业务": [
        """# {topic}业务分析

## 市场概述

随着数字化转型的深入推进，{topic}成为企业发展的关键领域。根据最新市场研究，{topic}市场规模预计在未来五年内将保持{growth_rate}%的年复合增长率。

## 行业趋势

### 主要趋势
1. **数字化加速**: 传统业务向数字化转移
2. **用户体验至上**: 以用户为中心的设计理念
3. **数据驱动决策**: 基于数据分析的业务决策
4. **个性化服务**: 定制化的产品和服务

### 技术驱动
- **人工智能**: AI技术在业务流程中的应用
- **大数据分析**: 深度挖掘用户行为和偏好
- **云计算**: 灵活的IT基础设施支持
- **移动互联网**: 随时随地的业务接入

## 竞争分析

### 市场格局
当前{topic}市场竞争激烈，主要参与者包括：

- **行业领导者**: 具有技术优势和规模效应
- **专业服务商**: 专注细分领域的深度服务
- **新兴创新者**: 采用新技术和新商业模式

### 竞争策略
1. **差异化定位**: 明确目标市场和客户群体
2. **价值主张**: 突出独特价值和服务优势
3. **合作伙伴**: 建立生态合作关系
4. **持续创新**: 保持技术和服务的领先性

## 用户分析

### 目标用户画像
- **人口统计特征**: 年龄、收入、教育背景等
- **行为特征**: 使用习惯、偏好、痛点等
- **需求特征**: 核心需求和期望

### 用户旅程
1. **认知阶段**: 了解{topic}的存在和价值
2. **考虑阶段**: 评估不同的解决方案
3. **决策阶段**: 选择并购买服务
4. **使用阶段**: 实际使用和体验
5. **推荐阶段**: 分享使用经验和推荐

## 商业模式

### 收入模式
- **订阅制**: 按月/年收取订阅费用
- **按使用量**: 根据实际使用量计费
- **一次性购买**: 永久使用权
- **免费增值**: 基础功能免费，高级功能收费

### 成本结构
- **研发成本**: 产品开发和技术投入
- **运营成本**: 服务器、带宽、维护等
- **营销成本**: 市场推广和销售费用
- **人力成本**: 员工薪酬和福利

## 成功要素

### 关键成功因素
1. **产品体验**: 优秀的产品设计和用户体验
2. **技术实力**: 稳定可靠的技术架构
3. **客户服务**: 及时专业的客户支持
4. **品牌建设**: 良好的品牌形象和口碑

### 风险因素
- **技术风险**: 技术更新换代的风险
- **市场风险**: 市场需求变化的风险
- **竞争风险**: 竞争对手的威胁
- **政策风险**: 监管政策变化的风险

## 发展建议

### 短期策略（1年内）
- 完善产品功能，提升用户体验
- 扩大市场份额，获取更多用户
- 优化运营效率，降低成本
- 建立初步的品牌认知

### 中期策略（1-3年）
- 拓展产品线，满足多样化需求
- 深化行业解决方案，提升专业度
- 建立合作伙伴生态
- 扩大国际市场布局

### 长期策略（3-5年）
- 成为行业领导者
- 引领行业标准制定
- 探索新的商业模式
- 实现可持续发展

## 总结

{topic}市场充满机遇和挑战。通过深入的市场分析、清晰的竞争策略、以用户为中心的产品设计，以及科学的商业规划，企业可以在{topic}领域获得成功。

关键是要保持敏锐的市场洞察力，快速响应市场变化，持续创新产品和服务，为用户创造真正的价值。

---

*本文基于{analysis_date}的市场分析数据*
"""
    ]
}

def generate_slug(title):
    """生成文章slug"""
    import re
    # 转换为小写
    slug = title.lower()
    # 移除特殊字符
    slug = re.sub(r'[^\w\s-]', '', slug)
    # 替换空格为连字符
    slug = re.sub(r'[\s_]+', '-', slug)
    # 移除多余的连字符
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug

def generate_article_content(title, category):
    """生成文章内容"""
    import random

    # 选择内容类型
    if category in ["技术", "开发", "编程", "架构"]:
        content_type = "技术"
    elif category in ["管理", "项目", "团队", "流程"]:
        content_type = "管理"
    else:
        content_type = "业务"

    content_templates = ARTICLE_CONTENTS.get(content_type, ARTICLE_CONTENTS["技术"])
    template = random.choice(content_templates)

    # 生成随机数据填充模板
    replacements = {
        "{topic}": title,
        "{topic_lower}": title.lower().replace(" ", "_"),
        "{description}": f"一种现代化的{category}解决方案，旨在提升效率和用户体验",
        "{package}": f"{title.lower().replace(' ', '-')}",
        "{env_var}": f"{title.upper().replace(' ', '_')}_ENABLED",
        "{function_name}": title.lower().replace(" ", "_").replace("-", "_"),
        "{update_date}": datetime.now().strftime("%Y年%m月%d日"),
        "{company_name}": random.choice(["科技公司A", "互联网企业B", "创新公司C", "传统企业D"]),
        "{time_period}": random.choice(["6个月", "1年", "2年", "3年"]),
        "{percentage}": str(random.randint(10, 80)),
        "{growth_rate}": str(random.randint(15, 40) + random.random()),
        "{analysis_date}": datetime.now().strftime("%Y年%m月")
    }

    content = template
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    return content

def create_random_articles(count=20):
    """批量创建随机文章"""
    app = create_app()
    with app.app_context():
        print(f"开始创建 {count} 篇随机文章...")

        # 获取所有用户（作为作者）
        users = User.query.filter_by(is_active=True).all()
        if not users:
            print("错误：数据库中没有用户，请先创建用户")
            return

        # 获取或创建分类
        categories = Category.query.all()
        if not categories:
            # 创建默认分类
            default_categories = [
                {"name": "技术文档", "description": "技术相关的文档和教程"},
                {"name": "项目管理", "description": "项目管理方法和工具"},
                {"name": "业务流程", "description": "业务流程和规范"},
                {"name": "产品设计", "description": "产品设计相关文档"},
                {"name": "市场分析", "description": "市场研究和分析报告"},
                {"name": "用户指南", "description": "用户使用指南和手册"}
            ]

            for cat_data in default_categories:
                category = Category(
                    name=cat_data["name"],
                    description=cat_data["description"],
                    created_by=users[0].id,
                    is_public=True
                )
                db.session.add(category)

            db.session.commit()
            categories = Category.query.all()

        created_articles = []

        for i in range(count):
            try:
                # 随机选择标题（如果不够用，生成新的）
                if i < len(ARTICLE_TITLES):
                    title = ARTICLE_TITLES[i]
                else:
                    # 生成新的标题
                    prefixes = ["深入理解", "掌握", "实战指南", "最佳实践", "完全手册"]
                    topics = ["系统架构", "开发流程", "产品设计", "项目管理", "团队协作", "业务分析"]
                    title = f"{random.choice(prefixes)}{random.choice(topics)}"

                # 检查标题是否已存在
                existing_page = Page.query.filter_by(title=title).first()
                if existing_page:
                    title = f"{title} - 补充版"

                # 生成slug
                slug = generate_slug(title)

                # 检查slug是否已存在
                existing_slug = Page.query.filter_by(slug=slug).first()
                if existing_slug:
                    slug = f"{slug}-{random.randint(1, 999)}"

                # 随机选择分类
                category = random.choice(categories)

                # 随机选择作者
                author = random.choice(users)

                # 生成文章内容
                content = generate_article_content(title, category.name)

                # 随机设置文章状态
                is_published = random.random() > 0.2  # 80% 已发布

                # 随机设置创建时间（过去60天内）
                days_ago = random.randint(0, 60)
                created_at = datetime.utcnow() - timedelta(days=days_ago)

                # 随机设置更新时间
                if random.random() > 0.5:  # 50%的文章有更新
                    update_days_ago = random.randint(0, days_ago)
                    updated_at = datetime.utcnow() - timedelta(days=update_days_ago)
                else:
                    updated_at = created_at

                # 创建文章
                page = Page(
                    title=title,
                    slug=slug,
                    content=content,
                    author_id=author.id,
                    category_id=category.id,
                    is_published=is_published,
                    created_at=created_at,
                    updated_at=updated_at,
                    published_at=created_at if is_published else None
                )

                db.session.add(page)
                created_articles.append({
                    'title': title,
                    'slug': slug,
                    'author': author.username,
                    'category': category.name,
                    'published': is_published,
                    'created_at': created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_at': updated_at.strftime('%Y-%m-%d %H:%M:%S')
                })

                print(f"创建文章 {i+1}/{count}: {title} - {author.username}")

            except Exception as e:
                print(f"创建文章 {i+1} 失败: {str(e)}")
                db.session.rollback()
                continue

        try:
            db.session.commit()
            print(f"\n✅ 成功创建 {len(created_articles)} 篇文章！")

            # 显示统计信息
            published_count = sum(1 for article in created_articles if article['published'])
            draft_count = len(created_articles) - published_count

            category_stats = {}
            author_stats = {}

            for article in created_articles:
                cat = article['category']
                author = article['author']
                category_stats[cat] = category_stats.get(cat, 0) + 1
                author_stats[author] = author_stats.get(author, 0) + 1

            print(f"\n📊 文章统计:")
            print(f"总文章数: {len(created_articles)}")
            print(f"已发布: {published_count} ({published_count/len(created_articles)*100:.1f}%)")
            print(f"草稿: {draft_count} ({draft_count/len(created_articles)*100:.1f}%)")

            print(f"\n📋 分类分布:")
            for category, count in sorted(category_stats.items()):
                percentage = count/len(created_articles)*100
                print(f"  {category}: {count} ({percentage:.1f}%)")

            print(f"\n👥 作者分布 (显示前5名):")
            sorted_authors = sorted(author_stats.items(), key=lambda x: x[1], reverse=True)[:5]
            for author, count in sorted_authors:
                percentage = count/len(created_articles)*100
                print(f"  {author}: {count} ({percentage:.1f}%)")

            # 保存文章信息到文件
            with open('created_articles.txt', 'w', encoding='utf-8') as f:
                f.write("批量创建的文章信息\n")
                f.write("=" * 50 + "\n")
                f.write(f"创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总文章数: {len(created_articles)}\n\n")

                for i, article in enumerate(created_articles, 1):
                    f.write(f"文章 {i}:\n")
                    f.write(f"  标题: {article['title']}\n")
                    f.write(f"  Slug: {article['slug']}\n")
                    f.write(f"  作者: {article['author']}\n")
                    f.write(f"  分类: {article['category']}\n")
                    f.write(f"  状态: {'已发布' if article['published'] else '草稿'}\n")
                    f.write(f"  创建时间: {article['created_at']}\n")
                    f.write(f"  更新时间: {article['updated_at']}\n")
                    f.write(f"  访问地址: http://127.0.0.1:5004/wiki/{article['slug']}\n")
                    f.write("-" * 30 + "\n")

            print(f"\n💾 文章信息已保存到 created_articles.txt 文件")

        except Exception as e:
            print(f"❌ 保存到数据库失败: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    from datetime import timedelta

    # 检查是否提供了文章数量参数
    count = 20
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print("错误：文章数量必须是整数")
            sys.exit(1)

    create_random_articles(count)