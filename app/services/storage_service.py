"""
存储服务抽象层
支持本地存储、S3存储（Cloudflare、MinIO等）
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid


class StorageBackend(ABC):
    """存储后端抽象基类"""

    @abstractmethod
    def upload_file(self, file_data: BinaryIO, filename: str,
                   content_type: str, folder: str = "") -> Dict[str, Any]:
        """
        上传文件

        Args:
            file_data: 文件数据流
            filename: 文件名
            content_type: MIME类型
            folder: 存储文件夹

        Returns:
            Dict包含文件信息: {
                'success': bool,
                'filename': str,
                'url': str,
                'file_path': str,
                'file_size': int,
                'message': str (可选)
            }
        """
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """
        删除文件

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否删除成功
        """
        pass

    @abstractmethod
    def get_file_url(self, file_path: str) -> str:
        """
        获取文件访问URL

        Args:
            file_path: 文件路径

        Returns:
            str: 文件URL
        """
        pass


class LocalStorageBackend(StorageBackend):
    """本地存储后端"""

    def __init__(self, upload_folder: str, base_url: str = None):
        self.upload_folder = upload_folder
        self.base_url = base_url or "/static/uploads"

    def upload_file(self, file_data: BinaryIO, filename: str,
                   content_type: str, folder: str = "") -> Dict[str, Any]:
        try:
            # 安全文件名处理
            safe_filename = secure_filename(filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{safe_filename}"

            # 构建存储路径
            if folder:
                upload_path = os.path.join(self.upload_folder, folder, unique_filename)
            else:
                upload_path = os.path.join(self.upload_folder, unique_filename)

            # 确保目录存在
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)

            # 保存文件
            file_data.seek(0)  # 重置文件指针
            with open(upload_path, 'wb') as f:
                f.write(file_data.read())

            # 获取文件大小
            file_size = os.path.getsize(upload_path)

            # 生成相对路径
            if folder:
                relative_path = f"{folder}/{unique_filename}"
            else:
                relative_path = unique_filename

            # 生成URL
            url = f"{self.base_url}/{relative_path}".replace("//", "/")

            return {
                'success': True,
                'filename': unique_filename,
                'original_filename': safe_filename,
                'url': url,
                'file_path': upload_path,
                'relative_path': relative_path,
                'file_size': file_size
            }

        except Exception as e:
            return {
                'success': False,
                'message': f"本地存储失败: {str(e)}"
            }

    def delete_file(self, file_path: str) -> bool:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False

    def get_file_url(self, file_path: str) -> str:
        # 本地存储需要将绝对路径转换为相对路径
        if file_path.startswith(self.upload_folder):
            relative_path = file_path[len(self.upload_folder):].lstrip('/')
            return f"{self.base_url}/{relative_path}".replace("//", "/")
        return file_path


class S3StorageBackend(StorageBackend):
    """S3兼容存储后端（支持AWS S3、Cloudflare R2、MinIO）"""

    def __init__(self, endpoint_url: str, access_key: str, secret_key: str,
                 bucket_name: str, region: str = None, cdn_url: str = None):
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.region = region
        self.cdn_url = cdn_url

        # 延迟导入boto3，只有在使用S3时才需要
        try:
            import boto3
            from botocore.exceptions import ClientError

            self.boto3 = boto3
            self.ClientError = ClientError

            # 创建S3客户端
            self.s3_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
        except ImportError:
            raise ImportError("请安装boto3库以支持S3存储: pip install boto3")

    def upload_file(self, file_data: BinaryIO, filename: str,
                   content_type: str, folder: str = "") -> Dict[str, Any]:
        try:
            # 安全文件名处理
            safe_filename = secure_filename(filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{safe_filename}"

            # 构建S3对象键
            if folder:
                object_key = f"{folder}/{unique_filename}"
            else:
                object_key = unique_filename

            # 获取文件大小
            file_data.seek(0, 2)  # 移动到文件末尾
            file_size = file_data.tell()
            file_data.seek(0)  # 重置到文件开头

            # 上传到S3
            upload_args = {
                'ContentType': content_type
            }

            # Cloudflare R2不支持ACL参数
            if 'cloudflare' not in self.endpoint_url.lower():
                upload_args['ACL'] = 'public-read'

            self.s3_client.upload_fileobj(
                file_data,
                self.bucket_name,
                object_key,
                ExtraArgs=upload_args
            )

            # 生成文件URL
            if self.cdn_url:
                url = f"{self.cdn_url.rstrip('/')}/{object_key}"
            else:
                # 根据不同的S3服务生成URL
                if 'cloudflare' in self.endpoint_url.lower():
                    url = f"{self.endpoint_url}/{self.bucket_name}/{object_key}"
                elif 'minio' in self.endpoint_url.lower():
                    url = f"{self.endpoint_url}/{self.bucket_name}/{object_key}"
                else:
                    # AWS S3
                    if self.region and self.region != 'us-east-1':
                        url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_key}"
                    else:
                        url = f"https://{self.bucket_name}.s3.amazonaws.com/{object_key}"

            # 文件大小已在上传前获取

            return {
                'success': True,
                'filename': unique_filename,
                'original_filename': safe_filename,
                'url': url,
                'file_path': object_key,
                'relative_path': object_key,
                'file_size': file_size
            }

        except Exception as e:
            return {
                'success': False,
                'message': f"S3存储失败: {str(e)}"
            }

    def delete_file(self, file_path: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except Exception:
            return False

    def get_file_url(self, file_path: str) -> str:
        if self.cdn_url:
            return f"{self.cdn_url.rstrip('/')}/{file_path}"
        elif 'cloudflare' in self.endpoint_url.lower():
            return f"{self.endpoint_url}/{self.bucket_name}/{file_path}"
        elif 'minio' in self.endpoint_url.lower():
            return f"{self.endpoint_url}/{self.bucket_name}/{file_path}"
        else:
            # AWS S3
            if self.region and self.region != 'us-east-1':
                return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_path}"
            else:
                return f"https://{self.bucket_name}.s3.amazonaws.com/{file_path}"


class StorageService:
    """存储服务统一接口"""

    def __init__(self, backend: StorageBackend):
        self.backend = backend

    def upload_file(self, file_data: BinaryIO, filename: str,
                   content_type: str, folder: str = "") -> Dict[str, Any]:
        """上传文件"""
        return self.backend.upload_file(file_data, filename, content_type, folder)

    def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        return self.backend.delete_file(file_path)

    def get_file_url(self, file_path: str) -> str:
        """获取文件URL"""
        return self.backend.get_file_url(file_path)


def create_storage_service(storage_config: Dict[str, Any]) -> StorageService:
    """
    根据配置创建存储服务

    Args:
        storage_config: 存储配置字典

    Returns:
        StorageService: 存储服务实例
    """
    storage_type = storage_config.get('type', 'local').lower()

    if storage_type == 'local':
        return StorageService(LocalStorageBackend(
            upload_folder=storage_config.get('upload_folder', 'app/static/uploads'),
            base_url=storage_config.get('base_url')
        ))
    elif storage_type == 's3':
        return StorageService(S3StorageBackend(
            endpoint_url=storage_config['endpoint_url'],
            access_key=storage_config['access_key'],
            secret_key=storage_config['secret_key'],
            bucket_name=storage_config['bucket_name'],
            region=storage_config.get('region'),
            cdn_url=storage_config.get('cdn_url')
        ))
    else:
        raise ValueError(f"不支持的存储类型: {storage_type}")