from typing import Literal, Optional, Union

from pydantic import BaseModel


class _WebPageMetadata(BaseModel):
    source: str
    content_type: str
    title: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None


class _ImageMetadata(BaseModel, frozen=True):
    url: str
    mime_type: str
    base64: str


class TextDocumentMetadata(BaseModel):
    url: str
    title: str
    modality: Literal["text"] = "text"


class ImageDocumentMetadata(BaseModel):
    url: str
    title: str
    modality: Literal["image"] = "image"

    # NOTE:
    # Pineconeにメタデータとして格納可能な型は以下のとおりであるため、ディクショナリ型のフィールドを持てないことに注意
    # ref: https://docs.pinecone.io/guides/data/filter-with-metadata#supported-metadata-types
    # - string
    # - number
    # - boolean
    # - string[]

    mime_type: str
    base64: str


DocumentMetadata = Union[TextDocumentMetadata, ImageDocumentMetadata]


class DocumentMetadataFactory:
    @staticmethod
    def from_web_page(metadata: dict[str, str]) -> TextDocumentMetadata:
        parsed_metadata = _WebPageMetadata.model_validate(metadata)
        return TextDocumentMetadata(
            url=parsed_metadata.source,
            title=parsed_metadata.title or "",
        )

    @staticmethod
    def from_image(metadata: dict[str, str]) -> ImageDocumentMetadata:
        parsed_metadata = _ImageMetadata.model_validate(metadata)
        return ImageDocumentMetadata(
            url=parsed_metadata.url,
            title="画像",
            mime_type=parsed_metadata.mime_type,
            base64=parsed_metadata.base64,
        )
