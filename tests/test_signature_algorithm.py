import unittest
import importlib.util
import sys
from pathlib import Path


def _load_signature_module():
    path = Path(__file__).parents[1] / "kaizen_cape" / "signature_algorithm.py"
    spec = importlib.util.spec_from_file_location("kaizen_signature_algorithm", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_signature = _load_signature_module()
ablation = _signature.ablation
allocate_experiments = _signature.allocate_experiments
sensitivity = _signature.sensitivity


class SignatureAlgorithmTests(unittest.TestCase):
    def test_budget_and_balance_constraints(self):
        result = allocate_experiments([5, 3], [2, 2], 4, min_replicates=1, max_replicates=2)
        self.assertEqual(result["allocations"], (1, 1))

    def test_invalid_shape_holds(self):
        with self.assertRaises(ValueError):
            allocate_experiments([], [], 4)

    def test_ablation_changes_allocation_space(self):
        base = allocate_experiments([5, 1], [1, 1], 4, max_replicates=4)
        removed = ablation([5, 1], [1, 1], 4, max_replicates=4)
        self.assertNotEqual(base["allocations"], removed["allocations"])

    def test_budget_sensitivity_is_reproducible(self):
        self.assertEqual(sensitivity([5, 3], [2, 2], 2, multiplier=2), sensitivity([5, 3], [2, 2], 2, multiplier=2))


if __name__ == "__main__":
    unittest.main()
