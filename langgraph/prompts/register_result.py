"""書面審査結果登録ツール用プロンプト.

Dify: BPaaS_書面審査結果登録ツール
"""

# ---------------------------------------------------------------------------
# パラメータ抽出 (Dify: parameter-extractor ノード)
# ---------------------------------------------------------------------------
PARAMETER_EXTRACTION_DESCRIPTIONS = {
    "company_name": '"契約者（甲）お客様名（書面用）"の値を代入してください。',
    "system_status": '"書面審査結果"の値が"承認"であれば"completed"、"差戻し"であれば"returned"となります。',
    "decision_reason": (
        '"書面チェック結果"に書かれている、判断理由を示した文章です。\n'
        '書面審査結果が"承認"の場合は何も代入せず、""としてください。'
    ),
    "contract_number": '"契約番号"の値です。',
    "case_number": (
        '"案件番号"の値です。\n'
        '"案件番号"が存在しない場合は12345678を代入してください。'
    ),
    "metadata_list": (
        "はじめに、パラメータを抽出する対象となるテキストデータのフォーマットを説明します。\n\n"
        "■差戻しコメントID\n"
        "・差戻しコメントID\n"
        "・フロー種別判定フラグ\n"
        "・NGと判断された理由\n\n"
        "■チェック項目ID\n"
        "・チェック項目ID\n"
        "・フロー種別判定フラグ\n"
        "・NGと判断された理由\n\n"
        "次に、下記の情報をそれぞれ特定してください。\n\n"
        '・flow_type("document_check"または"data_verification")\n'
        "・差戻しコメントID\n"
        "・上記差戻しコメントIDと対応するチェック項目ID\n"
        "・NGと判断された理由\n\n"
        "値は下記のフォーマットで出力してください。\n"
        '"■差戻しコメントID"や"■チェック項目ID"が複数ある場合は、Pythonのリストに準じて追記してください。\n\n'
        "[(flow_type,差戻しコメントID,チェック項目ID,AI判断理由),]\n\n"
        "※複数ある場合の例\n"
        "[(flow_type,差戻しコメントID,チェック項目ID,AI判断理由), "
        "(flow_type,差戻しコメントID,チェック項目ID,AI判断理由), "
        "(flow_type,差戻しコメントID,チェック項目ID,AI判断理由),]"
    ),
}

# ---------------------------------------------------------------------------
# metadata JSON 生成 (Dify: LLM "metadata生成" ノード)
# ---------------------------------------------------------------------------
METADATA_GENERATION_PROMPT = """\
{metadata_list}を参照して、下記のJSON文字列を出力してください。

"flow_type"が"document_check"であれば、下記フォーマットの"document_check"の"metadata"に情報を追記します。
"flow_type"が"data_verification"であれば、下記フォーマットの"data_verification"の"metadata"に情報を追記します。

**下記のフォーマットに書かれていないこと、例えば"[]"などは絶対に出力しないでください。**

{{
    "flow_type": "document_check",
    "process_status": "{system_status}",
    "metadata": [{{
        "check_list_id": {{チェック項目ID}},
        "comment_id": {{差戻しコメントID}},
        "decision_reason": "{{AI判断理由}}"
    }}]
}},
{{
    "flow_type": "data_verification",
    "process_status": "{system_status}",
    "metadata": [{{
        "check_list_id": {{チェック項目ID}},
        "comment_id": {{差戻しコメントID}},
        "decision_reason": "{{AI判断理由}}"
    }}]
}}

{metadata_list}を参照した結果、flow_typeに"document_check"がない場合は、"document_check"のJSON文字列を下記のように書き換えてください。
{{
    "flow_type": "document_check",
    "process_status": "completed",
    "metadata": []
}}

また、{metadata_list}を参照した結果、flow_typeに"data_verification"がない場合は、"data_verification"のJSON文字列を下記のように書き換えてください。
{{
    "flow_type": "data_verification",
    "process_status": "completed",
    "metadata": []
}}
"""
