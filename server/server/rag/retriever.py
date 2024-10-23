from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain_core.embeddings import Embeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec  # type: ignore

from server.rag.ingestion.s3_store import S3Store


def create_retriever(
    index_name: str,
    bucket_name: str,
    embedding: Embeddings,
    id_key: str = "doc_id",
    refresh: bool = False,
    force_create_index: bool = False,
) -> MultiVectorRetriever:
    docstore = S3Store(bucket_name=bucket_name)

    pinecone_client = Pinecone()
    existing_index_names = [
        index_info["name"] for index_info in pinecone_client.list_indexes()
    ]
    is_index_exists = index_name in existing_index_names

    if refresh:
        doc_keys = docstore.yield_keys()
        docstore.mdelete(list(doc_keys))

        pinecone_client.delete_index(index_name)
        pinecone_client.create_index(
            name=index_name,
            dimension=1024,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    elif not is_index_exists and force_create_index:
        pinecone_client.create_index(
            name=index_name,
            dimension=1024,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    elif not is_index_exists:
        raise ValueError(
            f"インデックス {index_name} は存在しません。作成したい場合は、force_create_index を True に設定してください。"
        )

    vectorstore = PineconeVectorStore.from_existing_index(
        index_name=index_name,
        embedding=embedding,
    )
    return MultiVectorRetriever(
        vectorstore=vectorstore,
        docstore=docstore,
        id_key=id_key,
        search_kwargs={"k": 5},
    )
