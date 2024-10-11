import base64
import logging
import mimetypes
import re
from typing import Optional, Sequence

import requests
from langchain_core.documents.base import Document
from tenacity import retry, stop_after_attempt, wait_exponential

from server.rag.ingestion.model import _ImageMetadata


class DocumentWithImages(Document):
    images: list[_ImageMetadata]


class ExtractImageConvertor:
    """
    Markdown形式のドキュメントから画像情報を抽出してDocumentWithImagesに変換する

    NOTE:
    役割としてはLangChainのDocumentTransformerに近いが、
    型付けを厳密に行うために独自に実装している
    """

    _image_cache: dict[str, _ImageMetadata]
    _logger: logging.Logger

    def __init__(self, logger: Optional[logging.Logger] = None):
        self._image_cache = {}

        if logger is None:
            self._logger = logging.getLogger(__name__)
            self._logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
        else:
            self._logger = logger

    def convert_documents(
        self, documents: Sequence[Document], **kwargs
    ) -> Sequence[DocumentWithImages]:
        return [self._convert_document(doc) for doc in documents]

    def _convert_document(self, doc: Document) -> DocumentWithImages:
        """
        ドキュメント内の画像URLを抽出し、その画像情報を格納したDocumentWithImagesを返す

        Args:
            doc (Document): 画像URLを抽出する対象のドキュメント

        Returns:
            DocumentWithImages: 画像URLを抽出し、その画像情報を格納したDocumentWithImages
        """

        image_urls = self._extract_image_urls(doc.page_content)
        self._logger.debug(f"抽出された画像URL: {image_urls}")

        images = []
        for image_url in image_urls:
            if image_url in self._image_cache:
                self._logger.debug(f"キャッシュから画像情報を取得: {image_url}")
                images.append(self._image_cache[image_url])
                continue

            try:
                self._logger.debug(f"画像の処理を開始します: {image_url}")
                image_base64 = self._get_image_base64(image_url)
                image_mime_type = mimetypes.guess_type(image_url)[0]

                if image_mime_type is None:
                    self._logger.warning(f"画像のMIMEタイプが不明です: {image_url}")
                    continue

                image_metadata = _ImageMetadata(
                    url=image_url,
                    base64=image_base64,
                    mime_type=image_mime_type,
                )
                images.append(image_metadata)
                self._image_cache[image_url] = image_metadata  # キャッシュに追加
            except Exception:
                self._logger.exception(
                    f"画像 {image_url} の処理中にエラーが発生しました"
                )

        transformed_doc = DocumentWithImages(
            page_content=doc.page_content,
            metadata={**doc.metadata},
            images=images,
        )

        return transformed_doc

    def _extract_image_urls(self, text) -> list[str]:
        """
        ドキュメント内の画像URLを抽出する

        Args:
            text (str): ドキュメントの内容

        Returns:
            list[str]: 抽出された画像URLのリスト
        """
        # Markdown形式の画像リンク文字列にマッチする正規表現パターン
        image_link_regex = r"!\[.*?\]\((https://[^)]+?\.(?:png|jpg|jpeg|gif|webp))\)"

        return re.findall(image_link_regex, text)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    def _get_image_base64(self, image_url: str) -> str:
        """
        画像URLを受け取り、その画像のBase64エンコードされた文字列を返す

        Args:
            image_url (str): 画像のURL

        Returns:
            str: Base64エンコードされた画像データ
        """
        try:
            self._logger.debug(f"画像のダウンロードを試みています: {image_url}")
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image_data = response.content
            base64_encoded = base64.b64encode(image_data).decode("utf-8")
            self._logger.debug(f"画像のダウンロードに成功しました: {image_url}")
            return base64_encoded
        except requests.exceptions.ConnectionError as e:
            self._logger.error(f"接続エラーが発生しました: {e}", exc_info=True)
            raise
        except requests.exceptions.Timeout as e:
            self._logger.error(f"タイムアウトが発生しました: {e}", exc_info=True)
            raise
        except requests.exceptions.RequestException as e:
            self._logger.error(
                f"リクエスト中にエラーが発生しました: {e}", exc_info=True
            )
            raise
        except Exception as e:
            self._logger.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)
            raise
