"""Offline, silent screen-recording condensation based on visual activity.

This is a standalone utility, not part of the EvoMAV runtime. Frame differences
estimate activity, not semantic importance. Input timing uses the reported FPS.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class Analysis:
    """Measured source timeline; frame count comes from decoding to EOF."""

    fps: float
    frames: int
    width: int
    height: int
    starts: NDArray[np.int64]
    changes: NDArray[np.float64]


@dataclass(frozen=True)
class Plan:
    """Monotonic source-to-output mapping, including the final source endpoint."""

    source_edges: NDArray[np.float64]
    output_edges: NDArray[np.float64]
    selected_frames: NDArray[np.int64]
    fps: int


def open_video(path: Path) -> cv2.VideoCapture:
    """Reject unreadable inputs before creating an output."""
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        raise ValueError(f"Cannot open video: {path}")
    return capture


def frame_change(frame: NDArray[np.uint8], previous: NDArray[np.uint8] | None) -> float:
    """Ignore minor codec noise; small pointer motion may still go undetected."""
    if previous is None:
        return 0.0
    return float(np.mean(cv2.absdiff(frame, previous) > 18))


def analyze(path: Path) -> Analysis:
    """Sample twice per second while scanning sequentially to avoid seek errors."""
    capture = open_video(path)
    starts: list[int] = []
    changes: list[float] = []
    previous = None
    count = 0
    width = height = 0
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        if not math.isfinite(fps) or not 0 < fps <= 1000:
            raise ValueError("Source FPS is invalid; convert to constant FPS first.")
        step = max(1, round(fps / 2))
        while capture.grab():
            if count % step == 0:
                ok, frame = capture.retrieve()
                if not ok:
                    raise ValueError(f"Cannot decode frame {count}.")
                height, width = frame.shape[:2]
                gray = cv2.cvtColor(cv2.resize(frame, (320, 180)), cv2.COLOR_BGR2GRAY)
                starts.append(count)
                changes.append(frame_change(gray, previous))
                previous = gray
            count += 1
            if count % max(1, round(fps * 60)) == 0:
                print(f"  Analyzed {count / fps:.0f} seconds", flush=True)
    finally:
        capture.release()
    if not count or min(width, height) < 2:
        raise ValueError("No usable video frames found.")
    return Analysis(fps, count, width, height, np.array(starts), np.array(changes))


def activity_weights(analysis: Analysis, threshold: float) -> NDArray[np.float64]:
    """Keep context around changes and extra viewing time at both endpoints."""
    starts = analysis.starts / analysis.fps
    weights = np.full(len(starts), 0.06)
    for index in np.flatnonzero(analysis.changes >= threshold):
        when = starts[index]
        nearby = (starts >= when - 1.0) & (starts <= when + 1.5)
        weights[nearby] = 1.0
    weights[(starts < 2.0) | (starts >= analysis.frames / analysis.fps - 3.0)] = 2.0
    return weights


def allocate_time(
    durations: NDArray[np.float64], weights: NDArray[np.float64], target: float
) -> NDArray[np.float64]:
    """Distribute a fixed budget without slowing any interval below real time."""
    if target >= float(durations.sum()):
        return durations.copy()
    low, high = 0.0, 1.0 / float(weights.min())
    for _ in range(80):
        middle = (low + high) / 2
        allotted = durations * np.minimum(1.0, weights * middle)
        if float(allotted.sum()) < target:
            low = middle
        else:
            high = middle
    return durations * np.minimum(1.0, weights * high)


def make_plan(analysis: Analysis, seconds: float, fps: int, threshold: float) -> Plan:
    """Choose output frames chronologically; exact duration is rounded to a frame."""
    edges = np.append(analysis.starts / analysis.fps, analysis.frames / analysis.fps)
    output_count = max(1, round(min(seconds, float(edges[-1])) * fps))
    target = min(output_count / fps, float(edges[-1]))
    allotted = allocate_time(np.diff(edges), activity_weights(analysis, threshold), target)
    output_edges = np.concatenate(([0.0], np.cumsum(allotted)))
    output_times = (np.arange(output_count) + 0.5) * target / output_count
    source_times = np.interp(output_times, output_edges, edges)
    selected = np.clip((source_times * analysis.fps).astype(np.int64), 0, analysis.frames - 1)
    selected[0] = 0
    if output_count > 1:
        selected[-1] = analysis.frames - 1
    return Plan(edges, output_edges, selected, fps)


def render(source: Path, destination: Path, analysis: Analysis, plan: Plan) -> None:
    """Stream frames with bounded memory and produce a silent MPEG-4 MP4."""
    capture = open_video(source)
    size = (analysis.width // 2 * 2, analysis.height // 2 * 2)
    writer = cv2.VideoWriter(str(destination), cv2.VideoWriter_fourcc(*"mp4v"), plan.fps, size)
    source_index = output_index = 0
    try:
        if not writer.isOpened():
            raise ValueError("MPEG-4 encoder unavailable in this OpenCV installation.")
        while output_index < len(plan.selected_frames) and capture.grab():
            if source_index == plan.selected_frames[output_index]:
                ok, frame = capture.retrieve()
                if not ok:
                    raise ValueError(f"Cannot decode frame {source_index} during export.")
                if (frame.shape[1], frame.shape[0]) != size:
                    frame = cv2.resize(frame, size)
                while (
                    output_index < len(plan.selected_frames)
                    and source_index == plan.selected_frames[output_index]
                ):
                    writer.write(frame)
                    output_index += 1
                    if output_index % (plan.fps * 15) == 0:
                        print(
                            f"  Exported {output_index / plan.fps:.0f} seconds",
                            flush=True,
                        )
            source_index += 1
    finally:
        capture.release()
        writer.release()
    if output_index != len(plan.selected_frames):
        raise ValueError("Source ended unexpectedly during export; output was not published.")


def verify_output(path: Path, expected: int) -> None:
    """Decode the produced file so silent writer failures cannot report success."""
    capture = open_video(path)
    count = 0
    try:
        while True:
            ok, _ = capture.read()
            if not ok:
                break
            count += 1
    finally:
        capture.release()
    if count != expected:
        raise ValueError(f"Output verification failed: {count} frames, expected {expected}.")


def save_report(path: Path, analysis: Analysis, plan: Plan) -> None:
    """Record the time mapping for inspecting which source intervals were compressed."""
    intervals = []
    for index, allotted in enumerate(np.diff(plan.output_edges)):
        duration = plan.source_edges[index + 1] - plan.source_edges[index]
        intervals.append(
            {
                "source_start": round(float(plan.source_edges[index]), 4),
                "source_end": round(float(plan.source_edges[index + 1]), 4),
                "output_start": round(float(plan.output_edges[index]), 4),
                "output_end": round(float(plan.output_edges[index + 1]), 4),
                "speed": round(float(duration / allotted), 3),
            }
        )
    report = {
        "source_seconds": analysis.frames / analysis.fps,
        "output_seconds": len(plan.selected_frames) / plan.fps,
        "output_fps": plan.fps,
        "method": "visual activity weighted time compression, no semantic understanding",
        "intervals": intervals,
    }
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Expose only duration, sensitivity, and output frame-rate adjustments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Source screen recording")
    parser.add_argument("-o", "--output", type=Path, help="New MP4 path; never overwrite")
    parser.add_argument(
        "--seconds", type=float, default=180.0, help="Target duration (default 180)"
    )
    parser.add_argument("--fps", type=int, default=30, help="Output FPS (default 30)")
    parser.add_argument(
        "--threshold", type=float, default=0.001, help="Activity sensitivity (0, 1]"
    )
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error("--seconds must be finite and positive")
    if not 1 <= args.fps <= 120:
        parser.error("--fps must be between 1 and 120")
    if not 0 < args.threshold <= 1:
        parser.error("--threshold must be in (0, 1]")
    return args


@contextmanager
def staging_directory(parent: Path) -> Iterator[Path]:
    """Use inherited ACLs so restricted Windows accounts can access staging files."""
    directory = parent / f".screen-condense-{uuid4().hex}"
    directory.mkdir()
    try:
        yield directory
    finally:
        for name in ("result.mp4", "timeline.json"):
            (directory / name).unlink(missing_ok=True)
        directory.rmdir()


def main() -> None:
    """Publish a verified MP4 plus an inspectable report alongside the output."""
    args = parse_args()
    source = args.input.resolve(strict=True)
    output = (args.output or source.with_name(source.stem + "_short.mp4")).resolve()
    report = output.with_suffix(".timeline.json")
    if source == output or output.exists() or report.exists():
        raise ValueError("Output or report already exists; choose a new output name.")
    if output.suffix.lower() != ".mp4":
        raise ValueError("Output must end with .mp4")
    print("1/3 Analyzing visual activity...", flush=True)
    analysis = analyze(source)
    plan = make_plan(analysis, args.seconds, args.fps, args.threshold)
    print(
        f"Source: {analysis.frames / analysis.fps:.2f}s; output: "
        f"{len(plan.selected_frames) / plan.fps:.2f}s",
        flush=True,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with staging_directory(output.parent) as scratch:
        temporary = scratch / "result.mp4"
        temporary_report = scratch / "timeline.json"
        print("2/3 Exporting...", flush=True)
        render(source, temporary, analysis, plan)
        print("3/3 Verifying output...", flush=True)
        verify_output(temporary, len(plan.selected_frames))
        save_report(temporary_report, analysis, plan)
        # Exclusive creation prevents a concurrent run from replacing an existing result.
        with output.open("xb") as target, temporary.open("rb") as content:
            while chunk := content.read(1024 * 1024):
                target.write(chunk)
        with report.open("x", encoding="utf-8") as target_report:
            target_report.write(temporary_report.read_text(encoding="utf-8"))
    print(f"Done: {output}\nTimeline: {report}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, cv2.error) as error:
        raise SystemExit(f"Error: {error}") from error
