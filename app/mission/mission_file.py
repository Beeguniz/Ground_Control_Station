from __future__ import annotations

import xml.etree.ElementTree as ET

from app.mission.mission_model import ACTION_TYPES, NAV_TYPES, MissionAction, MissionItem, renumber


def build_mission_xml(mission: list[MissionItem]) -> str:
    if not mission:
        return ""

    avg_lat = sum(item.lat for item in mission) / len(mission)
    avg_lon = sum(item.lon for item in mission) / len(mission)

    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        "<mission>",
        '\t<version value="2.3-pre8"/>',
        f'\t<mwp cx="{avg_lon:.7f}" cy="{avg_lat:.7f}" home-x="0" home-y="0" zoom="16"/>',
    ]

    counter = 1
    item_lines: list[str] = []

    for item in mission:
        action = "SET_POI" if item.type == "POI" else item.type
        item_lines.append(
            f'\t<missionitem no="{counter}" action="{action}" lat="{item.lat:.7f}" lon="{item.lon:.7f}" '
            f'alt="{item.alt}" parameter1="{item.p1}" parameter2="{item.p2}" parameter3="{item.p3}" flag="0" />'
        )
        counter += 1

        for mission_action in item.actions:
            item_lines.append(
                f'\t<missionitem no="{counter}" action="{mission_action.type}" lat="0" lon="0" alt="0" '
                f'parameter1="{mission_action.p1}" parameter2="{mission_action.p2}" '
                f'parameter3="{mission_action.p3}" flag="0" />'
            )
            counter += 1

    if item_lines:
        item_lines[-1] = item_lines[-1].replace('flag="0"', 'flag="165"')

    lines.extend(item_lines)
    lines.append("</mission>")
    return "\n".join(lines)


def parse_mission_xml(xml_text: str) -> list[MissionItem]:
    root = ET.fromstring(xml_text)
    mission: list[MissionItem] = []
    current: MissionItem | None = None

    for node in root.findall("missionitem"):
        action = node.attrib.get("action", "")
        item_type = "POI" if action == "SET_POI" else action
        lat = float(node.attrib.get("lat", 0))
        lon = float(node.attrib.get("lon", 0))
        alt = float(node.attrib.get("alt", 0))
        p1 = int(float(node.attrib.get("parameter1", 0)))
        p2 = int(float(node.attrib.get("parameter2", 0)))
        p3 = int(float(node.attrib.get("parameter3", 0)))
        flag = int(float(node.attrib.get("flag", 0)))

        if item_type in NAV_TYPES:
            current = MissionItem(
                id=len(mission) + 1,
                lat=lat,
                lon=lon,
                alt=alt,
                type=item_type,  # type: ignore[arg-type]
                p1=p1,
                p2=p2,
                p3=p3,
                flag=flag,
            )
            mission.append(current)
            continue

        if item_type in ACTION_TYPES and current:
            current.actions.append(
                MissionAction(
                    type=item_type,  # type: ignore[arg-type]
                    p1=p1,
                    p2=p2,
                    p3=p3,
                )
            )

    renumber(mission)
    return mission
