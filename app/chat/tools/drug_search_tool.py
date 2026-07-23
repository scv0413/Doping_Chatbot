from collections.abc import Callable

from app.chat.domain.drug_search.kada_client import search_kada_drugs
from app.chat.domain.drug_search.schemas import DrugSearchInput, DrugSearchResult
from app.chat.tools.schemas import DrugSearchToolOutput, DrugSearchToolRequest, ToolError

DrugSearcher = Callable[[DrugSearchInput], DrugSearchResult]


def run_drug_search_tool(
    request: DrugSearchToolRequest,
    drug_searcher: DrugSearcher = search_kada_drugs,
) -> DrugSearchToolOutput:
    search_input = request_to_drug_search_input(request)

    try:
        result = drug_searcher(search_input)
    except Exception as exc:
        return DrugSearchToolOutput(
            query=request.query,
            request_id=request.request_id,
            errors=[
                ToolError(
                    stage="drug_search",
                    message=str(exc),
                    error_type=type(exc).__name__,
                )
            ],
        )

    return DrugSearchToolOutput(
        query=request.query,
        result=result,
        request_id=request.request_id,
    )


def request_to_drug_search_input(request: DrugSearchToolRequest) -> DrugSearchInput:
    return DrugSearchInput(
        query=request.query,
        product_name=request.product_name,
        ingredient_name=request.ingredient_name,
        competition_period=request.competition_period,
        route=request.route,
        sport=request.sport,
        dose=request.dose,
        drug_code=request.drug_code,
    )
