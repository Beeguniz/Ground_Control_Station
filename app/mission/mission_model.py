from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


MissionType = Literal["WAYPOINT", "PH_TIME", "POI", "LAND", "SET_HEAD", "JUMP", "RTH"]
ActionType = Literal["SET_HEAD", "JUMP", "RTH"]


@dataclass
class MissionAction:
    type: ActionType = "SET_HEAD"
    p1: int = 0
    p2: int = 0
    p3: int = 0


@dataclass
class MissionItem:
    id: int
    lat: float
    lon: float
    alt: float = 50.0
    type: MissionType = "WAYPOINT"
    p1: int = 0
    p2: int = 0
    p3: int = 0
    flag: int = 0
    actions: list[MissionAction] = field(default_factory=list)


NAV_TYPES = {"WAYPOINT", "PH_TIME", "POI", "LAND"}
ACTION_TYPES = {"SET_HEAD", "JUMP", "RTH"}


def renumber(mission: list[MissionItem]) -> None:
    for index, item in enumerate(mission, start=1):
        item.id = index


def flatten_mission(mission: list[MissionItem]) -> list[MissionItem]:
    flat: list[MissionItem] = []

    for item in mission:
        flat.append(
            MissionItem(
                id=len(flat) + 1,
                lat=item.lat,
                lon=item.lon,
                alt=item.alt,
                type=item.type,
                p1=item.p1,
                p2=item.p2,
                p3=item.p3,
                flag=item.flag,
            )
        )

        for action in item.actions:
            flat.append(
                MissionItem(
                    id=len(flat) + 1,
                    lat=0,
                    lon=0,
                    alt=0,
                    type=action.type,
                    p1=action.p1,
                    p2=action.p2,
                    p3=action.p3,
                    flag=0,
                )
            )

    return flat


def decode_action_code(code: int) -> MissionType:
    return {
        1: "WAYPOINT",
        3: "PH_TIME",
        4: "RTH",
        5: "POI",
        6: "JUMP",
        7: "SET_HEAD",
        8: "LAND",
    }.get(code, "WAYPOINT")


def encode_action_type(action_type: MissionType) -> int:
    return {
        "WAYPOINT": 1,
        "PH_TIME": 3,
        "RTH": 4,
        "POI": 5,
        "JUMP": 6,
        "SET_HEAD": 7,
        "LAND": 8,
    }.get(action_type, 1)
