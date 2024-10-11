import json
from typing import Iterator, List, Optional, Sequence, Tuple

from langchain_core.documents import Document
from langchain_core.stores import BaseStore


class S3Store(BaseStore[str, Document]):
    """AWS S3バケットを使用したBaseStore"""

    def __init__(self, bucket_name: str, prefix: str = ""):
        """
        S3Storeを初期化します。

        Args:
            bucket_name (str): S3バケットの名前
            prefix (str): オプションのキープレフィックス
        """
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3ライブラリがインストールされていません。"
                "boto3 をインストールしてください。"
            )

        self._s3 = boto3.client("s3")
        self._bucket_name = bucket_name
        self._prefix = prefix

    def _full_key(self, key: str) -> str:
        """プレフィックス付きの完全なキーを返します"""
        return f"{self._prefix}{key}"

    def mget(self, keys: Sequence[str]) -> List[Optional[Document]]:
        """指定されたキーに関連付けられた値を取得します"""
        results: List[Optional[Document]] = []
        for key in keys:
            try:
                response = self._s3.get_object(
                    Bucket=self._bucket_name, Key=self._full_key(key)
                )
                json_data = json.loads(response["Body"].read().decode("utf-8"))
                results.append(Document(**json_data))
            except self._s3.exceptions.NoSuchKey:
                results.append(None)
        return results

    def mset(self, key_value_pairs: Sequence[Tuple[str, Document]]) -> None:
        """指定されたキーと値のペアを設定します"""
        for key, doc in key_value_pairs:
            json_data = doc.json()
            self._s3.put_object(
                Bucket=self._bucket_name,
                Key=self._full_key(key),
                Body=json_data.encode("utf-8"),
            )

    def mdelete(self, keys: Sequence[str]) -> None:
        """指定されたキーを削除します"""

        # 削除対象が空の場合、以下のエラーが発生するため、空の場合は何もしない
        # botocore.exceptions.ClientError: An error occurred (MalformedXML) when calling the DeleteObjects operation: The XML you provided was not well-formed or did not validate against our published schema
        if len(keys) == 0:
            return

        objects: Sequence = [{"Key": self._full_key(key)} for key in keys]
        self._s3.delete_objects(Bucket=self._bucket_name, Delete={"Objects": objects})

    def yield_keys(self, *, prefix: Optional[str] = None) -> Iterator[str]:
        """指定されたプレフィックスに一致するキーのイテレータを取得します"""
        full_prefix = self._full_key(prefix or "")
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket_name, Prefix=full_prefix):
            for obj in page.get("Contents", []):
                if "Key" not in obj:
                    continue

                yield obj["Key"][
                    len(self._prefix) :
                ]  # プレフィックスを除去して元のキーを返す
