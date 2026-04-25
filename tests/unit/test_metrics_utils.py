"""Tests for src/metrics_utils.py — shared confusion-matrix utilities.

Feature: Shared confusion-matrix tracking
    As evaluation code across multiple modules
    I want a single update_confusion function
    So that classification logic stays consistent everywhere
"""

from __future__ import annotations

import pytest

from metrics_utils import compute_accuracy_metrics, update_confusion


class TestUpdateConfusion:
    """Feature: update_confusion increments the correct cell."""

    @pytest.mark.unit
    def test_true_positive(self):
        """
        Scenario: Predicted TRUE, actual TRUE → tp increments
        Given a counts dict and predicted=True, actual=True
        When update_confusion is called
        Then tp increases by 1 and others are unchanged
        """
        counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
        update_confusion(counts, predicted=True, actual=True)
        assert counts == {"tp": 1, "fp": 0, "tn": 0, "fn": 0}

    @pytest.mark.unit
    def test_false_positive(self):
        """
        Scenario: Predicted TRUE, actual FALSE → fp increments
        Given a counts dict and predicted=True, actual=False
        When update_confusion is called
        Then fp increases by 1
        """
        counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
        update_confusion(counts, predicted=True, actual=False)
        assert counts == {"tp": 0, "fp": 1, "tn": 0, "fn": 0}

    @pytest.mark.unit
    def test_false_negative(self):
        """
        Scenario: Predicted FALSE, actual TRUE → fn increments
        Given a counts dict and predicted=False, actual=True
        When update_confusion is called
        Then fn increases by 1
        """
        counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
        update_confusion(counts, predicted=False, actual=True)
        assert counts == {"tp": 0, "fp": 0, "tn": 0, "fn": 1}

    @pytest.mark.unit
    def test_true_negative(self):
        """
        Scenario: Predicted FALSE, actual FALSE → tn increments
        Given a counts dict and predicted=False, actual=False
        When update_confusion is called
        Then tn increases by 1
        """
        counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
        update_confusion(counts, predicted=False, actual=False)
        assert counts == {"tp": 0, "fp": 0, "tn": 1, "fn": 0}

    @pytest.mark.unit
    def test_accumulates_across_multiple_calls(self):
        """
        Scenario: Multiple calls accumulate correctly
        Given a sequence of (predicted, actual) pairs
        When update_confusion is called for each
        Then the final counts match the expected totals
        """
        counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
        pairs = [
            (True, True),  # tp
            (True, True),  # tp
            (False, False),  # tn
            (True, False),  # fp
            (False, True),  # fn
        ]
        for predicted, actual in pairs:
            update_confusion(counts, predicted=predicted, actual=actual)
        assert counts == {"tp": 2, "fp": 1, "tn": 1, "fn": 1}

    @pytest.mark.unit
    def test_only_mutates_one_cell(self):
        """
        Scenario: Each call mutates exactly one cell
        Given non-zero initial counts
        When update_confusion is called
        Then only one cell changes
        """
        counts = {"tp": 5, "fp": 3, "tn": 7, "fn": 2}
        before = dict(counts)
        update_confusion(counts, predicted=True, actual=True)
        changed = [k for k in counts if counts[k] != before[k]]
        assert changed == ["tp"]


class TestComputeAccuracyMetrics:
    """Feature: compute_accuracy_metrics derives standard ML metrics."""

    @pytest.mark.unit
    def test_perfect_classifier(self):
        """
        Scenario: All predictions correct → accuracy=1.0, precision=1.0, recall=1.0
        Given tp=50, fp=0, tn=50, fn=0
        When compute_accuracy_metrics is called
        Then accuracy=1.0, precision=1.0, recall=1.0, f1=1.0
        """
        m = compute_accuracy_metrics(tp=50, fp=0, tn=50, fn=0)
        assert m["accuracy"] == 1.0
        assert m["precision"] == 1.0
        assert m["recall"] == 1.0
        assert m["f1"] == 1.0

    @pytest.mark.unit
    def test_zero_precision_when_no_positives_predicted(self):
        """
        Scenario: No positive predictions → precision is 0.0
        Given tp=0, fp=0 (no positive predictions)
        When compute_accuracy_metrics is called
        Then precision == 0.0 (no ZeroDivisionError)
        """
        m = compute_accuracy_metrics(tp=0, fp=0, tn=10, fn=5)
        assert m["precision"] == 0.0

    @pytest.mark.unit
    def test_zero_recall_when_no_true_positives(self):
        """
        Scenario: No true positives found → recall is 0.0
        Given tp=0, fn>0
        When compute_accuracy_metrics is called
        Then recall == 0.0 (no ZeroDivisionError)
        """
        m = compute_accuracy_metrics(tp=0, fp=3, tn=10, fn=5)
        assert m["recall"] == 0.0

    @pytest.mark.unit
    def test_known_values(self):
        """
        Scenario: Known tp/fp/tn/fn → expected metrics
        Given tp=80, fp=10, tn=90, fn=20 (total=200)
        When compute_accuracy_metrics is called
        Then accuracy=0.85, precision=0.888..., recall=0.8
        """
        m = compute_accuracy_metrics(tp=80, fp=10, tn=90, fn=20)
        assert abs(m["accuracy"] - 0.85) < 1e-9
        assert abs(m["precision"] - 80 / 90) < 1e-9
        assert abs(m["recall"] - 80 / 100) < 1e-9

    @pytest.mark.unit
    def test_f1_harmonic_mean(self):
        """
        Scenario: F1 is the harmonic mean of precision and recall
        Given tp=60, fp=20, tn=80, fn=40
        When compute_accuracy_metrics is called
        Then f1 == 2*tp / (2*tp + fp + fn)
        """
        tp, fp, tn, fn = 60, 20, 80, 40
        m = compute_accuracy_metrics(tp=tp, fp=fp, tn=tn, fn=fn)
        expected_f1 = 2 * tp / (2 * tp + fp + fn)
        assert abs(m["f1"] - expected_f1) < 1e-9

    @pytest.mark.unit
    def test_all_zeros_returns_zero_metrics(self):
        """
        Scenario: All counts zero → all metrics are 0.0 (no ZeroDivisionError)
        Given tp=0, fp=0, tn=0, fn=0
        When compute_accuracy_metrics is called
        Then all metrics are 0.0
        """
        m = compute_accuracy_metrics(tp=0, fp=0, tn=0, fn=0)
        assert m["accuracy"] == 0.0
        assert m["precision"] == 0.0
        assert m["recall"] == 0.0
        assert m["f1"] == 0.0
