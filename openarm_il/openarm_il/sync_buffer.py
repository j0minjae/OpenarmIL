"""Approximate timestamp synchronization for passive recording streams."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TimestampedItem:
    timestamp: float
    data: Any


@dataclass(frozen=True)
class SynchronizedSample:
    timestamp: float
    items: dict[str, TimestampedItem]


class SyncBuffer:
    """Store recent stream samples and build approximate synchronized frames."""

    def __init__(
        self,
        required_streams: list[str],
        optional_streams: list[str] | None = None,
        tolerance_sec: float = 0.05,
        maxlen: int = 200,
    ) -> None:
        self.required_streams = list(required_streams)
        self.optional_streams = list(optional_streams or [])
        self.tolerance_sec = float(tolerance_sec)
        self._items: dict[str, deque[TimestampedItem]] = defaultdict(lambda: deque(maxlen=maxlen))
        self.dropped_count = 0
        self.optional_missing_count: dict[str, int] = defaultdict(int)

    def add(self, stream: str, item: TimestampedItem) -> None:
        self._items[stream].append(item)

    def _nearest(self, stream: str, timestamp: float) -> TimestampedItem | None:
        candidates = self._items.get(stream)
        if not candidates:
            return None
        nearest = min(candidates, key=lambda item: abs(item.timestamp - timestamp))
        if abs(nearest.timestamp - timestamp) > self.tolerance_sec:
            return None
        return nearest

    def get_synchronized_sample(self, timestamp: float) -> SynchronizedSample | None:
        items: dict[str, TimestampedItem] = {}
        for stream in self.required_streams:
            item = self._nearest(stream, timestamp)
            if item is None:
                self.dropped_count += 1
                return None
            items[stream] = item

        for stream in self.optional_streams:
            item = self._nearest(stream, timestamp)
            if item is None:
                self.optional_missing_count[stream] += 1
            else:
                items[stream] = item

        return SynchronizedSample(timestamp=float(timestamp), items=items)
