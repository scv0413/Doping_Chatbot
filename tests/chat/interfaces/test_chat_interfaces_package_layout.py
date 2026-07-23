from app.chat.interfaces.api.main import create_app
from app.chat.interfaces.mcp.fastmcp_server import create_mcp_server
from app.chat.interfaces.ui.gradio_app import build_demo


def test_interfaces_are_importable() -> None:
    assert create_app
    assert create_mcp_server
    assert build_demo
