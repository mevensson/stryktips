"""Shared CLI test harness for injecting dependencies through the public seam."""

from flexmock import flexmock

import stryktips.core as stryktips_core
from stryktips.dependencies import Dependencies


def run_main(dependencies: Dependencies, argv: list[str]) -> int:
    """Run the CLI with dependencies injected through the public composition seam."""
    flexmock(stryktips_core, create_dependencies=lambda: dependencies)
    return stryktips_core.main(argv)
