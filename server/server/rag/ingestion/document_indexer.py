import uuid
from typing import Any

from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from server.rag.retriever import create_retriever


class DocumentIndexer:
    _index_name: str
    _bucket_name: str
    _embedding: Embeddings
    _id_key: str = "doc_id"  # TODO: 外部から指定できるようにするか検討
    _retriever: MultiVectorRetriever

    def __init__(
        self,
        *,
        index_name: str,
        bucket_name: str,
        embedding: Embeddings,
        refresh: bool = False,
        force_create_index: bool = False,
    ):
        self._index_name = index_name
        self._bucket_name = bucket_name
        self._embedding = embedding

        self._retriever = create_retriever(
            index_name=self._index_name,
            bucket_name=self._bucket_name,
            embedding=self._embedding,
            id_key=self._id_key,
            refresh=refresh,
            force_create_index=force_create_index,
        )

    def index(self, documents: list[Document]) -> None:
        doc_ids = [str(uuid.uuid4()) for _ in documents]
        id_doc_pairs = list(zip(doc_ids, documents))

        # 各ドキュメントをベクトルDBとドキュメントストアそれぞれに格納
        # ベクトルDBにはドキュメントに対する埋め込みベクトルを作成して格納
        # ドキュメントストアには生のドキュメントを格納
        # ベクトルDBのデータとドキュメントストアのデータは doc_id で紐づけられる
        self._retriever.vectorstore.add_documents(
            [
                Document(
                    page_content=doc.page_content,
                    metadata={
                        **self._shrink_metadata(doc.metadata),
                        self._id_key: doc_id,
                    },
                )
                for doc_id, doc in id_doc_pairs
            ]
        )
        self._retriever.docstore.mset(id_doc_pairs)

    def _shrink_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        # NOTE: Pineconeのメタデータの最大サイズは40KBである
        # base64の値はサイズが大きく、メタデータの最大サイズを超えることがあるため除外する
        # ref: https://docs.pinecone.io/guides/data/filter-with-metadata#supported-metadata-size
        new_metadata = {
            key: value for key, value in metadata.items() if key != "base64"
        }
        return new_metadata
