from dataclasses import dataclass
from typing import List

@dataclass
class BatteryDispatchOutput:
    actual_power_w : float | None = None
    state_of_charge_wh : float | None = None

