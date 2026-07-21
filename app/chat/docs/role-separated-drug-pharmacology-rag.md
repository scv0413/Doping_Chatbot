# Role-Separated Drug Search, Pharmacology Info, and RAG Safety Manual

## 목적

약물 관련 질문은 한 가지 검색만으로 끝나지 않는다. 선수와 트레이너가 실제로 묻는 질문은 보통 다음 세 성격이 섞여 있다.

- 이 약 또는 성분이 금지약물인가?
- 이미 먹었거나 먹어야 할 때 반감기 같은 참고 정보가 있는가?
- 그래도 현장에서 어떻게 행동해야 불이익을 줄일 수 있는가?

따라서 하나의 거대한 retrieval로 처리하지 않고 역할을 세 개로 나눴다.

## 역할 분리

### 1. drug_search

위치: `app/chat/drug_search/`

역할은 KADA 약물검색에 가까운 “제품명/성분명 기반 도핑 위험 조회”다. 이 모듈은 금지 가능성, 추가 확인 필요 여부, 투여 경로/종목/용량 확인 플래그를 만든다.

중요한 경계는 이 모듈이 반감기나 일반 의약품 약동학 해석을 담당하지 않는다는 점이다. drug_search는 도핑 규정상 확인해야 할 위험 신호를 반환한다.

### 2. pharmacology_info

위치: `app/chat/pharmacology/`

역할은 반감기, 배출, 대사처럼 약리학적 참고 정보를 제공하는 것이다. 단, 이것은 복용 허가나 도핑 안전 판정이 아니다.

현재는 `pseudoephedrine`부터 작은 source-backed knowledge base로 시작했다. 나중에는 약학 DB, DailyMed, PubChem, 국내 의약품 정보 API 등으로 확장할 수 있다.

설계 기준은 다음과 같다.

- 반감기는 “검출 가능 시간”과 동일하지 않다고 명시한다.
- 경기기간 중 사용 가능 여부를 반감기로 단정하지 않는다.
- 제품명, 성분명, 복용량, 마지막 복용 시각, 경기 시작 시각을 함께 확인하도록 유도한다.
- 출처가 없으면 모른다고 말하고 성분명 확인을 요청한다.

### 3. RAG safety manual

위치: `app/chat/retrieval/`, `app/chat/policy/`, manual chunks

역할은 공식 문서와 manual source에서 근거를 가져와 행동 지침을 붙이는 것이다. 예를 들어 반감기를 묻는 질문이어도 답변은 “반감기 참고”에서 끝나면 안 된다. 경기기간, S6 흥분제, 소변 농도 기준, KADA/팀닥터 확인 같은 안전 행동으로 이어져야 한다.

## 실행 흐름

현재 `run_chat_pipeline`과 `run_chat_graph`는 같은 역할 흐름을 가진다.

```text
user query
  -> router
  -> drug_search, if needed
  -> pharmacology_info, if half-life/metabolism question
  -> query rewrite
  -> RAG retrieval
  -> answer formatter / answer chain
```

`슈도에페드린 반감기가 얼마나 돼?` 같은 질문은 다음처럼 처리된다.

- router: `drug_search_with_rag`
- drug_search: 금지 가능성, S6, 용량/농도 확인 필요
- pharmacology_info: pseudoephedrine 반감기 참고와 변동 요인
- retrieval: WADA/KADA 문서 또는 manual 근거
- answer: 반감기 참고 + 도핑 안전 주의 + 근거 citation

## 왜 이렇게 나눴는가

도핑 챗봇에서 가장 위험한 설계는 “반감기 정보를 알면 사용 가능 여부를 판단할 수 있다”처럼 보이게 만드는 것이다. 실제로 반감기는 선수와 지도자에게 긴급 판단의 단서를 줄 수 있지만, 도핑검사 검출 가능 시간이나 제재 위험을 직접 결정하지 않는다.

그래서 `pharmacology_info`는 독립된 참고 정보로 두고, 최종 답변 단계에서 `drug_search`와 `RAG safety manual`이 반드시 같이 보완하도록 설계했다.

## 현재 한계

- pharmacology_info는 현재 pseudoephedrine 중심의 작은 내장 자료다.
- 출처는 PubChem, DailyMed, 약동학 논문 같은 외부 참고 자료를 기록하지만, 자동 갱신 파이프라인은 아직 없다.
- 도핑 관련 최종 판단은 KADA/WADA 공식 자료와 전문가 확인이 필요하다.

## 다음 확장

- 성분별 pharmacology record 추가
- 제품명에서 성분명으로 연결하는 normalization 강화
- pharmacology source ingestion 자동화
- 반감기 답변 전용 eval dataset 추가
- Gradio UI에서 복용 시각/경기 시각 입력 폼 추가
