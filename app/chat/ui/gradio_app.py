import argparse
from collections.abc import Callable

import gradio as gr

from app.chat.runtime import ChatEngine, ChatRequest, ChatResponse, run_chat

DEFAULT_TITLE = "KADA/WADA 도핑 정보 챗봇"
DEFAULT_DESCRIPTION = (
    "선수와 트레이너를 위한 근거 기반 도핑 정보 확인 도구입니다. "
    "공식 판정을 대체하지 않으며, 약물 사용 전 제품명과 성분명을 반드시 확인하세요."
)

ChatRunner = Callable[[ChatRequest], ChatResponse]


def format_citations(response: ChatResponse) -> str:
    if not response.citations:
        return "검색된 문서 근거가 없습니다."

    lines = []
    for index, citation in enumerate(response.citations, start=1):
        page_text = f", p.{citation.page}" if citation.page is not None else ""
        lines.append(
            f"{index}. {citation.title}{page_text} | `{citation.chunk_id}` | distance={citation.distance:.4f}"
        )
    return "\n".join(lines)


def format_metadata(response: ChatResponse) -> str:
    lines = [
        f"- route: `{response.route}`",
        f"- retrieval_attempts: `{response.retrieval_attempts}`",
        f"- retry_reason: `{response.retrieval_retry_reason or '없음'}`",
        f"- drug_status: `{response.drug_status or '없음'}`",
        f"- pharmacology_status: `{response.pharmacology_status or '없음'}`",
        f"- errors: `{len(response.errors)}`",
    ]
    if response.errors:
        lines.append("")
        lines.extend(f"  - {error}" for error in response.errors)
    return "\n".join(lines)


def respond(
    query: str,
    top_k: int | None = None,
    use_llm: bool | None = None,
    engine: str | None = None,
    runner: ChatRunner = run_chat,
) -> tuple[str, str]:
    if not query.strip():
        return "질문을 입력해주세요.", ""

    response = runner(
        ChatRequest(
            query=query.strip(),
            top_k=int(top_k) if top_k is not None else None,
            use_llm=use_llm,
            engine=ChatEngine(engine) if engine else None,
        )
    )
    return response.answer, format_citations(response)


def build_demo(runner: ChatRunner = run_chat) -> gr.Blocks:
    with gr.Blocks(title=DEFAULT_TITLE) as demo:
        gr.Markdown(f"# {DEFAULT_TITLE}")
        gr.Markdown(DEFAULT_DESCRIPTION)

        query = gr.Textbox(
            label="질문",
            placeholder="예: 경기기간 중 코감기약을 비강 스프레이로 써도 돼?",
            lines=4,
        )

        submit = gr.Button("답변 생성", variant="primary")

        answer = gr.Markdown(label="답변")
        citations = gr.Markdown(label="근거")
        submit.click(
            fn=lambda user_query: respond(user_query, runner=runner),
            inputs=[query],
            outputs=[answer, citations],
        )

        query.submit(
            fn=lambda user_query: respond(user_query, runner=runner),
            inputs=[query],
            outputs=[answer, citations],
        )

    return demo


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
