from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.dom import minidom
from dataclasses import dataclass, field
from typing import Literal

StepType = Literal[
    "Warmup", "Cooldown", "SteadyState", "Intervals", "FreeRide"
]


@dataclass
class WorkoutStep:
    type: StepType
    duration: int = 0  # seconds
    power: float | None = None
    power_low: float | None = None
    power_high: float | None = None
    cadence: int | None = None
    cadence_low: int | None = None
    cadence_high: int | None = None
    repeat: int = 1
    on_steps: list[WorkoutStep] = field(default_factory=list)
    off_steps: list[WorkoutStep] = field(default_factory=list)
    text: str = ""
    text_off: str = ""

    def total_duration(self) -> int:
        if self.type == "Intervals":
            on_dur = sum(s.duration for s in self.on_steps)
            off_dur = sum(s.duration for s in self.off_steps)
            return self.repeat * (on_dur + off_dur)
        return self.duration


@dataclass
class Workout:
    name: str
    description: str
    author: str = "Karoo Training Generator"
    sport_type: str = "bike"
    tags: list[str] = field(default_factory=list)
    steps: list[WorkoutStep] = field(default_factory=list)

    def total_duration(self) -> int:
        return sum(s.total_duration() for s in self.steps)


class ZWOGenerator:
    @staticmethod
    def generate(workout: Workout) -> str:
        root = ET.Element("workout_file")
        ET.SubElement(root, "name").text = workout.name
        ET.SubElement(root, "description").text = workout.description
        ET.SubElement(root, "author").text = workout.author
        ET.SubElement(root, "sportType").text = workout.sport_type

        tags_el = ET.SubElement(root, "tags")
        for tag in workout.tags:
            ET.SubElement(tags_el, "tag", name=tag)

        workout_el = ET.SubElement(root, "workout")
        for step in workout.steps:
            ZWOGenerator._add_step(workout_el, step)

        rough = ET.tostring(root, encoding="unicode")
        parsed = minidom.parseString(rough)
        return parsed.toprettyxml(indent="  ", encoding=None)

    @staticmethod
    def _add_step(parent: ET.Element, step: WorkoutStep) -> None:
        if step.type == "Intervals":
            intervals_el = ET.SubElement(
                parent, "Intervals", Repeat=str(step.repeat)
            )
            for on_step in step.on_steps:
                ZWOGenerator._add_simple_step(intervals_el, on_step, "On")
            for off_step in step.off_steps:
                ZWOGenerator._add_simple_step(intervals_el, off_step, "Off")
        else:
            ZWOGenerator._add_simple_step(parent, step, step.type)

    @staticmethod
    def _add_simple_step(
        parent: ET.Element, step: WorkoutStep, tag: str
    ) -> None:
        attrs: dict[str, str] = {"Duration": str(step.duration)}

        if step.power is not None:
            attrs["Power"] = f"{step.power:.2f}"
        if step.power_low is not None:
            attrs["PowerLow"] = f"{step.power_low:.2f}"
        if step.power_high is not None:
            attrs["PowerHigh"] = f"{step.power_high:.2f}"
        if step.cadence is not None:
            attrs["Cadence"] = str(step.cadence)
        if step.cadence_low is not None:
            attrs["CadenceLow"] = str(step.cadence_low)
        if step.cadence_high is not None:
            attrs["CadenceHigh"] = str(step.cadence_high)

        el = ET.SubElement(parent, tag, **attrs)

        if step.text:
            ET.SubElement(el, "text", seconds="0").text = step.text
        if step.text_off:
            ET.SubElement(el, "textOff", seconds="0").text = step.text_off
