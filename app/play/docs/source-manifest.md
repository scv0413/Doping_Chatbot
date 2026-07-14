# Source Manifest

## 목적

이 문서는 RAG 챗봇에 사용할 원본 자료의 출처, 버전, 문서 유형, 처리 방식을 기록한다.

PDF 파일명만으로 문서 의미를 추측하지 않고, 이 manifest를 기준으로 문서 메타데이터를 관리한다.

## PDF Sources

| id | file path | title | authority | year | language | document type | processing note | status |
|---|---|---|---|---|---|---|---|---|
| kada_anti_doping_rules_2021_ko | data/raw/pdf/kada/kada_anti_doping_rules_2021_ko_amended_20220308.pdf | 한국도핑방지규정 개정안 전문 | KADA | 2021 | ko | rules | 일반 PDF, 개정일 확인 필요 | 확인 필요 |
| kada_pro_sports_rules_2021_ko | data/raw/pdf/kada/kada_pro_sports_anti_doping_rules_2021_ko_amended_20220726.pdf | 프로스포츠 도핑방지규정 일부개정안 전문 | KADA | 2021 | ko | rules | 일반 PDF, 적용 범위 확인 필요 | 확인 필요 |
| wada_prohibited_list_2026_ko | data/raw/pdf/wada/wada_prohibited_list_2026_ko.pdf | 금지목록 국제표준 | WADA | 2026 | ko | prohibited_list | 목록/표 구조 확인 필요 | 확인 필요 |
| wada_code_consolidated_ko | data/raw/pdf/wada/wada_world_anti_doping_code_consolidated_ko.pdf | 세계도핑방지규약 통합본 | WADA | unknown | ko | code | 일반 PDF, 버전/시행일 확인 필요 | 확인 필요 |
| wada_isti_2021_ko_en | data/raw/pdf/wada/wada_isti_2021_ko_en.pdf | 검사 및 조사 국제표준 | WADA | 2021 | mixed | testing_standard | 한/영 병렬 또는 번역 구조 확인 필요 | 확인 필요 |
| wada_istue_2021_ko | data/raw/pdf/wada/wada_istue_2021_ko.pdf | 치료목적사용면책 국제표준 | WADA | 2021 | ko | tue_standard | 일반 PDF | 확인 필요 |
| wada_isrm_2021_ko_en | data/raw/pdf/wada/wada_isrm_2021_ko_en.pdf | 결과관리 국제표준 | WADA | 2021 | mixed | results_management | 한/영 병렬 또는 번역 구조 확인 필요 | 확인 필요 |
| wada_ise_2021_ko_en | data/raw/pdf/wada/wada_ise_2021_ko_en.pdf | 교육 국제표준 | WADA | 2021 | mixed | education_standard | 한/영 병렬 또는 번역 구조 확인 필요 | 확인 필요 |
| wada_isl_2021_ko_en | data/raw/pdf/wada/wada_isl_2021_ko_en.pdf | 시험실 국제표준 | WADA | 2021 | mixed | laboratory_standard | 한/영 병렬 또는 번역 구조 확인 필요 | 확인 필요 |
| wada_isccs_2024_ko | data/raw/pdf/wada/wada_isccs_2024_ko.pdf | 가맹기구 규약준수 국제표준 | WADA | 2024 | ko | compliance_standard | 일반 PDF | 확인 필요 |
| wada_tue_asthma_2023_en | data/raw/pdf/wada/tue_guidelines/wada_tue_physician_guideline_asthma_2023_en.pdf | TUE Physician Guideline - Asthma | WADA | 2023 | en | tue_guideline | 영문 의사용 가이드라인 | 확인 필요 |
| wada_tue_cardiovascular_beta_blockers_2020_en | data/raw/pdf/wada/tue_guidelines/wada_tue_physician_guideline_cardiovascular_beta_blockers_2020_en.pdf | TUE Physician Guideline - Cardiovascular Beta Blockers | WADA | 2020 | en | tue_guideline | 영문 의사용 가이드라인 | 확인 필요 |
| wada_tue_anaphylaxis_2021_en | data/raw/pdf/wada/tue_guidelines/wada_tue_physician_guideline_anaphylaxis_2021_en.pdf | TUE Physician Guideline - Anaphylaxis | WADA | 2021 | en | tue_guideline | 영문 의사용 가이드라인 | 확인 필요 |
| wada_tue_diabetes_mellitus_2022_en | data/raw/pdf/wada/tue_guidelines/wada_tue_physician_guideline_diabetes_mellitus_2022_en.pdf | TUE Physician Guideline - Diabetes Mellitus | WADA | 2022 | en | tue_guideline | 영문 의사용 가이드라인 | 확인 필요 |
| wada_tue_adhd_2021_en | data/raw/pdf/wada/tue_guidelines/wada_tue_physician_guideline_adhd_2021_en.pdf | TUE Physician Guideline - ADHD | WADA | 2021 | en | tue_guideline | 영문 의사용 가이드라인 | 확인 필요 |
| wada_tue_pain_management_en | data/raw/pdf/wada/tue_guidelines/wada_tue_physician_guideline_pain_management_en.pdf | TUE Physician Guideline - Pain Management | WADA | unknown | en | tue_guideline | 영문 의사용 가이드라인, 연도 확인 필요 | 확인 필요 |
| wada_tue_musculoskeletal_2021_en | data/raw/pdf/wada/tue_guidelines/wada_tue_physician_guideline_musculoskeletal_2021_en.pdf | TUE Physician Guideline - Musculoskeletal Conditions | WADA | 2021 | en | tue_guideline | 영문 의사용 가이드라인 | 확인 필요 |

## Notes

- `status`가 `확인 필요`인 문서는 공식 출처 URL, 시행일, 버전을 아직 검증하지 않았다는 뜻이다.
- `language`가 `mixed`인 문서는 한/영 병렬 구조, 번역본 구조, 표 구조를 loader 구현 전에 샘플 확인해야 한다.
- TUE physician guideline 문서는 선수/트레이너 답변에 바로 단정적으로 사용하지 않고, TUE 가능성 및 의료진 상담 안내의 보조 근거로 사용한다.

