"""書面審査エージェント -- LangGraph エントリーポイント.

Dify: BPaaS_オーケストレータ用エージェント_書面審査業務 を
LangGraph の ReAct エージェントとして再実装。

グラフ構成:
  開始 → ReAct Agent (tool-calling loop) → 終了

Agent が使用するツール:
  ① document_check   -- 注文書チェック
  ② approve_or_reject -- 承認・差戻し判定
  ③ register_result   -- 結果登録 (外部API POST)
"""

from __future__ import annotations

import json
import logging
import sys

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent

from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_ENDPOINT,
    LLM_TEMPERATURE,
)
from prompts.orchestrator import ORCHESTRATOR_INSTRUCTION, ORCHESTRATOR_QUERY_TEMPLATE
from tools import approve_or_reject, document_check, register_result

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
def _get_orchestrator_llm() -> AzureChatOpenAI:
    """オーケストレータ用の LLM を生成する.

    Dify では gpt-5-mini / max_completion_tokens=128000 を使用していたが、
    ここでは AZURE_OPENAI_DEPLOYMENT の設定に従う。
    """
    return AzureChatOpenAI(
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        temperature=LLM_TEMPERATURE,
    )


# ---------------------------------------------------------------------------
# グラフ構築
# ---------------------------------------------------------------------------
def build_graph():
    """LangGraph の ReAct エージェントグラフを構築する.

    Dify のオーケストレータ (ReAct 戦略) に対応:
      - system instruction でツールの使い方と実行順序を指示
      - ツール一覧をバインド
      - create_react_agent で tool-calling ループを構築
    """
    llm = _get_orchestrator_llm()

    tools = [document_check, approve_or_reject, register_result]

    graph = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SystemMessage(content=ORCHESTRATOR_INSTRUCTION),
    )

    return graph


# ---------------------------------------------------------------------------
# 実行
# ---------------------------------------------------------------------------
def run(prompt: str) -> str:
    """書面審査エージェントを実行する.

    Args:
        prompt: 契約データ JSON 文字列。

    Returns:
        オーケストレータの最終出力テキスト。
    """
    graph = build_graph()

    query = ORCHESTRATOR_QUERY_TEMPLATE.format(prompt=prompt)

    result = graph.invoke(
        {"messages": [HumanMessage(content=query)]},
        config={"recursion_limit": 30},
    )

    # 最後の AI メッセージを取得
    final_message = result["messages"][-1]
    return final_message.content


# ---------------------------------------------------------------------------
# CLI エントリーポイント
# ---------------------------------------------------------------------------
def main():
    """サンプル入力で実行するデモ."""

    sample_input = {
        "契約書一覧照会": [{"契約書名": "注文書"}],
        "基本情報タブ": {
            "契約者（甲）お客様名（書面用）": "サンプル株式会社",
            "契約者（甲）お客様名": "サンプル株式会社",
            "契約者（甲）住所": "東京都千代田区1-1-1",
            "契約者（甲）氏名": "山田太郎",
            "契約者（乙）住所": "東京都港区2-2-2",
            "契約者（乙）会社名（書面用）": "リコージャパン株式会社",
            "契約者（乙）組織名": "営業本部",
            "契約者（乙）役職": "部長",
            "契約者（乙）契約者氏名": "鈴木一郎",
            "契約者（乙）担当者氏名": "佐藤花子",
        },
        "取引明細タブ": [
            {
                "NO.": "1",
                "商品名": "複合機 RICOH IM C3510",
                "商品コード": "IM-C3510",
                "数量": "1",
                "税抜金額（円）": "500000",
            }
        ],
        "回収条件・請求先情報": {
            "商品明細一覧": [
                {
                    "回収条件NO.": "1",
                    "回収条件": {"回収条件NO.": "1", "請求先名": "サンプル株式会社"},
                    "支払区分": {
                        "支払区分": "一括",
                        "支払方法": "振込",
                        "支払期日": "翌月末",
                    },
                }
            ]
        },
        "ファイル情報": [
            {
                "署名付きURL": "https://example.com/presigned/order.pdf",
                "画像ファイル名": "order.pdf",
            }
        ],
        "契約番号": "C-2025-001234",
        "案件番号": "A-2025-005678",
        "基本契約": "有",
        "契約締結日（注文日）": "2025-12-18",
    }

    prompt = json.dumps(sample_input, ensure_ascii=False)

    print("=" * 60)
    print("書面審査エージェント (LangGraph) -- デモ実行")
    print("=" * 60)
    print()

    result = run(prompt)

    print()
    print("=" * 60)
    print("最終出力:")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()
