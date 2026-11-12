"""QRSM x Grover: asking a quantum recurrent model about its rarest histories."""

from .amplify import (amplified, amplified_state, best_calls_per_hit, calls_per_hit, grover_iterate, hardware_amplified,
                      iterations_to_peak, rotation_angle, steered_gamma, success_probability)
from .classical import BackwardSampler, conditional_distribution, total_variation
from .model import QRSM, history_to_string, string_to_history
from .predicates import any_click, at_least, click_at, contains, exact_record, odd_clicks, recurrent_counter_oracle

__version__ = "0.1.0"

__all__ = ["QRSM", "BackwardSampler", "amplified", "amplified_state", "any_click", "at_least", "best_calls_per_hit", "calls_per_hit",
           "click_at", "conditional_distribution", "contains", "exact_record", "grover_iterate", "hardware_amplified",
           "history_to_string", "iterations_to_peak", "odd_clicks", "recurrent_counter_oracle", "rotation_angle", "steered_gamma",
           "string_to_history", "success_probability", "total_variation"]
