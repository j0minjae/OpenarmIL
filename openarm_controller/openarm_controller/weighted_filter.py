"""Weighted moving average filter matching openarmx behavior."""

import numpy as np


class WeightedMovingFilter:
    """Smooths IK output with a weighted moving average over recent frames.

    Default weights [0.4, 0.3, 0.2, 0.1] match openarmx_arm_driver.
    """

    def __init__(self, weights=(0.4, 0.3, 0.2, 0.1), dim=14):
        self.weights = np.asarray(weights, dtype=np.float64)
        self.dim = dim
        self.window_size = len(weights)
        self.buffer = [np.zeros(dim, dtype=np.float64) for _ in range(self.window_size)]
        self.count = 0

    def filter(self, data: np.ndarray) -> np.ndarray:
        for i in range(self.window_size - 1, 0, -1):
            self.buffer[i] = self.buffer[i - 1]
        self.buffer[0] = np.asarray(data, dtype=np.float64)

        if self.count < self.window_size:
            self.count += 1

        result = np.zeros(self.dim, dtype=np.float64)
        w_sum = 0.0
        for i in range(self.count):
            result += self.weights[i] * self.buffer[i]
            w_sum += self.weights[i]
        return result / w_sum

    def reset(self):
        for i in range(self.window_size):
            self.buffer[i] = np.zeros(self.dim, dtype=np.float64)
        self.count = 0
