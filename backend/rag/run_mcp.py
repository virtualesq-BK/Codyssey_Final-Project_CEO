"""Claude Desktop 등에서 실행할 MCP 진입점 (작업 폴더와 무관하게 동작)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bizrag.mcp_server import main  # noqa: E402

main()
