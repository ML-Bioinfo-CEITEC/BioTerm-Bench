from __future__ import annotations

import math

from scripts.analyze_preirt_selection import logistic_slope
from scripts.preirt_common import assert_frozen_tasks, load_panel


def test_frozen_manifest_and_panel_sizes() -> None:
    assert len(assert_frozen_tasks()) == 113
    panel = load_panel()
    assert len(panel) == 10
    assert {row["provider"] for row in panel} == {"openrouter", "einfra"}


def test_logistic_slope_sign_tracks_ability() -> None:
    theta = [-2, -1, 0, 1, 2]
    assert logistic_slope(theta, [0, 0, 0, 1, 1], [1] * 5) > 0
    assert logistic_slope(theta, [1, 1, 0, 0, 0], [1] * 5) < 0


def test_logistic_slope_is_missing_at_floor_or_ceiling() -> None:
    assert math.isnan(logistic_slope([-1, 0, 1], [0, 0, 0], [1, 1, 1]))
    assert math.isnan(logistic_slope([-1, 0, 1], [1, 1, 1], [1, 1, 1]))
