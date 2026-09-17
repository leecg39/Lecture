"""보완 질문 초안: 확인 필요 항목만 대상으로, 현장 담당자에게 보낼 문장을 만든다.

질문은 원문 값을 인용하되 값을 추정하거나 대신 채우지 않는다.
"""
from __future__ import annotations

import re

from .catalog import items_by_id


def draft(check_result: dict) -> dict:
    lex = items_by_id()
    for r in check_result["항목"]:
        if not r["확인필요"]:
            r["보완질문"] = None
            continue
        f, st, v = r["항목ID"], r["상태"], r.get("원문값")
        cand = r.get("표준명후보")
        q = None
        if f == "item_id":
            if st == "누락":
                q = "요청하신 자재의 품목 ID(P-NN) 또는 정확한 품명과 규격을 알려주세요."
            elif st == "불일치":
                q = f"품목 ID '{v}'가 자재 목록에 없습니다. 정확한 품목 ID를 확인해 주세요."
            elif "판독" in r["근거"]:
                q = f"품목 ID 글자 '{v}'가 명확하지 않습니다. 정확한 품목 ID를 알려주세요."
            else:
                ids = re.findall(r"P-\d{2}", str(cand or ""))
                opts = " / ".join(f"{i} {lex[i].display}" for i in ids if i in lex) or "자재 목록의 해당 품목"
                q = f"'{v}'은(는) {opts} 중 어느 것인가요? 규격(예: 50A/100A)을 함께 알려주세요."
        elif f == "qty":
            q = "필요 수량을 알려주세요." if st == "누락" else f"수량 '{v}' 글자가 명확하지 않습니다. 정확한 수량을 확인해 주세요."
        elif f == "unit":
            if st == "누락":
                q = f"수량의 단위({cand or '개/본/m/롤'})를 확인해 주세요."
            elif st == "불일치":
                q = f"이 품목의 표준 단위는 '{cand}'입니다. 요청하신 '{v}'이(가) 맞는지, 환산이 필요한지 확인해 주세요."
            else:
                q = f"품목이 확정되면 단위 '{v}'를 다시 확인하겠습니다. 품목 ID를 알려주세요."
        elif f == "need_date":
            if st == "누락":
                q = "희망 납기일을 날짜로 알려주세요(예: 2026-09-25)."
            elif st == "불일치":
                q = f"희망일 '{v}'이(가) 요청일 이전입니다. 날짜를 확인해 주세요."
            elif "판독" in r["근거"]:
                q = f"희망일 글자 '{v}'가 명확하지 않습니다. 정확한 날짜를 알려주세요."
            else:
                q = f"'{v}'은(는) 구체적인 날짜가 아닙니다. 희망 납기일을 정확한 날짜(예: 2026-09-25)로 알려주세요."
        elif f == "delivery_location":
            if st == "누락":
                q = "배송 현장과 세부 위치(동·층·창고·게이트)를 알려주세요."
            else:
                q = f"'{v}' 내 세부 배송 위치(동·층·창고·게이트)를 알려주세요."
        elif f == "spec":
            if st == "누락":
                q = "규격(예: 50A/100A/12mm)을 알려주세요."
            elif st == "불일치":
                q = f"품목 ID의 사전 규격은 '{cand}'인데 요청 규격은 '{v}'입니다. 어느 쪽이 맞는지 확인해 주세요."
            else:
                q = f"규격 글자 '{v}'가 명확하지 않습니다. 정확한 규격을 알려주세요."
        r["보완질문"] = q
    check_result["보완질문요약"] = [r["보완질문"] for r in check_result["항목"] if r["보완질문"]]
    return check_result
