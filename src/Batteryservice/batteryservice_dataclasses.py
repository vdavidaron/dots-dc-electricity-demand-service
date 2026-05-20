from dataclasses import dataclass
from typing import List

@dataclass
class DailyDegradationOutput:
    health_capacity_degradation : float | None = None

@dataclass
class BatteryDispatchOutput:
    bess_power_w : float | None = None
    state_of_charge : float | None = None
    max_available_charge : float | None = None
    max_available_discharge : float | None = None

