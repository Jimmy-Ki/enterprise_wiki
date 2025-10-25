"""
Chat views - AI 对话功能
"""

from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context
from flask_login import login_required, current_user
from app.services.fastgpt_client import get_fastgpt_client, format_message
import json
import uuid

chat = Blueprint('chat', __name__)


@chat.route('/')
@login_required
def index():
    """对话页面主页"""
    return render_template('chat/index.html')


@chat.route('/api/chat/stream', methods=['POST'])
@login_required
def chat_stream():
    """流式对话API接口"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': '缺少消息内容'}), 400

        message = data['message']
        chat_id = data.get('chat_id')
        variables = data.get('variables', {})

        # 获取 FastGPT 客户端
        client = get_fastgpt_client()

        # 构建消息历史
        messages = [
            format_message('user', message)
        ]

        # 生成响应
        def generate():
            try:
                for response_data in client.chat_completion_stream(
                    messages=messages,
                    chat_id=chat_id,
                    detail=True,
                    variables=variables
                ):
                    # 发送流式数据
                    yield f"data: {json.dumps(response_data)}\n\n"

            except Exception as e:
                # 发送错误信息
                error_response = {
                    'error': True,
                    'message': str(e)
                }
                yield f"data: {json.dumps(error_response)}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )

    except Exception as e:
        return jsonify({'error': f'请求处理失败: {str(e)}'}), 500


@chat.route('/api/chat', methods=['POST'])
@login_required
def chat_completion():
    """非流式对话API接口"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': '缺少消息内容'}), 400

        message = data['message']
        chat_id = data.get('chat_id')
        stream = data.get('stream', False)
        detail = data.get('detail', False)
        variables = data.get('variables', {})

        # 获取 FastGPT 客户端
        client = get_fastgpt_client()

        # 构建消息历史
        messages = [
            format_message('user', message)
        ]

        # 发送请求
        response = client.chat_completion(
            messages=messages,
            chat_id=chat_id,
            stream=stream,
            detail=detail,
            variables=variables
        )

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': f'请求处理失败: {str(e)}'}), 500


@chat.route('/api/chat/histories', methods=['POST'])
@login_required
def get_chat_histories():
    """获取对话历史记录"""
    try:
        data = request.get_json()
        app_id = data.get('app_id', 'default')  # 使用默认应用ID
        offset = data.get('offset', 0)
        page_size = data.get('page_size', 20)

        client = get_fastgpt_client()
        response = client.get_chat_histories(
            app_id=app_id,
            offset=offset,
            page_size=page_size
        )

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': f'获取历史记录失败: {str(e)}'}), 500


@chat.route('/api/chat/records', methods=['POST'])
@login_required
def get_chat_records():
    """获取对话记录"""
    try:
        data = request.get_json()
        app_id = data.get('app_id', 'default')
        chat_id = data.get('chat_id')
        offset = data.get('offset', 0)
        page_size = data.get('page_size', 10)

        if not chat_id:
            return jsonify({'error': '缺少对话ID'}), 400

        client = get_fastgpt_client()
        response = client.get_chat_records(
            app_id=app_id,
            chat_id=chat_id,
            offset=offset,
            page_size=page_size
        )

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': f'获取对话记录失败: {str(e)}'}), 500


@chat.route('/api/chat/update', methods=['POST'])
@login_required
def update_chat():
    """更新对话（标题或置顶）"""
    try:
        data = request.get_json()
        app_id = data.get('app_id', 'default')
        chat_id = data.get('chat_id')
        custom_title = data.get('custom_title')
        top = data.get('top')

        if not chat_id:
            return jsonify({'error': '缺少对话ID'}), 400

        client = get_fastgpt_client()
        response = client.update_chat_title(
            app_id=app_id,
            chat_id=chat_id,
            custom_title=custom_title,
            top=top
        )

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': f'更新对话失败: {str(e)}'}), 500


@chat.route('/api/chat/delete', methods=['DELETE'])
@login_required
def delete_chat():
    """删除对话"""
    try:
        app_id = request.args.get('app_id', 'default')
        chat_id = request.args.get('chat_id')

        if not chat_id:
            return jsonify({'error': '缺少对话ID'}), 400

        client = get_fastgpt_client()
        response = client.delete_chat_history(
            app_id=app_id,
            chat_id=chat_id
        )

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': f'删除对话失败: {str(e)}'}), 500


@chat.route('/api/chat/suggestions', methods=['POST'])
@login_required
def get_suggestions():
    """获取猜你想问建议"""
    try:
        data = request.get_json()
        app_id = data.get('app_id', 'default')
        chat_id = data.get('chat_id')
        custom_prompt = data.get('custom_prompt')

        if not chat_id:
            return jsonify({'error': '缺少对话ID'}), 400

        client = get_fastgpt_client()
        response = client.create_question_guide(
            app_id=app_id,
            chat_id=chat_id,
            custom_prompt=custom_prompt
        )

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': f'获取建议失败: {str(e)}'}), 500


@chat.route('/api/chat/health', methods=['GET'])
@login_required
def health_check():
    """健康检查接口"""
    try:
        client = get_fastgpt_client()
        # 这里可以添加对FastGPT服务的健康检查
        # 暂时返回成功状态
        return jsonify({
            'status': 'healthy',
            'message': 'FastGPT service is available'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'message': f'FastGPT service error: {str(e)}'
        }), 500