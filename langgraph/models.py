"""Pydantic モデル定義 -- 入出力スキーマ."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 入力データ構造 (Dify の prompt JSON に対応)
# ---------------------------------------------------------------------------
class ContractDocument(BaseModel):
    """契約書一覧照会の1件."""

    契約書名: str = ""


class BasicInfo(BaseModel):
    """基本情報タブ."""

    契約者_甲_お客様名_書面用: str = Field("", alias="契約者（甲）お客様名（書面用）")
    契約者_甲_お客様名: str = Field("", alias="契約者（甲）お客様名")
    契約者_甲_住所: str = Field("", alias="契約者（甲）住所")
    契約者_甲_氏名: str = Field("", alias="契約者（甲）氏名")
    契約者_乙_住所: str = Field("", alias="契約者（乙）住所")
    契約者_乙_会社名_書面用: str = Field("", alias="契約者（乙）会社名（書面用）")
    契約者_乙_組織名: str = Field("", alias="契約者（乙）組織名")
    契約者_乙_役職: str = Field("", alias="契約者（乙）役職")
    契約者_乙_契約者氏名: str = Field("", alias="契約者（乙）契約者氏名")
    契約者_乙_担当者氏名: str = Field("", alias="契約者（乙）担当者氏名")

    model_config = {"populate_by_name": True}


class TradeDetail(BaseModel):
    """取引明細タブの1行."""

    no: str = Field("", alias="NO.")
    商品名: str = ""
    商品コード: str = ""
    数量: str = ""
    税抜金額: str = Field("", alias="税抜金額（円）")

    model_config = {"populate_by_name": True}


class PaymentCondition(BaseModel):
    """支払区分."""

    支払区分: str = ""
    支払方法: str = ""
    支払期日: str = ""


class CollectionCondition(BaseModel):
    """回収条件."""

    回収条件NO: str = Field("", alias="回収条件NO.")
    請求先名: str = ""

    model_config = {"populate_by_name": True}


class CollectionDetail(BaseModel):
    """回収条件・請求先情報の1行."""

    回収条件NO: str = Field("", alias="回収条件NO.")
    回収条件: Optional[CollectionCondition] = None
    支払区分: Optional[PaymentCondition] = None

    model_config = {"populate_by_name": True}


class CollectionInfo(BaseModel):
    """回収条件・請求先情報."""

    商品明細一覧: list[CollectionDetail] = []


class FileInfo(BaseModel):
    """ファイル情報."""

    署名付きURL: str = ""
    画像ファイル名: str = ""


class ContractData(BaseModel):
    """オーケストレータに渡される入力データ全体."""

    契約書一覧照会: list[ContractDocument] = []
    基本情報タブ: Optional[BasicInfo] = None
    取引明細タブ: list[TradeDetail] = []
    回収条件_請求先情報: Optional[CollectionInfo] = Field(None, alias="回収条件・請求先情報")
    ファイル情報: list[FileInfo] = []
    契約番号: str = ""
    案件番号: str = ""
    基本契約: str = ""
    契約締結日_注文日: str = Field("", alias="契約締結日（注文日）")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# パラメータ抽出結果 (結果登録ツール用)
# ---------------------------------------------------------------------------
class ExtractedParams(BaseModel):
    """BPaaS_書面審査結果登録ツール のパラメータ抽出結果."""

    company_name: str = ""
    system_status: str = ""  # "completed" or "returned"
    decision_reason: str = ""
    contract_number: str = ""
    case_number: str = "12345678"
    metadata_list: list[str] = []


# ---------------------------------------------------------------------------
# メタデータ (結果登録用)
# ---------------------------------------------------------------------------
class MetadataEntry(BaseModel):
    """details 内の1エントリ."""

    check_list_id: int = 0
    comment_id: int = 0
    decision_reason: str = ""


class FlowResult(BaseModel):
    """document_check / data_verification のフロー結果."""

    flow_type: str = ""
    process_status: str = ""
    metadata: list[MetadataEntry] = []
