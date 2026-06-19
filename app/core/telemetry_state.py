from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TelemetryState:
    api_version: str = "--"
    armed: bool = False
    angle_mode: bool = False
    nav_mode: int = 0
    flight_mode: str = "MANUAL"
    gps_fix: int = 0
    satellites: int = 0
    lat: float = 0.0
    lon: float = 0.0
    altitude_m: float = 0.0
    speed_ms: float = 0.0
    hdop: float = 0.0
    heading_deg: float = 0.0
    voltage: float = 0.0
    link_quality: int = 0
    link_latency_ms: float = 0.0
    home_lat: float = 0.0
    home_lon: float = 0.0
    home_set: bool = False

    def update_flight_mode(self) -> None:
        if self.nav_mode == 0:
            self.flight_mode = "ANGLE" if self.angle_mode else "ACRO"
        elif self.nav_mode == 1:
            self.flight_mode = "POSHOLD"
        elif self.nav_mode == 2:
            self.flight_mode = "RTH"
        elif self.nav_mode == 3:
            self.flight_mode = "CRUISE"
        else:
            self.flight_mode = f"NAV:{self.nav_mode}"

    def maybe_set_home(self) -> bool:
        if self.armed and not self.home_set and self.satellites >= 6 and self.lat and self.lon:
            self.home_lat = self.lat
            self.home_lon = self.lon
            self.home_set = True
            return True
        return False
