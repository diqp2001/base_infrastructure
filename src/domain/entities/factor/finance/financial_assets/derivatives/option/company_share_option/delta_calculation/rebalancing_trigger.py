from enum import Enum


class RebalancingTrigger(Enum):
    """Trigger strategy for VolForecastTriggeredBSDelta.

    MEDIAN       – hedge when forecast vol exceeds the rolling median of prior forecasts.
    PERCENTILE_90 – hedge when forecast vol exceeds the 90th-percentile of prior forecasts.
    TREND        – hedge when forecast vol is rising (current > previous).
    """

    MEDIAN = "median"
    PERCENTILE_90 = "percentile_90"
    TREND = "trend"
