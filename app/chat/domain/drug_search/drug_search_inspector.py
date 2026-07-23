from app.chat.domain.drug_search.formatter import format_drug_search_answer
from app.chat.domain.drug_search.kada_client import search_kada_drugs
from app.chat.domain.drug_search.schemas import CompetitionPeriod, DrugCandidate, DrugSearchInput


TEST_INPUTS = [
    DrugSearchInput(
        query="타이레놀 먹어도 돼?",
        product_name="타이레놀",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    ),
    DrugSearchInput(
        query="아세트아미노펜 경기기간 중 괜찮아?",
        ingredient_name="아세트아미노펜",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    ),
    DrugSearchInput(
        query="슈도에페드린 경기기간 중 먹어도 돼?",
        ingredient_name="슈도에페드린",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    ),
    DrugSearchInput(
        query="슈도에페드린 경기기간 외에 먹어도 돼?",
        ingredient_name="슈도에페드린",
        competition_period=CompetitionPeriod.OUT_OF_COMPETITION,
    ),
    DrugSearchInput(
        query="테스토스테론 사용해도 돼?",
        ingredient_name="테스토스테론",
        competition_period=CompetitionPeriod.OUT_OF_COMPETITION,
    ),
    DrugSearchInput(
        query="분사형 코감기약은 금지약물이야?",
        product_name="코감기약",
        competition_period=CompetitionPeriod.IN_COMPETITION,
    ),
    DrugSearchInput(query="알 수 없는 약"),
]


def inspect_drug_searches(
    page_size: int = 5,
    candidate_limit: int = 5,
    show_formatted_answer: bool = True,
) -> None:
    for search_input in TEST_INPUTS:
        print("#" * 100)
        print(f"QUERY: {search_input.query}")
        print(
            "INPUT: "
            f"product_name={search_input.product_name} "
            f"ingredient_name={search_input.ingredient_name} "
            f"competition_period={search_input.competition_period} "
            f"route={search_input.route} "
            f"sport={search_input.sport} "
            f"dose={search_input.dose}"
        )

        try:
            result = search_kada_drugs(search_input=search_input, page_size=page_size)
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")
            continue

        print("-" * 80)
        print(f"STATUS: {result.status}")
        print(f"MATCHED SUBSTANCES: {result.matched_substances}")
        print(f"PROHIBITED CATEGORIES: {result.prohibited_categories}")
        print(f"requires_product_selection: {result.requires_product_selection}")
        print(f"requires_route_confirmation: {result.requires_route_confirmation}")
        print(f"requires_sport_confirmation: {result.requires_sport_confirmation}")
        print(f"requires_dose_confirmation: {result.requires_dose_confirmation}")
        print(f"RECOMMENDED ACTION: {result.recommended_action}")
        print("CANDIDATES:")

        for idx, candidate in enumerate(result.matched_candidates[:candidate_limit], start=1):
            print(format_candidate(idx, candidate))

        if len(result.matched_candidates) > candidate_limit:
            print(f"... and {len(result.matched_candidates) - candidate_limit} more candidates")

        print("NOTES:")
        for note in result.notes:
            print(f"- {note}")

        if show_formatted_answer:
            print("-" * 80)
            print("FORMATTED ANSWER:")
            print(format_drug_search_answer(result, candidate_limit=candidate_limit))


def format_candidate(idx: int, candidate: DrugCandidate) -> str:
    ingredient_text = ", ".join(candidate.ingredient_names) or "-"
    manufacturer = candidate.manufacturer or "-"
    return (
        f"{idx}. [{candidate.match_type}] {candidate.name} | "
        f"ingredients={ingredient_text} | manufacturer={manufacturer}"
    )


if __name__ == "__main__":
    inspect_drug_searches()
