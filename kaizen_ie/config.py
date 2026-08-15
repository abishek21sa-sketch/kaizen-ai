from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class IEAssumptions:
    """Transparent operating assumptions used by the V0.3 IE layer.

    These are not hidden-factory causal inputs. They are planning parameters that a real
    plant would normally source from demand and schedule systems.
    """

    gross_shift_minutes: float = 480.0
    planned_break_minutes: float = 30.0
    customer_demand_units_per_shift: int = 600
    resources_per_station: int = 1

    @property
    def net_available_seconds_per_shift(self) -> float:
        return (self.gross_shift_minutes - self.planned_break_minutes) * 60.0

    @property
    def takt_seconds_per_unit(self) -> float:
        return self.net_available_seconds_per_shift / self.customer_demand_units_per_shift

    @property
    def required_rate_units_per_hour(self) -> float:
        return 3600.0 / self.takt_seconds_per_unit

    def to_dict(self) -> dict[str, float | int]:
        data = asdict(self)
        data.update(
            {
                "net_available_seconds_per_shift": self.net_available_seconds_per_shift,
                "takt_seconds_per_unit": self.takt_seconds_per_unit,
                "required_rate_units_per_hour": self.required_rate_units_per_hour,
            }
        )
        return data


DEFAULT_IE_ASSUMPTIONS = IEAssumptions()
