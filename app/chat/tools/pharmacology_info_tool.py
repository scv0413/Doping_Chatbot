from collections.abc import Callable

from app.chat.pharmacology.schemas import PharmacologyInfoResult
from app.chat.pharmacology.service import search_pharmacology_info
from app.chat.tools.schemas import PharmacologyInfoToolOutput, PharmacologyInfoToolRequest, ToolError

PharmacologySearcher = Callable[[str], PharmacologyInfoResult]


def run_pharmacology_info_tool(
    request: PharmacologyInfoToolRequest,
    pharmacology_searcher: PharmacologySearcher = search_pharmacology_info,
) -> PharmacologyInfoToolOutput:
    try:
        result = pharmacology_searcher(request.query)
    except Exception as exc:
        return PharmacologyInfoToolOutput(
            query=request.query,
            request_id=request.request_id,
            errors=[
                ToolError(
                    stage="pharmacology_info",
                    message=str(exc),
                    error_type=type(exc).__name__,
                )
            ],
        )

    return PharmacologyInfoToolOutput(
        query=request.query,
        result=result,
        request_id=request.request_id,
    )
