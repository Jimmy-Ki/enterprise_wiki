"""
FastGPT API 客户端
用于与 FastGPT 服务进行对话交互
"""

import requests
import json
import uuid
from typing import Dict, List, Optional, Generator, Any
from flask import current_app
import time


class FastGPTClient:
    """FastGPT API 客户端"""

    def __init__(self, base_url: str = None, api_key: str = None):
        """
        初始化 FastGPT 客户端

        Args:
            base_url: FastGPT 服务的基础URL
            api_key: FastGPT API 密钥
        """
        self.base_url = base_url or current_app.config.get('FASTGPT_BASE_URL', 'http://10.0.0.229:30000/api')
        self.api_key = api_key or current_app.config.get('FASTGPT_API_KEY', 'fastgpt-l2xX4RECkCTUJ453oq2IXG1PbxifKVYMmyEGwdvrZplKXYz1DVv9X5iu5NxSkVkI9')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })

    def chat_completion(self,
                       messages: List[Dict],
                       chat_id: str = None,
                       stream: bool = True,
                       detail: bool = True,
                       variables: Dict = None,
                       response_chat_item_id: str = None) -> Dict:
        """
        发起对话请求

        Args:
            messages: 对话消息列表
            chat_id: 对话ID，用于保持上下文
            stream: 是否使用流式响应
            detail: 是否返回详细信息
            variables: 模块变量
            response_chat_item_id: 响应消息ID

        Returns:
            API响应数据
        """
        if chat_id is None:
            chat_id = str(uuid.uuid4())

        data = {
            "chatId": chat_id,
            "stream": stream,
            "detail": detail,
            "messages": messages
        }

        if variables:
            data["variables"] = variables

        if response_chat_item_id:
            data["responseChatItemId"] = response_chat_item_id

        try:
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=data,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"FastGPT API 请求失败: {str(e)}")
            raise Exception(f"FastGPT API 请求失败: {str(e)}")

    def chat_completion_stream(self,
                              messages: List[Dict],
                              chat_id: str = None,
                              detail: bool = True,
                              variables: Dict = None,
                              response_chat_item_id: str = None) -> Generator[Dict, None, None]:
        """
        流式对话请求

        Args:
            messages: 对话消息列表
            chat_id: 对话ID，用于保持上下文
            detail: 是否返回详细信息
            variables: 模块变量
            response_chat_item_id: 响应消息ID

        Yields:
            流式响应数据
        """
        if chat_id is None:
            chat_id = str(uuid.uuid4())

        data = {
            "chatId": chat_id,
            "stream": True,
            "detail": detail,
            "messages": messages
        }

        if variables:
            data["variables"] = variables

        if response_chat_item_id:
            data["responseChatItemId"] = response_chat_item_id

        try:
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=data,
                stream=True,
                timeout=60
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]  # 移除 'data: ' 前缀
                        if data_str.strip() == '[DONE]':
                            break
                        try:
                            data_json = json.loads(data_str)
                            yield data_json
                        except json.JSONDecodeError:
                            continue

        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"FastGPT 流式API 请求失败: {str(e)}")
            raise Exception(f"FastGPT 流式API 请求失败: {str(e)}")

    def get_chat_histories(self, app_id: str, offset: int = 0, page_size: int = 20) -> Dict:
        """
        获取对话历史记录

        Args:
            app_id: 应用ID
            offset: 偏移量
            page_size: 页面大小

        Returns:
            历史记录数据
        """
        data = {
            "appId": app_id,
            "offset": offset,
            "pageSize": page_size,
            "source": "api"
        }

        try:
            response = self.session.post(
                f"{self.base_url}/core/chat/getHistories",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"获取对话历史失败: {str(e)}")
            raise Exception(f"获取对话历史失败: {str(e)}")

    def get_chat_records(self, app_id: str, chat_id: str, offset: int = 0, page_size: int = 10) -> Dict:
        """
        获取对话记录

        Args:
            app_id: 应用ID
            chat_id: 对话ID
            offset: 偏移量
            page_size: 页面大小

        Returns:
            对话记录数据
        """
        data = {
            "appId": app_id,
            "chatId": chat_id,
            "offset": offset,
            "pageSize": page_size,
            "loadCustomFeedbacks": True
        }

        try:
            response = self.session.post(
                f"{self.base_url}/core/chat/getPaginationRecords",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"获取对话记录失败: {str(e)}")
            raise Exception(f"获取对话记录失败: {str(e)}")

    def update_chat_title(self, app_id: str, chat_id: str, custom_title: str = None, top: bool = False) -> Dict:
        """
        更新对话标题或置顶状态

        Args:
            app_id: 应用ID
            chat_id: 对话ID
            custom_title: 自定义标题
            top: 是否置顶

        Returns:
            更新结果
        """
        data = {
            "appId": app_id,
            "chatId": chat_id
        }

        if custom_title is not None:
            data["customTitle"] = custom_title
        if top is not None:
            data["top"] = top

        try:
            response = self.session.post(
                f"{self.base_url}/core/chat/updateHistory",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"更新对话失败: {str(e)}")
            raise Exception(f"更新对话失败: {str(e)}")

    def delete_chat_history(self, app_id: str, chat_id: str) -> Dict:
        """
        删除对话历史

        Args:
            app_id: 应用ID
            chat_id: 对话ID

        Returns:
            删除结果
        """
        try:
            response = self.session.delete(
                f"{self.base_url}/core/chat/delHistory",
                params={"chatId": chat_id, "appId": app_id},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"删除对话失败: {str(e)}")
            raise Exception(f"删除对话失败: {str(e)}")

    def create_question_guide(self, app_id: str, chat_id: str, custom_prompt: str = None) -> Dict:
        """
        创建猜你想问

        Args:
            app_id: 应用ID
            chat_id: 对话ID
            custom_prompt: 自定义提示词

        Returns:
            猜你想问的问题列表
        """
        data = {
            "appId": app_id,
            "chatId": chat_id,
            "questionGuide": {
                "open": True,
                "model": "GPT-4o-mini",
                "customPrompt": custom_prompt or "你是一个智能助手，请根据用户的问题生成猜你想问。"
            }
        }

        try:
            response = self.session.post(
                f"{self.base_url}/core/ai/agent/v2/createQuestionGuide",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"创建猜你想问失败: {str(e)}")
            raise Exception(f"创建猜你想问失败: {str(e)}")


# 全局 FastGPT 客户端实例
fastgpt_client = None


def get_fastgpt_client() -> FastGPTClient:
    """获取 FastGPT 客户端实例"""
    global fastgpt_client
    if fastgpt_client is None:
        fastgpt_client = FastGPTClient()
    return fastgpt_client


def format_message(role: str, content: str, content_type: str = "text") -> Dict:
    """
    格式化消息

    Args:
        role: 角色 (user/assistant)
        content: 内容
        content_type: 内容类型 (text/image_url/file_url)

    Returns:
        格式化的消息字典
    """
    if content_type == "text":
        return {
            "role": role,
            "content": content
        }
    else:
        return {
            "role": role,
            "content": [
                {
                    "type": content_type,
                    content_type: content
                }
            ]
        }


def parse_stream_response(response_data: Dict) -> Dict[str, Any]:
    """
    解析流式响应数据

    Args:
        response_data: 流式响应数据

    Returns:
        解析后的响应数据
    """
    result = {
        "event": "unknown",
        "content": "",
        "finish_reason": None,
        "quote_list": [],
        "module_responses": [],
        "node_status": None,
        "error": None
    }

    # 处理不同的event类型
    if "choices" in response_data and response_data["choices"]:
        choice = response_data["choices"][0]
        if "delta" in choice:
            result["content"] = choice["delta"].get("content", "")
        if "finish_reason" in choice:
            result["finish_reason"] = choice["finish_reason"]

    # 处理引用列表
    if "responseData" in response_data:
        for item in response_data["responseData"]:
            if "quoteList" in item:
                result["quote_list"].extend(item["quoteList"])

            # 记录模块响应
            result["module_responses"].append({
                "module_name": item.get("moduleName", "Unknown"),
                "module_type": item.get("moduleType", "Unknown"),
                "data": item
            })

    return result