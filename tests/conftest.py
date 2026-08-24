import sys
from pathlib import Path
from typing import Any

import pytest

# Add the project root to sys.path so that stryktips can be imported
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_response():
    """Return a factory that stubs a requests response body."""
    from flexmock import flexmock

    def _make(data: Any, status_code: int = 200) -> Any:
        mock = flexmock(status_code=status_code)
        mock.should_receive("json").and_return(data)
        mock.should_receive("raise_for_status").and_return(None)
        return mock

    return _make
