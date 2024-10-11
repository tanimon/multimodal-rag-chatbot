from langchain_aws.chat_models.bedrock import ChatBedrock
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from server.rag.ingestion.model import _ImageMetadata
from server.rag.model import MetadataTypedDocument

_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "user",
            [
                {
                    "type": "text",
                    "text": "Describe the image in detail in Japanese.",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "data:{mime_type};base64,{image_base64}",
                    },
                },
            ],
        )
    ]
)

_model = ChatBedrock(
    model="anthropic.claude-3-haiku-20240307-v1:0",
    client=None,
    region="us-east-1",
)


def _image_to_dict(image: _ImageMetadata) -> dict[str, str]:
    return {"image_base64": image.base64, "mime_type": image.mime_type}


_describe_image_chain = (
    RunnableLambda(_image_to_dict) | _prompt | _model | StrOutputParser()
)


def describe_images(
    images: list[_ImageMetadata],
) -> list[MetadataTypedDocument[_ImageMetadata]]:
    """
    与えられた画像の説明を含むドキュメントを生成する。

    NOTE: 5MBを超える画像は説明を生成できないため、そのような画像は除外される。

    Args:
        images (list[_ImageMetadata]): 画像データ

    Returns:
        list[MetadataTypedDocument[_ImageMetadata]]: 画像データとその説明を含むドキュメント
    """
    # NOTE: 画像サイズが5MBを超えると以下のようなエラーが発生するため除外する
    # File "/path/to/repo/server/.venv/lib/python3.12/site-packages/langchain_aws/llms/bedrock.py", line 726, in _prepare_input_and_invoke
    # raise ValueError(f"Error raised by bedrock service: {e}")
    # ValueError: Error raised by bedrock service: An error occurred (ValidationException) when calling the InvokeModel operation: messages.0.content.1.image.source.base64: image exceeds 5 MB maximum: 7850880 bytes > 5242880 bytes
    #
    # Claudeにおける画像ファイルサイズの制限に関しては公式ドキュメントに以下の記載がある:
    # > アップロードできる画像ファイルのサイズに制限はありますか？
    # > はい、以下の制限があります。
    # > API: 画像1枚あたり最大5MB
    # > claude.ai: 画像1枚あたり最大10MB
    # > これらの制限を超える画像は拒否され、APIを使用する際にエラーが返されます。
    # ref: https://docs.anthropic.com/ja/docs/build-with-claude/vision
    filtered_images = [image for image in images if len(image.base64) < 5 * 1024 * 1024]

    image_descriptions = _describe_image_chain.batch(filtered_images)
    image_description_docs = [
        MetadataTypedDocument(
            page_content=description,
            metadata=image,
        )
        for image, description in zip(filtered_images, image_descriptions)
    ]

    return image_description_docs
