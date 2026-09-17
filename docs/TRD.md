# TRD — 구매 요청서 누락 확인 PoC

- 대응 PRD: `docs/PRD.md` v0.1
- 런타임: Python 3.11+ (검증 환경 3.14), 의존성 `openpyxl`, 개발 의존성 `pytest`
- 외부 서비스: 선택적 OpenAI Chat Completions (환경변수 `OPENAI_API_KEY`가 있을 때만, 가정)

## 1. 아키텍처

```
요청서 텍스트 ─┬─> extract(rule)  ─┐
              └─> extract(llm)   ─┤   같은 스키마(Extraction JSON)
ChatGPT 붙여넣기 JSON ────────────┘
                                   │
                                   v
                          rules.check()  ── 필수항목표·용어사전
                                   │
                    ┌──────────────┼──────────────┐
                    v              v              v
              gate.audit()   questions.draft()   evaluate.score()  ── 정답표
                    │              │              │
                    └──────> 누락 표시표 / 역할표 / 리포트 / xlsx
```

두 축을 분리한다.

- **AI 축** (추출·표준명 후보·질문 문장): 생성형 AI 또는 규칙 추출기. 결과는 항상 "제안".
- **규칙 축** (필수 항목 판정·게이트·지표): 결정적 코드. 시연에서 "AI가 잘하는 일 / 규칙으로 할 일 / 사람이 할 일"을 나누는 근거가 된다.

## 2. 데이터 스키마

### 2.1 필수 항목표 `D04_자재군별_필수항목표.csv`

| 열 | 설명 |
|---|---|
| 자재군 | `배관` (교육용 단일 자재군) |
| 항목ID | `item_id`, `qty`, `unit`, `need_date`, `delivery_location`, `spec` |
| 항목명 | 품목 ID, 수량, 단위, 희망일, 배송 위치, 규격 |
| 구분 | `공통` / `자재군추가` |
| 충족조건 | 판정 규칙 요약(사람이 읽는 문장) |
| 모호조건 | 어떤 경우 `모호`로 두는지 |
| 중요항목 | 중요 오류 계산 대상 여부(품목·수량·단위·희망일 = Y) |

### 2.2 용어 사전 `D04_용어사전_교육용.csv`

| 열 | 설명 |
|---|---|
| 품목ID | `P-01` … `P-10` |
| 표준명 | 예: `PVC 파이프` |
| 규격 | 예: `50A` (같은 표준명·다른 규격은 별도 행 → 함정) |
| 표준단위 | `본`, `개`, `m`, `롤`, `EA` 중 하나 |
| 별칭 | `;`로 구분. 예: `PVC관;피브이씨 파이프;pvc pipe` |
| 주의 | 함정 설명. 예: `P-01(50A)과 P-02(100A)는 별칭이 같음 → 규격 없으면 병합 금지` |

### 2.3 요청서 표본

- `data/requests/D04_가상구매요청서_NN.txt`: 메신저·메모형 자유 텍스트 3~6줄
- `data/requests_scan/D04_가상구매요청서_NN_scan.txt`: 같은 건의 저품질 스캔 버전. 스펙에서 지정한 항목 값 글자만 결정적으로 손상(`0↔O`, `1↔l`, 공백 삭제/삽입). 손상된 항목의 정답 상태는 `모호(판독)`
- `data/requests_manifest.csv`: 건번호, 유형, 스캔 손상 항목, 설명

### 2.4 정답표 `D04_원문위치_정답표.csv` / `.json`

| 열 | 설명 |
|---|---|
| 문서ID | `D04-01` … `D04-30`, 스캔은 `D04-01S` |
| 항목ID | 2.1의 항목ID |
| 정답상태 | `충족` / `누락` / `모호` / `불일치` |
| 정답값 | 충족일 때 원문 값(그 외 빈칸) |
| 원문시작 / 원문끝 | 원문 문자 오프셋(반열림 구간). 누락이면 빈칸 |
| 원문발췌 | `text[원문시작:원문끝]` |
| 사유 | 예: `모호 표현 '다음 주'`, `현장명만 있고 세부 위치 없음`, `표준 단위 '본'과 다름` |

### 2.5 Extraction JSON (AI·규칙 추출기·ChatGPT 붙여넣기 공통)

```json
{
  "문서ID": "D04-01",
  "항목": [
    {
      "항목ID": "item_id",
      "원문값": "P-01",
      "원문시작": 12, "원문끝": 16,
      "표준명후보": "PVC 파이프 50A",
      "표준명근거": "사전 별칭 일치",
      "메모": null
    },
    {"항목ID": "need_date", "원문값": "다음 주", "원문시작": 28, "원문끝": 32,
     "표준명후보": null, "표준명근거": null, "메모": "구체 날짜 없음"}
  ]
}
```

규칙: 값이 없으면 `원문값: null`, 오프셋 `null`. ChatGPT 출력은 오프셋 대신 `원문발췌`만 줄 수 있으므로 로더가 `text.find(발췌)`로 오프셋을 복원한다(중복이면 첫 위치, 미발견이면 오프셋 `null` → 게이트 G4 위반).

### 2.6 판정 결과 (Check Result)

```json
{"문서ID": "D04-01", "항목": [
  {"항목ID": "need_date", "상태": "모호", "원문값": "다음 주", "원문발췌": "다음 주",
   "표준명후보": null, "근거": "희망일이 특정 날짜가 아닌 표현", "확인필요": true,
   "보완질문": "희망 납기일을 정확한 날짜(예: 2026-09-25)로 알려주실 수 있을까요?",
   "역할": {"AI제안": "다음 주 → 날짜 확인 필요", "규칙": "희망일은 YYYY-MM-DD 또는 M월 D일", "사람확정": ""}}
]}
```

## 3. 모듈 설계 (`src/poc_d04/`)

| 모듈 | 책임 | 핵심 함수 |
|---|---|---|
| `catalog.py` | 필수 항목표·용어 사전 정의와 CSV 저장/로드 | `REQUIRED_FIELDS`, `LEXICON`, `write_catalog(dir)`, `load_lexicon(path)` |
| `data_gen.py` | 30건 스펙 → 텍스트 렌더링 → 스캔 손상 → 정답표 | `SPECS`, `render(spec)`, `degrade(text, fields)`, `build_dataset(dir)` |
| `extract.py` | 추출 백엔드 | `extract_rule(text, lexicon)`, `extract_llm(text, lexicon, model)`, `load_pasted(json, text)` |
| `rules.py` | 필수 항목 판정 | `check(extraction, text, lexicon) -> CheckResult` |
| `gate.py` | 게이트 G1–G5 감사 | `audit(extraction, text, lexicon) -> list[Violation]` |
| `questions.py` | 보완 질문 초안 | `draft(check_result) -> dict[field, str]` |
| `evaluate.py` | 정답표 대조 지표 | `score(results, truth) -> Metrics`, `render_report(metrics) -> str` |
| `workbook.py` | xlsx 활동지 | `build_workbook(path, sample_result)` |
| `examples.py` | 실패 장면·오프라인 캡처 | `write_bad_draft(dir)`, `write_offline_captures(dir, ids)` |
| `cli.py` | 커맨드 | `gen`, `run`, `check-paste`, `eval`, `workbook`, `examples`, `all` |

### 3.1 규칙 추출기 알고리즘 (`extract_rule`)

1. 품목 ID: `P-\d{2}` 정규식. 없으면 사전 별칭을 길이 내림차순으로 검색 → 후보 품목 목록. 후보가 규격으로 유일하게 좁혀지면 `표준명후보`에 넣고 `원문값`은 별칭 원문. 규격이 없어 둘 이상이면 `표준명후보 = "후보 N개(규격 확인)"`, 병합하지 않는다(G3).
2. 수량·단위: `(\d[\d,]*)\s*(개|EA|ea|본|m|M|미터|롤|박스)` → 수량과 단위를 별도 항목으로. 단위 토큰이 없으면 `unit=null`.
3. 희망일: ISO(`2026-09-25`), `9월 25일`, `9/25` → 충족 후보. 모호 사전(`다음 주`, `다음주`, `이번 주`, `ASAP`, `빨리`, `급함`, `이번 달 안`, `조속히`, `내주`) 매칭 시 원문값은 그 표현 그대로, 날짜로 변환하지 않는다(G2).
4. 배송 위치: `([A-Z])현장` + 뒤따르는 `\d동|지하\d층|\d층|자재창고|야적장|게이트` 등 세부 토큰. 세부 토큰이 없으면 현장명만 원문값으로 기록(→ 규칙 축에서 `모호`).
5. 규격: `\d{2,3}A`, `Ø\d+`, `\d+mm`. 없으면 `null`.
6. 손상 글자(`2O개`, `P-Ol`)는 정규식에 걸리지 않으므로 값 `null` + `메모: "판독 불가 후보: '2O개'"`를 남긴다. 판독 후보는 `[0-9OolI]` 혼합 토큰 스캔으로 찾는다.

### 3.2 규칙 판정 (`rules.check`)

| 항목 | 충족 | 모호 | 불일치 | 누락 |
|---|---|---|---|---|
| item_id | `P-NN`이 사전에 존재 | 별칭만 있음 / 후보 2개 이상 / 판독 불가 | `P-NN`이 사전에 없음 | 값 없음 |
| qty | 양의 정수 | 판독 불가 | — | 값 없음 |
| unit | 사전 표준 단위와 같음(대소문자·동의어 `EA=개` 허용) | 판독 불가 / 품목 미확정으로 비교 불가 | 표준 단위와 다름 | 값 없음 |
| need_date | 특정 날짜 | 모호 표현 / 판독 불가 | 과거 날짜(기준일 2026-09-17) | 값 없음 |
| delivery_location | 현장명 + 세부 위치 | 현장명만 | — | 값 없음 |
| spec | 규격 토큰 존재 | 판독 불가 | 품목 ID의 사전 규격과 다름 | 값 없음 |

`확인필요 = 상태 != 충족`.

### 3.3 게이트 감사 (`gate.audit`)

| 코드 | 검사 |
|---|---|
| G1 | `원문값`이 있는데 `원문시작/끝`이 없거나, `text[시작:끝] != 원문값` |
| G2 | `need_date.원문값`이 날짜 형식인데 원문 어디에도 그 날짜가 없고 모호 표현만 있음 |
| G3 | `표준명후보`가 특정 규격(품목)으로 확정됐는데 원문에 규격 토큰이 없고 별칭이 2개 이상 품목에 매핑됨 |
| G4 | `spec.원문값`이 있는데 원문에 없음 (원문 없는 규격 채움) — G1의 특수 사례로 별도 보고 |
| G5 | 결과 JSON에 `사람확정` 값이 미리 채워져 있음 (AI가 확정을 대신함) |

## 4. 지표 정의 (`evaluate.score`)

- 항목 단위로 계산한다. 문서 d, 항목 f에 대해 `truth(d,f) ∈ {충족, 누락, 모호, 불일치}`, `pred(d,f)` 동일.
- `flag_t = truth != 충족`, `flag_p = pred != 충족`.
- 누락 탐지율 = `|flag_t ∧ flag_p| / |flag_t|`
- 잘못된 누락 경고 비율 = `|¬flag_t ∧ flag_p| / |flag_p|`
- 중요 오류 = `|flag_t ∧ ¬flag_p ∧ f ∈ {item_id, qty, unit, need_date}|`
- 원문 추적 가능 비율 = `원문값이 있는 예측 중 오프셋 유효·텍스트 일치 / 원문값이 있는 예측`
- 상태 정확도(보조) = `|truth == pred| / 전체`
- 유형별(정상/누락/모호/불일치/배송조건) 및 버전별(clean/scan) 분리 표를 함께 출력한다.

## 5. CLI

```
python -m poc_d04 gen                     # data/ 생성(필수항목표·사전·30건×2·정답표)
python -m poc_d04 run --backend rule      # 전 표본 추출→판정→게이트→out/results.json
python -m poc_d04 run --backend llm       # OPENAI_API_KEY 필요(가정)
python -m poc_d04 check-paste --doc D04-01 --json paste.json   # ChatGPT 출력 검사
python -m poc_d04 eval                    # out/평가리포트.md
python -m poc_d04 workbook                # out/D04_누락표시표_활동지.xlsx
python -m poc_d04 examples                # examples/ 실패장면·오프라인 캡처
python -m poc_d04 all                     # 위 전부(rule 백엔드)
```

## 6. 테스트 전략 (`tests/`)

- `test_data_gen.py`: 30건·유형 6건씩·정답표 오프셋이 원문과 일치·스캔 손상 항목의 정답이 `모호`
- `test_extract_rule.py`: 시연 사례 → item_id/qty/unit 충족, need_date/delivery_location 확인필요; 별칭만 있는 건에서 후보 병합 금지; 손상 토큰 → null + 메모
- `test_rules.py`: 표 3.2의 각 셀 최소 1케이스
- `test_gate.py`: G1–G5 각 위반 1케이스, 정상 결과 0건
- `test_evaluate.py`: 규칙 백엔드 전 표본 지표가 목표(탐지율 ≥95%, 오탐 ≤10%, 중요오류 0, 추적율 100%) 충족; 손수 만든 pred로 공식 검증
- `test_paste.py`: 오프셋 없는 ChatGPT형 JSON 로딩 → 오프셋 복원, 미발견 시 G1 위반
- `test_workbook.py`: 시트 5개 존재, 헤더 검증

## 7. 저장소 구조

```
poc-d04/
├─ README.md            ├─ pyproject.toml   ├─ Makefile
├─ docs/  PRD.md TRD.md PLAN.md DEMO_SCRIPT_15min.md REVIEW_NN.md
├─ prompts/             ├─ data/ (gen 산출, 커밋)      ├─ examples/ (커밋)
├─ out/  (run/eval/workbook 산출, 커밋)                 ├─ src/poc_d04/   ├─ tests/
```

`data/`, `out/`, `examples/`는 결정적으로 재생성되므로 커밋해 두어 교실에서 Python 없이도 열 수 있게 한다.
