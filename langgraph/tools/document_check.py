"""Tool①: 注文書チェックツール.

Dify: BPaaS_注文書チェックツール
フロー:
  正常系: 開始 → パラメータ抽出 → HTTP(署名付きURL) → PDF to PNG
          → LLM Vision(発注書チェック) → LLM(差戻しコメントID判定)
          → LLM(チェック項目ID判定) → コード結合 → 終了
  異常系: HTTP失敗 → LLM(書面未添付) → 差戻しコメントID判定
          → チェック項目ID判定 → コード結合 → 終了
"""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI

from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_ENDPOINT,
    LLM_TEMPERATURE,
)
from prompts.document_check import (
    CHECK_LIST,
    CHECK_LIST_ID_PROMPT,
    DOCUMENT_CHECK_PROMPT,
    DOCUMENT_NOT_FOUND_PROMPT,
    RETURN_COMMENT_ID_PROMPT,
    RETURN_COMMENT_LIST,
)

logger = logging.getLogger(__name__)


def _get_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        temperature=LLM_TEMPERATURE,
    )


# ---------------------------------------------------------------------------
# Step 1: パラメータ抽出 (署名付きURL)
# ---------------------------------------------------------------------------
def _extract_presigned_url(prompt_data: str) -> str | None:
    """入力 JSON からファイル情報の署名付きURLを抽出する."""
    try:
        data = json.loads(prompt_data)
        file_info_list = data.get("ファイル情報", [])
        for fi in file_info_list:
            url = fi.get("署名付きURL", "")
            if url:
                return url
    except (json.JSONDecodeError, TypeError):
        pass

    # JSON パース失敗時は LLM にフォールバック
    llm = _get_llm()
    messages = [
        {
            "role": "system",
            "content": "以下のテキストデータを参照し、注文書の署名付きURLを抜き出してください。URLのみを出力してください。",
        },
        {"role": "user", "content": prompt_data},
    ]
    response = llm.invoke(messages)
    url = response.content.strip()
    return url if url.startswith("http") else None


# ---------------------------------------------------------------------------
# Step 2: HTTP GET でファイル取得 (スタブ)
# ---------------------------------------------------------------------------
def _download_file(url: str) -> bytes | None:
    """署名付きURLからファイルをダウンロードする (スタブ).

    本番では httpx.get(url) でバイナリを取得する。
    """
    logger.info("[STUB] ファイルダウンロード: %s", url)
    # スタブ: None を返して「書面未添付」フローへ分岐させる
    # 本番実装例:
    # import httpx
    # resp = httpx.get(url, follow_redirects=True, timeout=30)
    # return resp.content if resp.status_code == 200 else None
    return None


# ---------------------------------------------------------------------------
# Step 3: PDF → PNG 変換 (PyMuPDF)
# ---------------------------------------------------------------------------
def _pdf_to_png_images(pdf_bytes: bytes) -> list[str]:
    """PDF バイナリを PNG 画像 (base64) のリストに変換する."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images_b64: list[str] = []
    for page in doc:
        mat = fitz.Matrix(2, 2)  # zoom=2
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        images_b64.append(base64.b64encode(img_bytes).decode("utf-8"))
    doc.close()
    return images_b64


# ---------------------------------------------------------------------------
# Step 4: LLM Vision - 発注書チェック
# ---------------------------------------------------------------------------
def _check_document_with_vision(
    images_b64: list[str],
    prompt_data: str,
) -> str:
    """注文書画像を LLM Vision で突合チェックする."""
    llm = _get_llm()

    system_prompt = DOCUMENT_CHECK_PROMPT.format(prompt=prompt_data)

    # マルチモーダル入力: テキスト + 画像群
    content: list[dict[str, Any]] = [{"type": "text", "text": system_prompt}]
    for img_b64 in images_b64:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}",
                    "detail": "high",
                },
            }
        )

    messages = [HumanMessage(content=content)]
    response = llm.invoke(messages)
    return response.content


# ---------------------------------------------------------------------------
# Step 4': 書面未添付時のフォールバック
# ---------------------------------------------------------------------------
def _document_not_found_result() -> str:
    """書面未添付時の固定レスポンスを生成する."""
    llm = _get_llm()
    messages = [
        {"role": "system", "content": DOCUMENT_NOT_FOUND_PROMPT},
        {"role": "user", "content": "出力してください。"},
    ]
    response = llm.invoke(messages)
    return response.content


# ---------------------------------------------------------------------------
# Step 5: 差戻しコメントID判定
# ---------------------------------------------------------------------------
def _determine_return_comment_id(check_result: str) -> str:
    """チェック結果から差戻しコメントIDを判定する."""
    llm = _get_llm()
    system_prompt = RETURN_COMMENT_ID_PROMPT.format(
        check_result=check_result,
        return_comment_list=RETURN_COMMENT_LIST,
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": check_result},
    ]
    response = llm.invoke(messages)
    return response.content


# ---------------------------------------------------------------------------
# Step 6: チェック項目ID判定
# ---------------------------------------------------------------------------
def _determine_check_list_id(check_result: str) -> str:
    """チェック結果からチェック項目IDを判定する."""
    llm = _get_llm()
    system_prompt = CHECK_LIST_ID_PROMPT.format(
        check_result=check_result,
        check_list=CHECK_LIST,
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": check_result},
    ]
    response = llm.invoke(messages)
    return response.content


# ---------------------------------------------------------------------------
# Step 7: 結果結合 (Dify: コード実行ノード)
# ---------------------------------------------------------------------------
def _combine_results(
    doc_check_result: str,
    return_comment_id: str,
    check_list_id: str,
) -> str:
    """3つの結果を結合して最終出力とする."""
    return doc_check_result + return_comment_id + check_list_id


# ===========================================================================
# メインツール
# ===========================================================================
@tool
def document_check(prompt: str) -> str:
    """注文書チェックツール. 契約データ JSON を受け取り、注文書の書面チェックを実行する.

    入力データに含まれる署名付きURLから注文書ファイルを取得し、
    PDF→PNG変換後、LLM Vision で突合チェックを行う。
    チェック結果に基づき差戻しコメントID・チェック項目IDも判定する。

    Args:
        prompt: 契約データ JSON 文字列。

    Returns:
        注文書チェック結果 + 差戻しコメントID + チェック項目ID の結合テキスト。
    """
    # Step 1: パラメータ抽出
    presigned_url = _extract_presigned_url(prompt)

    if not presigned_url:
        logger.warning("署名付きURLが見つかりません。書面未添付として処理します。")
        doc_check_result = _document_not_found_result()
        return_comment_id = _determine_return_comment_id(doc_check_result)
        check_list_id = _determine_check_list_id(doc_check_result)
        return _combine_results(doc_check_result, return_comment_id, check_list_id)

    # Step 2: ファイルダウンロード
    file_bytes = _download_file(presigned_url)

    if file_bytes is None:
        # HTTP失敗 → 書面未添付フロー (Dify: fail-branch)
        logger.warning("ファイルダウンロード失敗。書面未添付として処理します。")
        doc_check_result = _document_not_found_result()
        return_comment_id = _determine_return_comment_id(doc_check_result)
        check_list_id = _determine_check_list_id(doc_check_result)
        return _combine_results(doc_check_result, return_comment_id, check_list_id)

    # Step 3: PDF → PNG
    images_b64 = _pdf_to_png_images(file_bytes)

    # Step 4: LLM Vision で発注書チェック
    doc_check_result = _check_document_with_vision(images_b64, prompt)

    # Step 5: 差戻しコメントID判定
    return_comment_id = _determine_return_comment_id(doc_check_result)

    # Step 6: チェック項目ID判定
    check_list_id = _determine_check_list_id(doc_check_result)

    # Step 7: 結合
    return _combine_results(doc_check_result, return_comment_id, check_list_id)
