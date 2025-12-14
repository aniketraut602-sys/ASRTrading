import os
import json
import gzip
import shutil
from datetime import datetime
from typing import Any, Dict
from asr_trading.core.logger import logger

class ColdStore:
    """
    Manages 'Cold' storage (S3/File) for raw ticks and audit logs.
    Used for historical replay and compliance audits.
    """
    def __init__(self, base_path="data/cold_store"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    async def store_object(self, bucket: str, key: str, data: Any, compress: bool = True):
        """
        Stores an object. In a real cloud setup, this would use boto3/s3fs.
        Here we emulate buckets with directories.
        """
        try:
            full_dir = os.path.join(self.base_path, bucket)
            os.makedirs(full_dir, exist_ok=True)
            
            file_path = os.path.join(full_dir, key)
            if compress:
                file_path += ".gz"
                
            # Serialize if dict/list
            if isinstance(data, (dict, list)):
                content = json.dumps(data).encode('utf-8')
            elif isinstance(data, str):
                content = data.encode('utf-8')
            else:
                content = data
            
            if compress:
                with gzip.open(file_path, 'wb') as f:
                    f.write(content)
            else:
                with open(file_path, 'wb') as f:
                    f.write(content)
            
            logger.debug(f"ColdStore: Saved {key} to {bucket}")
            return file_path

        except Exception as e:
            logger.error(f"ColdStore Write Failed: {e}")
            raise e

    def get_object_path(self, bucket: str, key: str) -> str:
        return os.path.join(self.base_path, bucket, key)

cold_store = ColdStore()
