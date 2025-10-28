"""S3分享功能路由"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from app import db
from app.models import S3Share
from app.services.storage_service import create_storage_service
import os
import json

share = Blueprint('share', __name__)


@share.route('/')
@login_required
def index():
    """S3分享主页面"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    shares = S3Share.query.filter_by(uploader_id=current_user.id)\
                          .order_by(S3Share.created_at.desc())\
                          .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('share/index.html', shares=shares.items)


@share.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """上传文件到S3并创建分享"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有选择文件'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '文件名为空'})

    # 检查文件大小 (100MB限制)
    if hasattr(file, 'content_length') and file.content_length > 100 * 1024 * 1024:
        return jsonify({'success': False, 'message': '文件大小超过100MB限制'})

    try:
        # 获取S3存储服务
        storage_config = current_app.config.get('STORAGE_CONFIG')
        if not storage_config or storage_config.get('type', '').lower() != 's3':
            return jsonify({'success': False, 'message': 'S3存储未配置'})

        storage_service = create_storage_service(storage_config)

        # 获取文件信息
        original_filename = secure_filename(file.filename)
        file_extension = os.path.splitext(original_filename)[1].lower().lstrip('.')
        file_type = file.content_type or 'application/octet-stream'

        # 上传到S3（使用shares文件夹）
        upload_result = storage_service.upload_file(
            file_data=file,
            filename=original_filename,
            content_type=file_type,
            folder='shares'
        )

        if not upload_result['success']:
            return jsonify({'success': False, 'message': upload_result.get('message', '上传失败')})

        # 创建分享记录
        s3_share = S3Share(
            original_filename=original_filename,
            file_path=upload_result['file_path'],
            file_size=upload_result['file_size'],
            file_type=file_type,
            file_extension=file_extension,
            s3_url=upload_result['url'],
            public_url=upload_result['url'],  # S3直接URL作为公开URL
            uploader_id=current_user.id,
            is_public=True,
            expires_at=datetime.utcnow() + timedelta(days=30)  # 默认30天过期
        )

        # 生成分享代码和令牌
        s3_share.generate_share_codes()

        db.session.add(s3_share)
        db.session.commit()

        current_app.logger.info(f"S3 Share: User {current_user.id} uploaded file {original_filename}")

        return jsonify({
            'success': True,
            'share_id': s3_share.id,
            'share_code': s3_share.share_code,
            'share_url': s3_share.get_share_url(),
            's3_url': s3_share.s3_url,
            'original_filename': s3_share.original_filename,
            'file_size': s3_share.file_size,
            'file_type': s3_share.file_type,
            'message': '文件上传成功'
        })

    except Exception as e:
        current_app.logger.error(f"S3 Share upload error: {str(e)}")
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'})


@share.route('/share/<share_code>')
def view_share(share_code):
    """查看分享页面"""
    share = S3Share.find_by_share_code(share_code)

    if not share:
        return render_template('share/not_found.html'), 404

    if not share.can_access:
        return render_template('share/expired.html'), 410

    # 增加访问计数
    share.increment_download_count()

    return render_template('share/view.html', share=share)


@share.route('/api/share/<int:share_id>', methods=['GET'])
@login_required
def get_share(share_id):
    """获取分享详情API"""
    share = S3Share.query.filter_by(id=share_id, uploader_id=current_user.id).first()

    if not share:
        return jsonify({'success': False, 'message': '分享不存在'}), 404

    return jsonify({
        'success': True,
        'share': share.to_dict()
    })


@share.route('/api/share/<int:share_id>', methods=['PUT'])
@login_required
def update_share(share_id):
    """更新分享设置API"""
    share = S3Share.query.filter_by(id=share_id, uploader_id=current_user.id).first()

    if not share:
        return jsonify({'success': False, 'message': '分享不存在'}), 404

    data = request.get_json()

    try:
        # 更新过期时间
        if 'expires_at' in data:
            if data['expires_at']:
                share.expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
            else:
                share.expires_at = None

        # 更新下载限制
        if 'max_downloads' in data:
            share.max_downloads = data['max_downloads'] if data['max_downloads'] > 0 else None

        # 更新状态
        if 'is_active' in data:
            share.is_active = data['is_active']

        if 'is_public' in data:
            share.is_public = data['is_public']

        share.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '分享设置已更新',
            'share': share.to_dict()
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'}), 400


@share.route('/api/share/<int:share_id>', methods=['DELETE'])
@login_required
def delete_share(share_id):
    """删除分享API"""
    share = S3Share.query.filter_by(id=share_id, uploader_id=current_user.id).first()

    if not share:
        return jsonify({'success': False, 'message': '分享不存在'}), 404

    try:
        # 从S3删除文件
        storage_config = current_app.config.get('STORAGE_CONFIG')
        if storage_config and storage_config.get('type', '').lower() == 's3':
            storage_service = create_storage_service(storage_config)
            storage_service.delete_file(share.file_path)

        # 删除数据库记录
        db.session.delete(share)
        db.session.commit()

        current_app.logger.info(f"S3 Share: User {current_user.id} deleted share {share_id}")

        return jsonify({
            'success': True,
            'message': '分享已删除'
        })

    except Exception as e:
        current_app.logger.error(f"S3 Share delete error: {str(e)}")
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


@share.route('/api/s3/upload', methods=['POST'])
@login_required
def api_upload_s3():
    """S3文件上传API"""
    return upload_file()


@share.route('/api/s3/image-upload', methods=['POST'])
@login_required
def api_upload_image():
    """富文本编辑器图片上传API"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有选择文件'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '文件名为空'})

    # 检查是否为图片文件
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
    if file.content_type not in allowed_types:
        return jsonify({'success': False, 'message': '只支持图片文件'})

    try:
        # 获取S3存储服务
        storage_config = current_app.config.get('STORAGE_CONFIG')
        if not storage_config or storage_config.get('type', '').lower() != 's3':
            return jsonify({'success': False, 'message': 'S3存储未配置'})

        storage_service = create_storage_service(storage_config)

        # 获取文件信息
        original_filename = secure_filename(file.filename)
        file_extension = os.path.splitext(original_filename)[1].lower().lstrip('.')
        file_type = file.content_type

        # 上传到S3（使用images文件夹）
        upload_result = storage_service.upload_file(
            file_data=file,
            filename=original_filename,
            content_type=file_type,
            folder='images'
        )

        if not upload_result['success']:
            return jsonify({'success': False, 'message': upload_result.get('message', '上传失败')})

        current_app.logger.info(f"S3 Image Upload: User {current_user.id} uploaded image {original_filename}")

        return jsonify({
            'success': True,
            'url': upload_result['url'],
            'filename': upload_result['filename'],
            'original_filename': original_filename,
            'file_size': upload_result['file_size'],
            'message': '图片上传成功'
        })

    except Exception as e:
        current_app.logger.error(f"S3 Image upload error: {str(e)}")
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'})


@share.route('/my-shares')
@login_required
def my_shares():
    """我的分享页面"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    shares = S3Share.query.filter_by(uploader_id=current_user.id)\
                          .order_by(S3Share.created_at.desc())\
                          .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('share/my_shares.html', shares=shares)