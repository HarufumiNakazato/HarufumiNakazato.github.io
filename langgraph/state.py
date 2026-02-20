"""LangGraph のグラフ状態定義."""

from __future__ import annotations

from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ReviewState(TypedDict):
    """書面審査エージェントのグラフ状態.

    messages: ReAct エージェントの会話履歴（tool-calling ループ用）
    prompt:   オーケストレータへの入力 (契約データ JSON 文字列)
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    prompt: str
