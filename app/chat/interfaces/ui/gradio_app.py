import argparse
from collections.abc import Callable
from html import escape
from typing import Any

import gradio as gr

from app.chat.domain.drug_search.schemas import KADADrugDetail
from app.chat.runtime import ChatRequest, ChatResponse, DrugCandidateSummary, run_chat

DEFAULT_TITLE = "KADA/WADA 도핑 정보 챗봇"
DEFAULT_DESCRIPTION = (
    "선수와 트레이너를 위한 근거 기반 도핑 정보 확인 도구입니다. "
    "공식 판정을 대체하지 않으며, 약물 사용 전 제품명과 성분명을 반드시 확인하세요."
)
MAX_PRODUCT_CANDIDATES = 10

ChatRunner = Callable[[ChatRequest], ChatResponse]


def format_citations(response: ChatResponse) -> str:
    """Keep detailed citations available to API clients, not the player-facing UI."""
    if not response.citations:
        return "검색된 문서 근거가 없습니다."

    lines: list[str] = []
    for index, citation in enumerate(response.citations, start=1):
        page_text = f", p.{citation.page}" if citation.page is not None else ""
        lines.append(f"{index}. {citation.title}{page_text}")
        if citation.official_source_id:
            official_page_text = (
                f", p.{citation.official_source_page}"
                if citation.official_source_page is not None
                else ""
            )
            lines.append("   - 원문: `" + citation.official_source_id + "`" + official_page_text)
    return "\n".join(lines)


def format_metadata(response: ChatResponse) -> str:
    lines = [
        f"- route: {response.route}",
        f"- retrieval_attempts: {response.retrieval_attempts}",
        f"- retry_reason: {response.retrieval_retry_reason or '없음'}",
        f"- drug_status: {response.drug_status or '없음'}",
        f"- pharmacology_status: {response.pharmacology_status or '없음'}",
        f"- errors: {len(response.errors)}",
    ]
    if response.errors:
        lines.append("")
        lines.extend(f"  - {error}" for error in response.errors)
    return "\n".join(lines)


def format_product_candidate_choices(response: ChatResponse) -> list[tuple[str, str]]:
    return [
        (format_product_candidate_label(candidate), candidate.name)
        for candidate in response.product_candidates
    ]


def format_product_candidate_label(candidate: DrugCandidateSummary) -> str:
    parts = [candidate.name]
    if candidate.ingredient_names:
        parts.append(", ".join(candidate.ingredient_names))
    if candidate.manufacturer:
        parts.append(candidate.manufacturer)
    return " | ".join(parts)


def build_selected_product_request(query: str, candidate: DrugCandidateSummary) -> ChatRequest:
    return ChatRequest(
        query=query.strip(),
        product_name=candidate.name,
        drug_code=candidate.drug_code,
    )


def format_drug_detail_card(detail: KADADrugDetail | None) -> str:
    if detail is None:
        return ""

    ingredient_text = ", ".join(escape(ingredient) for ingredient in detail.ingredients) or "KADA 상세정보 미제공"
    dosage_text = escape(detail.dosage or "KADA 상세정보 미제공")
    notice_html = format_doping_notices(detail.doping_notices)
    image_html = format_drug_images(detail)
    return f"""
<section class="drug-card">
  <div class="drug-card__header">
    <p>KADA 금지약물 검색 결과</p>
    <h2>{escape(detail.product_name)}</h2>
  </div>
  <div class="drug-card__availability">
    <div>{format_kada_status("경기기간 중", detail.in_competition_status)}</div>
    <div>{format_kada_status("경기기간 외", detail.out_of_competition_status)}</div>
  </div>
  <dl class="drug-card__details">
    <div><dt>성분</dt><dd>{ingredient_text}</dd></div>
    <div><dt>복용법 · 용량</dt><dd>{dosage_text}</dd></div>
  </dl>
  {notice_html}
  {image_html}
</section>
""".strip()


def format_kada_status(period: str, status: str | None) -> str:
    status_text = status or "KADA 상세정보 미제공"
    status_class = {
        "금지": "prohibited",
        "정보확인": "check",
    }.get(status_text, "allowed")
    return (
        f'<strong class="drug-card__status drug-card__status--{status_class}">'
        f"{escape(period)}: {escape(status_text)}</strong>"
    )


def format_doping_notices(notices: list[str]) -> str:
    if not notices:
        return ""
    body = "<br>".join(escape(notice) for notice in notices)
    return f"""
  <section class="drug-card__notice">
    <h3>정보확인</h3>
    <p>{body}</p>
  </section>
""".strip()


def format_drug_images(detail: KADADrugDetail) -> str:
    images: list[str] = []
    if detail.pill_image_url:
        images.append(
            f'<figure><img src="{escape(detail.pill_image_url, quote=True)}" alt="약제형 이미지"><figcaption>약제형</figcaption></figure>'
        )
    if detail.package_image_url:
        images.append(
            f'<figure><img src="{escape(detail.package_image_url, quote=True)}" alt="포장 이미지"><figcaption>포장</figcaption></figure>'
        )
    if not images:
        return ""
    return '<div class="drug-card__images">' + "".join(images) + "</div>"


def format_product_pharmacology_card(response: ChatResponse) -> str:
    if response.drug_detail is None or response.pharmacology_status is None:
        return ""

    if response.pharmacology_status != "found" or not response.pharmacology_ingredients:
        return """
<section class="drug-card__pharmacology drug-card__pharmacology--missing">
  <h3>성분별 반감기 참고</h3>
  <p>현재 등록된 성분별 반감기 근거가 없습니다.</p>
  <p>반감기 정보가 없다는 뜻이 복용 가능하다는 뜻은 아닙니다. 제품 성분표와 KADA 검색 결과를 팀 닥터, 약사 또는 도핑 담당자와 확인하세요.</p>
</section>
""".strip()

    items = []
    for ingredient in response.pharmacology_ingredients:
        typical_range = escape(ingredient.typical_range or "현재 등록된 일반적 범위 없음")
        wider_range = (
            f"<p>변동 가능 범위: {escape(ingredient.wider_range)}</p>"
            if ingredient.wider_range
            else ""
        )
        items.append(
            f"""
  <article class="drug-card__pharmacology-item">
    <h4>{escape(ingredient.substance_name)}</h4>
    <p>일반적 반감기 참고: {typical_range}</p>
    {wider_range}
  </article>
""".strip()
        )

    return f"""
<section class="drug-card__pharmacology">
  <h3>성분별 반감기 참고</h3>
  {''.join(items)}
  <p class="drug-card__pharmacology-caveat">반감기는 참고용이며 도핑검사 검출 가능 시간이나 출전 가능 여부를 확정하지 않습니다.</p>
</section>
""".strip()


def format_selected_product_card(response: ChatResponse) -> str:
    return "\n".join(
        part
        for part in [
            format_drug_detail_card(response.drug_detail),
            format_product_pharmacology_card(response),
        ]
        if part
    )


def format_answer_for_ui(response: ChatResponse) -> str:
    if response.herbal_verification_unavailable:
        return """
## KADA 정보확인
- **생약성분 포함 의약품 금지여부 확인 불가**
- KADA 금지약물 검색서비스는 생약성분 및 생약성분을 원료로 하는 의약품의 금지여부를 제공하지 않습니다.
- 이 결과를 허용으로 해석하지 말고, 사용 전 KADA 또는 도핑 담당자에게 확인하세요.
""".strip()

    # Product lookup is a focused KADA workflow. Show rules only when the user
    # asks a rules question without a selectable product or selected product card.
    if response.requires_product_selection and response.product_candidates:
        return ""
    if response.drug_detail is not None:
        return ""
    return response.answer


def candidate_to_state(candidate: DrugCandidateSummary) -> dict[str, Any]:
    return candidate.model_dump(mode="json")


def state_to_candidate(value: dict[str, Any]) -> DrugCandidateSummary:
    return DrugCandidateSummary.model_validate(value)


def product_button_updates(candidates: list[DrugCandidateSummary]) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    for index in range(MAX_PRODUCT_CANDIDATES):
        if index < len(candidates):
            updates.append(gr.update(value=candidates[index].name, visible=True))
        else:
            updates.append(gr.update(value="", visible=False))
    return updates


def response_to_ui_updates(response: ChatResponse):
    candidates = response.product_candidates[:MAX_PRODUCT_CANDIDATES]
    show_candidates = response.requires_product_selection and bool(candidates)
    return (
        format_answer_for_ui(response),
        [candidate_to_state(candidate) for candidate in candidates] if show_candidates else [],
        gr.update(
            value=format_selected_product_card(response),
            visible=response.drug_detail is not None,
        ),
        *product_button_updates(candidates if show_candidates else []),
    )


def respond(query: str, runner: ChatRunner = run_chat) -> tuple[str, str]:
    if not query.strip():
        return "질문을 입력해주세요.", ""

    response = runner(ChatRequest(query=query.strip()))
    return format_answer_for_ui(response), ""


def respond_for_initial_query(query: str, runner: ChatRunner = run_chat):
    if not query.strip():
        empty_response = ChatResponse(
            answer="질문을 입력해주세요.",
            route="rag",
            query="",
            engine="graph",
        )
        return response_to_ui_updates(empty_response)
    return response_to_ui_updates(runner(ChatRequest(query=query.strip())))


def respond_for_selected_candidate(
    query: str,
    candidate_state: list[dict[str, Any]],
    index: int,
    runner: ChatRunner = run_chat,
):
    if not query.strip():
        return respond_for_initial_query(query, runner=runner)
    if index >= len(candidate_state):
        return respond_for_initial_query(query, runner=runner)

    candidate = state_to_candidate(candidate_state[index])
    if not candidate.drug_code:
        return respond_for_initial_query(query, runner=runner)
    return response_to_ui_updates(runner(build_selected_product_request(query, candidate)))


def build_demo(runner: ChatRunner = run_chat) -> gr.Blocks:
    with gr.Blocks(title=DEFAULT_TITLE, css=DRUG_CARD_CSS) as demo:
        gr.Markdown(f"# {DEFAULT_TITLE}")
        gr.Markdown(DEFAULT_DESCRIPTION)

        query = gr.Textbox(
            label="질문",
            placeholder="예: 경기기간 중 스트랩실 먹어도 돼?",
            lines=4,
        )
        submit = gr.Button("답변 생성", variant="primary")
        candidate_state = gr.State([])
        gr.Markdown("### 정확한 제품을 선택하세요", visible=True)
        with gr.Row():
            candidate_buttons = [gr.Button(visible=False) for _ in range(MAX_PRODUCT_CANDIDATES)]
        drug_detail = gr.HTML(visible=False)
        answer = gr.Markdown(label="답변")

        outputs = [answer, candidate_state, drug_detail, *candidate_buttons]
        submit.click(
            fn=lambda user_query: respond_for_initial_query(user_query, runner=runner),
            inputs=[query],
            outputs=outputs,
        )
        query.submit(
            fn=lambda user_query: respond_for_initial_query(user_query, runner=runner),
            inputs=[query],
            outputs=outputs,
        )
        for index, button in enumerate(candidate_buttons):
            button.click(
                fn=lambda user_query, candidates, selected_index=index: respond_for_selected_candidate(
                    user_query,
                    candidates,
                    selected_index,
                    runner=runner,
                ),
                inputs=[query, candidate_state],
                outputs=outputs,
            )

    return demo


DRUG_CARD_CSS = """
.drug-card { border: 1px solid #d5dce6; border-radius: 8px; margin: 1rem 0; overflow: hidden; background: #fff; color: #152238; }
.drug-card__header { padding: 1rem 1.25rem; background: #075da8; color: #fff; }
.drug-card__header p { margin: 0 0 .25rem; font-size: .85rem; opacity: .85; }
.drug-card__header h2 { margin: 0; font-size: 1.2rem; }
.drug-card__availability { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px; background: #d5dce6; }
.drug-card__availability div { padding: 1rem; background: #f8fbff; display: grid; gap: .35rem; }
.drug-card__availability span { font-weight: 600; }
.drug-card__status { width: fit-content; padding: .2rem .6rem; border-radius: 4px; color: #fff; }
.drug-card__status--allowed { background: #1ea93b; }
.drug-card__status--prohibited { background: #d92d20; }
.drug-card__status--check { background: #b54708; }
.drug-card__details { margin: 0; }
.drug-card__details div { display: grid; grid-template-columns: 10rem 1fr; border-top: 1px solid #e3e8ef; }
.drug-card__details dt, .drug-card__details dd { padding: .9rem 1rem; margin: 0; }
.drug-card__details dt { background: #f5f7fa; font-weight: 600; }
.drug-card__details dd { background: #fff; color: #111827 !important; }
.drug-card__notice { padding: 1rem; background: #f3a62f; color: #111827; }
.drug-card__notice h3 { margin: 0 0 .4rem; font-size: 1rem; color: #111827; }
.drug-card__notice p { margin: 0; color: #111827; font-weight: 600; }
.drug-card__pharmacology { padding: 1rem; border-top: 1px solid #e3e8ef; background: #f7fbff; color: #111827; }
.drug-card__pharmacology--missing { background: #fff8ed; }
.drug-card__pharmacology h3 { margin: 0 0 .75rem; font-size: 1rem; color: #111827; }
.drug-card__pharmacology-item { border-top: 1px solid #dbe7f1; padding: .75rem 0; }
.drug-card__pharmacology-item:first-of-type { border-top: 0; padding-top: 0; }
.drug-card__pharmacology-item h4, .drug-card__pharmacology-item p, .drug-card__pharmacology-caveat { margin: .25rem 0; color: #111827; }
.drug-card__pharmacology-caveat { margin-top: .75rem; font-weight: 600; }
.drug-card__images { display: flex; flex-wrap: wrap; gap: 1rem; padding: 1rem; border-top: 1px solid #e3e8ef; }
.drug-card__images figure { margin: 0; width: min(260px, 100%); }
.drug-card__images img { width: 100%; max-height: 220px; object-fit: contain; background: #f5f7fa; }
.drug-card__images figcaption { margin-top: .35rem; color: #52606d; font-size: .85rem; }
@media (max-width: 640px) { .drug-card__availability { grid-template-columns: 1fr; } .drug-card__details div { grid-template-columns: 1fr; } .drug-card__details dt { padding-bottom: .25rem; } .drug-card__details dd { padding-top: .25rem; } }
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-name", default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=7860)
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()

    demo = build_demo()
    demo.launch(
        server_name=args.server_name,
        server_port=args.server_port,
        share=args.share,
    )


if __name__ == "__main__":
    main()
