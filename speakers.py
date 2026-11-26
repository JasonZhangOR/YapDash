from collections import deque

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage


def fingerprint(image):
    if image.isNull():
        return None
    sample = image.scaled(32, 20, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    sample = sample.convertToFormat(QImage.Format_RGB888)
    pixels = sample.constBits()
    pixels.setsize(sample.sizeInBytes())
    return bytes(pixels)


def distance(first, second):
    return sum(abs(a - b) for a, b in zip(first, second)) / len(first)


def is_active(current, quiet, speaking):
    separation = distance(quiet, speaking)
    if separation < 2:
        return False
    idle_distance = distance(current, quiet)
    speaking_distance = distance(current, speaking)
    return speaking_distance <= separation * 0.60 and speaking_distance < idle_distance * 0.72


class Activity:
    def __init__(self):
        self.samples = deque()

    def record(self, timestamp, names):
        self.samples.append((timestamp, frozenset(names)))
        while self.samples and timestamp - self.samples[0][0] > 90:
            self.samples.popleft()

    def identify(self, start, end):
        span = end - start
        if span <= 0:
            return None
        votes = {}
        overlap = 0
        previous = None
        for timestamp, names in self.samples:
            if previous:
                last_time, last_names = previous
                duration = max(0, min(timestamp, last_time + 0.22, end) - max(last_time, start))
                if duration and len(last_names) > 1:
                    overlap += duration
                elif duration and last_names:
                    name = next(iter(last_names))
                    votes[name] = votes.get(name, 0) + duration
            if timestamp >= end:
                break
            previous = timestamp, names
        ordered = sorted(votes.items(), key=lambda entry: entry[1], reverse=True)
        if not ordered:
            return None
        name, coverage = ordered[0]
        competing = overlap + sum(seconds for _, seconds in ordered[1:])
        if coverage >= span * 0.45 and competing < min(coverage * 0.30, span * 0.20):
            return name
        return None
