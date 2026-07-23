# Retrieval Eval vs LangGraph Retrieval Eval

## Purpose

기존 retrieval-only eval과 LangGraph 기반 retrieval eval을 같은 10개 케이스와 같은 evaluator로 비교한다.
목적은 LangGraph 도입 이후에도 검색 품질이 유지되는지 확인하는 것이다.

## Configuration

- top_k: 3
- baseline rewrite_enabled: True
- graph use_llm: False
- evaluator: route_match, source_hit, term_hit, context_budget, retrieval_quality

## Average Scores

| Runner | route_match | source_hit | term_hit | context_budget | retrieval_quality |
|---|---:|---:|---:|---:|---:|
| baseline retrieval | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| LangGraph retrieval | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

## Case Details

| Case | Baseline quality | Graph quality | Baseline chunks | Graph chunks |
|---|---:|---:|---|---|
| `definition_s0` | 1.00 | 1.00 | wada_prohibited_list_2026_ko:p5:c1, wada_prohibited_list_2026_ko:p5:c0, wada_prohibited_list_2026_ko:p7:c1 | wada_prohibited_list_2026_ko:p5:c1, wada_prohibited_list_2026_ko:p5:c0, wada_prohibited_list_2026_ko:p7:c1 |
| `drug_tylenol` | 1.00 | 1.00 | - | - |
| `drug_pseudoephedrine` | 1.00 | 1.00 | wada_prohibited_list_2026_ko:p16:c1, wada_prohibited_list_2026_ko:p4:c4, wada_prohibited_list_2026_ko:p22:c2 | wada_prohibited_list_2026_ko:p4:c4, wada_prohibited_list_2026_ko:p4:c3, wada_prohibited_list_2026_ko:p16:c1 |
| `procedure_tue` | 1.00 | 1.00 | field_response_manual:s6:c0, kada_anti_doping_rules_2021_ko:p28:c1, kada_anti_doping_rules_2021_ko:p28:c0 | field_response_manual:s6:c0, kada_anti_doping_rules_2021_ko:p28:c1, kada_anti_doping_rules_2021_ko:p28:c0 |
| `field_dco_identity` | 1.00 | 1.00 | field_response_manual:s1:c0, kada_anti_doping_rules_2021_ko:p18:c1, wada_isti_2021_ko_en:p81:c4 | field_response_manual:s1:c0, kada_anti_doping_rules_2021_ko:p18:c1, wada_isti_2021_ko_en:p81:c4 |
| `field_night_blood` | 1.00 | 1.00 | field_response_manual:s2:c0, wada_isti_2021_ko_en:p137:c3, wada_isti_2021_ko_en:p139:c0 | field_response_manual:s2:c0, wada_isti_2021_ko_en:p137:c3, wada_isti_2021_ko_en:p139:c0 |
| `field_injury_delay` | 1.00 | 1.00 | field_response_manual:s3:c0, field_response_manual:s1:c0, kada_anti_doping_rules_2021_ko:p100:c1 | field_response_manual:s3:c0, field_response_manual:s1:c0, kada_anti_doping_rules_2021_ko:p100:c1 |
| `drug_nasal_spray` | 1.00 | 1.00 | field_response_manual:s4:c0, kada_anti_doping_rules_2021_ko:p26:c0, wada_prohibited_list_2026_ko:p4:c4 | field_response_manual:s4:c0, kada_anti_doping_rules_2021_ko:p26:c0, wada_prohibited_list_2026_ko:p4:c4 |
| `field_leave_station` | 1.00 | 1.00 | field_response_manual:s3:c0, kada_anti_doping_rules_2021_ko:p35:c1, field_response_manual:s2:c0 | field_response_manual:s3:c0, kada_anti_doping_rules_2021_ko:p35:c1, field_response_manual:s2:c0 |
| `drug_half_life` | 1.00 | 1.00 | field_response_manual:s5:c0, field_response_manual:s4:c0, kada_anti_doping_rules_2021_ko:p19:c1 | field_response_manual:s5:c0, field_response_manual:s4:c0, kada_anti_doping_rules_2021_ko:p19:c1 |

## Interpretation

LangGraph는 기존 pipeline 기능을 graph node로 감싼 1차 구조이며, 이 비교에서는 agentic retry나 추가 tool loop를 사용하지 않는다.
따라서 점수가 유지된다는 것은 orchestration layer를 LangGraph로 바꾸어도 검색 품질이 유지된다는 근거가 된다.

다음 단계에서는 이 결과를 기준선으로 삼고, 검색 결과가 비거나 품질이 낮을 때만 1회 재시도하는 최소 agentic graph를 설계한다.
