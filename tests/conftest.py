from collections.abc import Callable
from time import monotonic, sleep

import pytest


@pytest.fixture
def wait_until():
    """Wait for a condition, allowing for delayed scheduling on CI runners."""
    
    def wait(
        predicate: Callable[[], bool],
        timeout: float = 2.0,
        interval: float = 0.005,
    ) -> None:
        deadline = monotonic() + timeout

        while monotonic() < deadline:
            if predicate():
                return
            sleep(interval)

        assert predicate(), f"Condition was not met within {timeout} seconds"

    return wait
