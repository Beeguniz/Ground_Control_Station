from __future__ import annotations

from dataclasses import dataclass

from app.mission.mission_model import MissionItem


@dataclass
class MissionValidation:
    wp: int
    level: str
    message: str


def validate_mission(mission: list[MissionItem]) -> list[MissionValidation]:
    results: list[MissionValidation] = []
    rth_count = 0
    poi_count = 0
    jump_seen = False
    rth_seen = False

    for index, item in enumerate(mission):
        if item.type == "POI":
            poi_count += 1

        if item.alt <= 0:
            results.append(MissionValidation(item.id, "error", "Altitude must be > 0"))

        if item.type == "LAND" and index != len(mission) - 1:
            results.append(MissionValidation(item.id, "error", "LAND must be last"))

        for action in item.actions:
            if action.type == "SET_HEAD" and action.p1 != -1 and not 0 <= action.p1 <= 360:
                results.append(MissionValidation(item.id, "error", "SET_HEAD heading must be -1 or 0-360"))

            if action.type == "RTH":
                rth_count += 1
                rth_seen = True
                if index == 0:
                    results.append(MissionValidation(item.id, "error", "First waypoint cannot contain RTH"))
                if jump_seen:
                    results.append(MissionValidation(item.id, "error", "RTH cannot appear after JUMP"))

            if action.type == "JUMP":
                jump_seen = True
                if rth_seen:
                    results.append(MissionValidation(item.id, "error", "JUMP cannot appear after RTH"))
                if action.p1 < 1 or action.p1 > len(mission):
                    results.append(MissionValidation(item.id, "error", "JUMP target waypoint invalid"))
                if action.p1 == item.id:
                    results.append(MissionValidation(item.id, "error", "JUMP cannot target itself"))
                if action.p2 != -1 and action.p2 < 1:
                    results.append(MissionValidation(item.id, "error", "JUMP repeat must be -1 or >= 1"))

    if poi_count > 1:
        results.append(MissionValidation(-1, "error", "Only one POI allowed"))

    if rth_count > 1:
        results.append(MissionValidation(-1, "error", "Only one RTH allowed"))

    if mission:
        last = mission[-1]
        has_end = last.type == "LAND" or any(action.type == "RTH" for action in last.actions)
        if not has_end:
            results.append(MissionValidation(-1, "warning", "Mission should end with LAND or RTH"))

    return results
