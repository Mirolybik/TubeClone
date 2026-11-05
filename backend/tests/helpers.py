"""Вспомогательные функции для проверки метрик Prometheus."""

from __future__ import annotations


def metrics_lines(text: str):
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        sample, _, value = line.rpartition(" ")
        try:
            yield sample, float(value)
        except ValueError:
            continue


def metric_sum(text: str, prefix: str) -> float:
    return sum(value for sample, value in metrics_lines(text) if sample.startswith(prefix))


def metric_value(text: str, sample: str) -> float:
    for current, value in metrics_lines(text):
        if current == sample:
            return value
    return 0.0
