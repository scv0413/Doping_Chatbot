# KADA Drug Search Investigation

## 조사 목적

KADA 금지약물 검색 기능을 챗봇 내부 tool로 연결할 수 있는지 확인했다.

조사 기준은 다음과 같다.

```text
1. 공식 KADA 페이지에서 실제 검색 서비스가 어디에 있는지 확인
2. 검색 입력 방식 확인
3. 내부 요청 endpoint 확인
4. JSON 응답 구조 확인
5. 챗봇에 연결할 때 필요한 guardrail 확인
```

## 공식 페이지 구조

KADA 홈페이지의 금지약물 검색서비스 페이지는 자체 검색 UI를 직접 구현하기보다 `https://kada.health.kr/`를 iframe으로 포함한다.

확인한 iframe:

```html
<iframe src="https://kada.health.kr/" title="금지약물제품검색"></iframe>
```

따라서 실제 drug search adapter는 `www.kada.or.kr`이 아니라 `kada.health.kr`를 대상으로 설계해야 한다.

## 검색 화면 구조

`https://kada.health.kr/`의 상세검색은 제품명 또는 성분명을 하나의 입력창에서 받는다.

주요 form 구조:

```text
form action="/result"
method="post"
input name="bothName"
input name="idfy"
```

검색 방식:

```text
idfy=N: 상세검색
idfy=Y: 낱알검색
```

현재 챗봇의 1차 drug search tool은 상세검색만 대상으로 한다.

## 내부 endpoint

검색 결과 페이지는 처음부터 결과 목록을 HTML에 모두 넣지 않는다.

`/result` 응답 이후 `result.js`가 다음 endpoint를 호출한다.

```text
POST https://kada.health.kr/result/baseDrug
POST https://kada.health.kr/result/sunb
```

용도:

```text
/result/baseDrug: 의약품 후보 목록 조회
/result/sunb: 성분 후보 목록 조회
```

기본 요청 예시:

```bash
curl -X POST "https://kada.health.kr/result/baseDrug" \
  -H "Content-Type: application/x-www-form-urlencoded; charset=UTF-8" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d "pageNo=0&pageSize=5&bothName=타이레놀&idfy=N"
```

```bash
curl -X POST "https://kada.health.kr/result/sunb" \
  -H "Content-Type: application/x-www-form-urlencoded; charset=UTF-8" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d "pageNo=0&pageSize=5&bothName=아세트아미노펜&idfy=N"
```

## JSON 응답 구조

### 의약품 검색

`/result/baseDrug`는 다음 형태의 JSON을 반환한다.

```json
{
  "page": {
    "total": 7,
    "pageNo": 0,
    "pageSize": 5,
    "pageCount": 2
  },
  "list": [
    {
      "drug_code": "2022020300026",
      "drug_name": "타이레놀8시간이알서방정",
      "list_sunb_name": "Acetaminophen 325mg",
      "sunb_count": "1",
      "firm_name": "한국존슨앤드존슨판매",
      "cls_name": "서방정",
      "drug_class": "일반",
      "produce": "○",
      "pack_img": "",
      "drug_pic": "...",
      "herbal": "0"
    }
  ]
}
```

adapter mapping:

```text
drug_name -> DrugCandidate.name
list_sunb_name -> DrugCandidate.ingredient_names 또는 notes
firm_name -> DrugCandidate.manufacturer
drug_code -> source-specific candidate id
cls_name -> dosage form note
drug_class -> product class note
pack_img/drug_pic -> future UI image reference
```

### 성분 검색

`/result/sunb`는 다음 형태의 JSON을 반환한다.

```json
{
  "page": {
    "total": 1,
    "pageNo": 0,
    "pageSize": 5,
    "pageCount": 1
  },
  "list": [
    {
      "sunb_ename": "Acetaminophen",
      "sunb_name": "아세트아미노펜",
      "snm_cnt": 10,
      "sunb_cnt": 29,
      "ingd_code": "I002817",
      "ingame": null,
      "outgame": null,
      "mapid": null,
      "herbal": "0"
    }
  ]
}
```

금지 여부 관련 필드:

```text
ingame: 경기기간 중 상태
outgame: 경기기간 외 상태
```

확인한 값:

```text
null 또는 허용: 허용 또는 금지정보 없음으로 표시되는 케이스
금지: 금지
종목확인: 종목 확인 필요
```

## 테스트 요청 결과

### 타이레놀

요청:

```text
POST /result/baseDrug
bothName=타이레놀
```

결과:

```text
total: 7
예시 후보:
- 어린이타이레놀산160mg
- 어린이타이레놀현탁액
- 우먼스타이레놀정
- 타이레놀8시간이알서방정
- 타이레놀산500mg
```

의미:

```text
제품명 검색은 여러 후보가 나올 수 있으므로 사용자가 정확한 제품을 선택해야 한다.
```

### 아세트아미노펜

요청:

```text
POST /result/sunb
bothName=아세트아미노펜
```

결과:

```text
sunb_ename: Acetaminophen
sunb_name: 아세트아미노펜
ingame: null
outgame: null
```

의미:

```text
검색 결과만으로 "사용 가능 보장"이라고 말하지 않는다.
현재 정보 기준 금지 정보가 확인되지 않았다는 정도로 표현한다.
```

### 슈도에페드린

요청:

```text
POST /result/sunb
bothName=슈도에페드린
```

결과:

```text
sunb_ename: pseudoephedrine
sunb_name: 슈도에페드린
ingame: 금지
outgame: 허용
```

의미:

```text
경기기간 여부가 판단에 직접 영향을 준다.
```

### 테스토스테론

요청:

```text
POST /result/sunb
bothName=테스토스테론
```

결과 예시:

```text
ingame: 금지
outgame: 금지
```

의미:

```text
상시 금지 가능성이 있는 성분은 prohibited_possible 상태로 매핑할 수 있다.
```

## Guardrail

`kada.health.kr` 공식 화면의 유의사항을 답변 정책에 반영해야 한다.

반영할 내용:

```text
1. 본 서비스는 식품의약품안전처에서 허가된 국내 의약품에 한해 정보를 제공한다.
2. 건강기능식품, 보충제, 가공식품, 한약재, 국외 의약품은 신뢰성을 보장받을 수 없다.
3. 제품명과 성분명 등 검색어를 정확하게 입력할 책임은 사용자에게 있다.
4. 조회 결과가 없음은 금지를 의미하지 않는다.
5. 의약품 사용 전 의사 또는 약사와 함께 확인하는 것을 권장한다.
6. 서비스의 안정적 운영과 관리를 위해 이용 내역이 기록 및 저장된다.
```

## Adapter 구현 판단

현재 확인 기준으로는 자동 조회 adapter 구현이 가능해 보인다.

우선 구현 범위:

```text
1. 상세검색만 지원
2. 제품명/성분명 검색만 지원
3. 낱알검색은 제외
4. 검색 결과 상위 N개만 사용
5. ingame/outgame 기준으로 위험 상태값 매핑
```

아직 보류할 범위:

```text
1. 제품 상세 페이지 자동 조회
2. 성분 상세 팝업 자동 조회
3. 낱알검색
4. 이미지 기반 제품 식별
5. 대량 크롤링
```

## Risk Status Mapping 초안

```text
ingame=금지, outgame=금지
-> prohibited_possible

ingame=금지, outgame=허용
-> 경기기간 중: prohibited_possible
-> 경기기간 외: caution
-> 경기기간 unknown: caution 또는 needs_verification

ingame=종목확인 또는 outgame=종목확인
-> caution
-> requires_sport_confirmation=true

ingame/outgame이 null 또는 허용
-> low_risk 또는 needs_verification
-> 단, 제품 후보가 여러 개거나 경기기간이 unknown이면 needs_verification

검색 결과 없음
-> needs_verification
```

## 다음 구현 단계

```text
1. app/chat/drug_search/kada_client.py 생성
2. requests 없이 표준 urllib 또는 httpx 의존성 추가 여부 결정
3. search_kada_drugs(input: DrugSearchInput) -> DrugSearchResult 구현
4. 제품 후보와 성분 후보를 schema에 매핑
5. pytest에서 monkeypatch/fake response로 adapter parsing 테스트
6. 실제 네트워크 테스트는 별도 inspector로 분리
```
