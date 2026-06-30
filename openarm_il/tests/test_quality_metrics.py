import numpy as np

from openarm_il.quality_metrics import ConfidenceConfig, compute_confidence


def test_confidence_is_bounded_and_returns_terms():
    actions = np.zeros((3, 16), dtype=np.float32)
    actions[2] = 0.5
    hand_confidence = np.array([[1.0, 1.0], [0.5, 1.0], [0.5, 0.5]], dtype=np.float32)
    workspace_violation = np.array([0.0, 0.1, 0.2], dtype=np.float32)

    result = compute_confidence(actions, hand_confidence, workspace_violation, ConfidenceConfig())

    assert result.confidence.shape == (3,)
    assert np.all(result.confidence >= 0.0)
    assert np.all(result.confidence <= 1.0)
    assert result.uncertainty_terms.shape == (3, 4)
    assert result.confidence[0] > result.confidence[-1]
