"""Tool②: 承認・差戻しツール.

Dify: BPaaS_承認・差戻しツール
フロー: 開始 → LLM → 終了

書面チェック結果を受け取り、差戻しコメント一覧と照合して
承認 or 差戻しを判定する。
"""

from __future__ import annotations

from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI

from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_ENDPOINT,
    LLM_TEMPERATURE,
)
from prompts.approve_or_reject import APPROVE_OR_REJECT_SYSTEM_PROMPT


def _get_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        temperature=LLM_TEMPERATURE,
    )


@tool
def approve_or_reject(prompt: str) -> str:
    """書面チェック結果を受け取り、承認・差戻しを判定するツール.

    Args:
        prompt: 書面チェックエージェントの実行結果テキスト。

    Returns:
        承認/差戻し判定結果テキスト。
        フォーマット:
            ■ ツール実行結果 (SUCCESS/FAILED)
            ■ 書面審査結果 (承認/差戻し)
            ・差戻しコメント (差戻しの場合のみ)
    """
    llm = _get_llm()

    system_message = APPROVE_OR_REJECT_SYSTEM_PROMPT.format(
        check_result=prompt,
    )

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]

    response = llm.invoke(messages)
    return response.content
