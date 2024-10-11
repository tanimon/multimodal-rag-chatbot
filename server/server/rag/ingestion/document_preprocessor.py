from typing import Sequence

from langchain_community.document_loaders import (
    MergedDataLoader,
    RecursiveUrlLoader,
)
from langchain_community.document_transformers import (
    MarkdownifyTransformer,
)
from langchain_core.documents.base import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from server.rag.ingestion.extract_image_converter import ExtractImageConvertor
from server.rag.ingestion.image_describer import describe_images
from server.rag.ingestion.model import DocumentMetadataFactory, _ImageMetadata
from server.rag.model import MetadataTypedDocument


class DocumentPreprocessor:
    _document_loader: MergedDataLoader
    _text_splitter: RecursiveCharacterTextSplitter

    def __init__(self, crawling_root_urls: list[str]):
        recursive_url_loaders = [
            RecursiveUrlLoader(
                url=url,
                max_depth=5,
                prevent_outside=True,
            )
            for url in crawling_root_urls
        ]
        self._document_loader = MergedDataLoader(
            loaders=recursive_url_loaders,
        )

        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )

    def preprocess(self) -> list[Document]:
        html_docs = self._document_loader.load()

        transformer = MarkdownifyTransformer()
        markdown_docs = transformer.transform_documents(html_docs)

        image_docs = self._extract_image_descriptions(markdown_docs)

        markdown_docs_with_converted_metadata = [
            doc.model_copy(
                update={
                    "metadata": DocumentMetadataFactory.from_web_page(
                        doc.metadata
                    ).model_dump()
                }
            )
            for doc in markdown_docs
        ]
        image_docs_with_converted_metadata = [
            Document(
                page_content=doc.page_content,
                metadata=DocumentMetadataFactory.from_image(
                    doc.metadata.model_dump()
                ).model_dump(),  # TODO: Pydanticモデルとdictの変換が冗長なのを解消する
            )
            for doc in image_docs
        ]

        all_docs = (
            markdown_docs_with_converted_metadata + image_docs_with_converted_metadata
        )

        splitted_docs = self._text_splitter.split_documents(all_docs)

        return splitted_docs

    def _extract_image_descriptions(
        self, docs: Sequence[Document]
    ) -> list[MetadataTypedDocument[_ImageMetadata]]:
        image_convertor = ExtractImageConvertor()
        image_docs = image_convertor.convert_documents(docs)
        image_metadata_set: set[_ImageMetadata] = set()

        for doc in image_docs:
            images = doc.images
            image_metadata_set.update(images)

        image_metadata = list(image_metadata_set)
        image_descriptions = describe_images(image_metadata)

        return image_descriptions
