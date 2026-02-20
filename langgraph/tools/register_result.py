"""Tool③: 書面審査結果登録ツール.

Dify: BPaaS_書面審査結果登録ツール
フロー: 開始 → パラメータ抽出 → LLM(metadata生成) → コード(現在時刻) → HTTP POST → 終了
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI

from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_ENDPOINT,
    BPAAS_API_BASE_URL,
    LLM_TEMPERATURE,
)
from prompts.register_result import (
    METADATA_GENERATION_PROMPT,
    PARAMETER_EXTRACTION_DESCRIPTIONS,
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
# Step 1: パラメータ抽出 (Dify: parameter-extractor)
# ---------------------------------------------------------------------------
def _extract_parameters(prompt: str) -> dict:
    """LLM を使ってテキストからパラメータを抽出する.

    Dify の parameter-extractor ノードに対応。
    structured output で抽出する。
    """
    llm = _get_llm()

    extraction_instructions = "\n".join(
        f"- {name}: {desc}"
        for name, desc in PARAMETER_EXTRACTION_DESCRIPTIONS.items()
    )

    system_prompt = f"""\
以下のテキストデータから、下記のパラメータを抽出してください。
JSONフォーマットで出力してください。

{extraction_instructions}

出力例:
{{
    "company_name": "...",
    "system_status": "completed",
    "decision_reason": "...",
    "contract_number": "...",
    "case_number": "...",
    "metadata_list": ["(flow_type,差戻しコメントID,チェック項目ID,AI判断理由)"]
}}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    response = llm.invoke(messages)

    try:
        # レスポンスから JSON 部分を抽出
        content = response.content
        # ```json ... ``` でラップされている場合を考慮
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        logger.error("パラメータ抽出に失敗しました: %s", response.content)
        return {
            "company_name": "",
            "system_status": "completed",
            "decision_reason": "",
            "contract_number": "",
            "case_number": "12345678",
            "metadata_list": [],
        }


# ---------------------------------------------------------------------------
# Step 2: metadata JSON 生成 (Dify: LLM "metadata生成" ノード)
# ---------------------------------------------------------------------------
def _generate_metadata(params: dict) -> str:
    """抽出パラメータから details 用の metadata JSON を生成する."""
    llm = _get_llm()

    metadata_list_str = str(params.get("metadata_list", []))
    system_status = params.get("system_status", "completed")

    system_prompt = METADATA_GENERATION_PROMPT.format(
        metadata_list=metadata_list_str,
        system_status=system_status,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"metadata_list: {metadata_list_str}"},
    ]
    response = llm.invoke(messages)
    return response.content


# ---------------------------------------------------------------------------
# Step 3: 現在時刻取得 (Dify: コード "現在時刻取得" ノード)
# ---------------------------------------------------------------------------
def _get_now_datetime() -> str:
    """日本時間の現在時刻を文字列で返す."""
    return str(datetime.now(ZoneInfo("Asia/Tokyo")))


# ---------------------------------------------------------------------------
# Step 4: HTTP POST (スタブ)
# ---------------------------------------------------------------------------
def _post_result(payload: dict) -> int:
    """外部 API に結果を POST する (スタブ).

    本番では httpx.post() で実行する。

    Returns:
        HTTP ステータスコード。
    """
    logger.info("[STUB] POST %s/process", BPAAS_API_BASE_URL)
    logger.info("[STUB] Payload: %s", json.dumps(payload, ensure_ascii=False, indent=2))
    # スタブ: 200 を返す
    # 本番実装例:
    # import httpx
    # resp = httpx.post(f"{BPAAS_API_BASE_URL}/process", json=payload, timeout=30)
    # return resp.status_code
    return 200


# ===========================================================================
# メインツール
# ===========================================================================
@tool
def register_result(prompt: str) -> str:
    """書面審査結果登録ツール. 審査結果をデータベースに登録する.

    書面チェック結果と承認・差戻し判定結果を含むテキストを受け取り、
    パラメータを抽出して外部 API に POST する。

    Args:
        prompt: 書面チェック結果 + 書面審査結果を含むテキストデータ。

    Returns:
        登録結果 (HTTP ステータスコード)。
    """
    # Step 1: パラメータ抽出
    params = _extract_parameters(prompt)
    logger.info("抽出パラメータ: %s", params)

    # Step 2: metadata JSON 生成
    metadata_json = _generate_metadata(params)
    logger.info("生成されたmetadata: %s", metadata_json)

    # Step 3: 現在時刻取得
    now_datetime = _get_now_datetime()

    # Step 4: HTTP POST ペイロード構築
    payload = {
        "company_name": params.get("company_name", ""),
        "document_type": "review",
        "identifiers": [
            {
                "identifier_type": "case_number",
                "identifier_value": params.get("case_number", "12345678"),
            },
            {
                "identifier_type": "contract_number",
                "identifier_value": params.get("contract_number", ""),
            },
        ],
        "search_condition_id": 1,
        "system_status": params.get("system_status", "completed"),
        "requested_at": now_datetime,
        "start_at": "2025-12-18 13:00:00",  # Dify では固定値
        "end_at": "2025-12-18 13:20:00",  # Dify では固定値
        "details": [metadata_json],
    }

    status_code = _post_result(payload)

    return str(status_code)
