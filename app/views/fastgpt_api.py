"""
FastGPT API 文件库接口实现
实现 FastGPT API 文件库规范的三个接口：
1. 获取文件树
2. 获取单个文件内容
3. 获取文件阅读链接
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required
from app.models.user import User, Permission
from app.models.wiki import Page, Attachment, Category
from app.models.comment import Comment
from app import db
from datetime import datetime
import os
import hashlib
import base64
import re

fastgpt_api = Blueprint('fastgpt_api', __name__, url_prefix='/api/v1/file')

def verify_fastgpt_token(token):
    """
    验证 FastGPT API token
    这里我们使用用户的密码作为 token（根据用户要求）
    """
    if not token:
        return None

    # 遍历所有用户，检查密码是否匹配 token
    users = User.query.all()
    for user in users:
        if user.verify_password(token):
            return user

    return None

def fastgpt_auth_required(f):
    """FastGPT API 认证装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'code': 401,
                'success': False,
                'message': 'Missing or invalid authorization header',
                'data': None
            }), 401

        token = auth_header[7:]  # 移除 'Bearer ' 前缀
        user = verify_fastgpt_token(token)
        if not user:
            return jsonify({
                'code': 401,
                'success': False,
                'message': 'Invalid token',
                'data': None
            }), 401

        # 检查用户是否有权限访问文件库
        if not user.is_active:
            return jsonify({
                'code': 403,
                'success': False,
                'message': 'User account is inactive',
                'data': None
            }), 403

        return f(*args, **kwargs)
    return decorated_function

def get_category_path(category):
    """获取分类的完整路径"""
    path_parts = []
    current = category
    visited_ids = set()

    while current and current.id not in visited_ids:
        path_parts.append(current.name)
        visited_ids.add(current.id)
        if not current.parent:
            break
        current = current.parent

    # 反转路径并组合
    path_parts.reverse()
    return "/".join(path_parts)

def format_file_item(obj, item_type='file'):
    """格式化文件项为 FastGPT 格式"""
    if item_type == 'page':
        # 获取分类路径
        category_path = ""
        if obj.category:
            category_path = get_category_path(obj.category)
            # 将分类路径中的斜杠替换为连字符
            category_path = category_path.replace("/", "-")
            category_path += "-"

        # 生成文件名：分类路径-页面标题.md
        filename = f"{category_path}{obj.title}.md"

        return {
            'id': f'page_{obj.id}',
            'parentId': None,  # 不使用父级结构
            'name': filename,
            'type': 'file',
            'updateTime': obj.updated_at.isoformat() if hasattr(obj, 'updated_at') and obj.updated_at else obj.created_at.isoformat(),
            'createTime': obj.created_at.isoformat() if obj.created_at else datetime.utcnow().isoformat()
        }
    elif item_type == 'attachment':
        return {
            'id': f'attachment_{obj.id}',
            'parentId': None,  # 不使用父级结构
            'name': obj.filename,
            'type': 'file',
            'updateTime': obj.created_at.isoformat() if obj.created_at else datetime.utcnow().isoformat(),
            'createTime': obj.created_at.isoformat() if obj.created_at else datetime.utcnow().isoformat()
        }

@fastgpt_api.route('/list', methods=['POST'])
@fastgpt_auth_required
def list_files():
    """
    获取文件树
    FastGPT API 规范：POST /api/v1/file/list
    """
    try:
        data = request.get_json() or {}
        parent_id = data.get('parentId')
        search_key = data.get('searchKey', '').strip()

        file_list = []

        # 处理 parentId
        category_id = None
        page_id = None

        if parent_id:
            if parent_id.startswith('category_'):
                category_id = int(parent_id[9:])
            elif parent_id.startswith('page_'):
                page_id = int(parent_id[5:])
            elif parent_id == 'null' or parent_id is None:
                category_id = None

        # 如果有页面ID，获取该页面的附件
        if page_id:
            page = Page.query.get(page_id)
            if page:
                # 权限检查
                auth_header = request.headers.get('Authorization', '')
                token = auth_header[7:]
                user = verify_fastgpt_token(token)

                if not page.is_public or (user and not page.can_view(user)):
                    return jsonify({
                        'code': 403,
                        'success': False,
                        'message': 'Access denied',
                        'data': []
                    }), 403

                # 获取页面附件
                attachments = Attachment.query.filter_by(page_id=page_id).all()
                for attachment in attachments:
                    file_list.append(format_file_item(attachment, 'attachment'))
        else:
            # 不返回分类文件夹，只返回页面
            # 获取所有页面（按权限过滤）
            pages_query = Page.query

            if search_key:
                pages_query = pages_query.filter(
                    Page.title.contains(search_key) |
                    Page.content.contains(search_key)
                )

            # 获取公开页面
            pages = pages_query.filter_by(is_public=True).all()

            # 如果用户已认证，也包含用户有权限的私有页面
            auth_header = request.headers.get('Authorization', '')
            token = auth_header[7:]
            user = verify_fastgpt_token(token)

            if user:
                private_pages = Page.query.filter_by(is_public=False).all()
                for page in private_pages:
                    if page.can_view(user):
                        pages.append(page)

            # 添加所有页面到文件列表
            for page in pages:
                try:
                    file_item = format_file_item(page, 'page')
                    file_list.append(file_item)
                except Exception as e:
                    print(f"Error formatting page {page.id}: {e}")
                    continue

        return jsonify({
            'code': 200,
            'success': True,
            'message': '',
            'data': file_list
        })

    except Exception as e:
        current_app.logger.error(f"FastGPT API list_files error: {str(e)}")
        return jsonify({
            'code': 500,
            'success': False,
            'message': 'Internal server error',
            'data': []
        }), 500

@fastgpt_api.route('/content', methods=['GET'])
@fastgpt_auth_required
def get_file_content():
    """
    获取单个文件内容
    FastGPT API 规范：GET /api/v1/file/content?id=xx
    """
    try:
        file_id = request.args.get('id')
        if not file_id:
            return jsonify({
                'code': 400,
                'success': False,
                'message': 'Missing file id parameter',
                'data': None
            }), 400

        # 解析文件ID
        if file_id.startswith('page_'):
            page_id = int(file_id[5:])
            page = Page.query.get(page_id)
            if not page:
                return jsonify({
                    'code': 404,
                    'success': False,
                    'message': 'Page not found',
                    'data': None
                }), 404

            # 权限检查
            auth_header = request.headers.get('Authorization', '')
            token = auth_header[7:]
            user = verify_fastgpt_token(token)

            if not page.is_public or (user and not page.can_view(user)):
                return jsonify({
                    'code': 403,
                    'success': False,
                    'message': 'Access denied',
                    'data': None
                }), 403

            # 清理HTML标签，返回纯文本内容
            import re
            content = re.sub('<[^<]+?>', '', page.content)

            return jsonify({
                'code': 200,
                'success': True,
                'message': '',
                'data': {
                    'title': page.title,
                    'content': content,
                    'previewUrl': None
                }
            })

        elif file_id.startswith('attachment_'):
            attachment_id = int(file_id[11:])
            attachment = Attachment.query.get(attachment_id)
            if not attachment:
                return jsonify({
                    'code': 404,
                    'success': False,
                    'message': 'Attachment not found',
                    'data': None
                }), 404

            # 权限检查
            page = Page.query.get(attachment.page_id)
            if page:
                auth_header = request.headers.get('Authorization', '')
                token = auth_header[7:]
                user = verify_fastgpt_token(token)

                if not page.is_public or (user and not page.can_view(user)):
                    return jsonify({
                        'code': 403,
                        'success': False,
                        'message': 'Access denied',
                        'data': None
                    }), 403

            # 对于附件，提供下载链接
            preview_url = f"/api/v1/file/read?id={file_id}"

            return jsonify({
                'code': 200,
                'success': True,
                'message': '',
                'data': {
                    'title': attachment.filename,
                    'content': None,
                    'previewUrl': preview_url
                }
            })

        else:
            return jsonify({
                'code': 400,
                'success': False,
                'message': 'Invalid file id format',
                'data': None
            }), 400

    except Exception as e:
        current_app.logger.error(f"FastGPT API get_file_content error: {str(e)}")
        return jsonify({
            'code': 500,
            'success': False,
            'message': 'Internal server error',
            'data': None
        }), 500

@fastgpt_api.route('/read', methods=['GET'])
@fastgpt_auth_required
def get_file_read_url():
    """
    获取文件阅读链接
    FastGPT API 规范：GET /api/v1/file/read?id=xx
    """
    try:
        file_id = request.args.get('id')
        if not file_id:
            return jsonify({
                'code': 400,
                'success': False,
                'message': 'Missing file id parameter',
                'data': None
            }), 400

        # 解析文件ID
        if file_id.startswith('page_'):
            page_id = int(file_id[5:])
            page = Page.query.get(page_id)
            if not page:
                return jsonify({
                    'code': 404,
                    'success': False,
                    'message': 'Page not found',
                    'data': None
                }), 404

            # 权限检查
            auth_header = request.headers.get('Authorization', '')
            token = auth_header[7:]
            user = verify_fastgpt_token(token)

            if not page.is_public or (user and not page.can_view(user)):
                return jsonify({
                    'code': 403,
                    'success': False,
                    'message': 'Access denied',
                    'data': None
                }), 403

            # 返回页面访问链接
            url = f"/wiki/{page.id}"

            return jsonify({
                'code': 200,
                'success': True,
                'message': '',
                'data': {
                    'url': url
                }
            })

        elif file_id.startswith('attachment_'):
            attachment_id = int(file_id[11:])
            attachment = Attachment.query.get(attachment_id)
            if not attachment:
                return jsonify({
                    'code': 404,
                    'success': False,
                    'message': 'Attachment not found',
                    'data': None
                }), 404

            # 权限检查
            page = Page.query.get(attachment.page_id)
            if page:
                auth_header = request.headers.get('Authorization', '')
                token = auth_header[7:]
                user = verify_fastgpt_token(token)

                if not page.is_public or (user and not page.can_view(user)):
                    return jsonify({
                        'code': 403,
                        'success': False,
                        'message': 'Access denied',
                        'data': None
                    }), 403

            # 返回附件下载链接
            url = f"/api/download/{attachment.id}"

            return jsonify({
                'code': 200,
                'success': True,
                'message': '',
                'data': {
                    'url': url
                }
            })

        else:
            return jsonify({
                'code': 400,
                'success': False,
                'message': 'Invalid file id format',
                'data': None
            }), 400

    except Exception as e:
        current_app.logger.error(f"FastGPT API get_file_read_url error: {str(e)}")
        return jsonify({
            'code': 500,
            'success': False,
            'message': 'Internal server error',
            'data': None
        }), 500

# 错误处理
@fastgpt_api.errorhandler(404)
def not_found(error):
    return jsonify({
        'code': 404,
        'success': False,
        'message': 'Endpoint not found',
        'data': None
    }), 404

@fastgpt_api.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'code': 405,
        'success': False,
        'message': 'Method not allowed',
        'data': None
    }), 405

@fastgpt_api.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({
        'code': 500,
        'success': False,
        'message': 'Internal server error',
        'data': None
    }), 500