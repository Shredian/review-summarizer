import unittest

from src.infrastructure.services.summarization.aspect_evidence_guided.aspect_candidates import (
    nominal_spans_from_pos_pairs,
)


class TestNominalSpansFromPosPairs(unittest.TestCase):
    def test_splits_on_punct_and_merges_nominal_runs(self) -> None:
        pairs = [
            ("красивый", "ADJ"),
            ("экран", "NOUN"),
            (".", "PUNCT"),
            ("батарея", "NOUN"),
            ("держит", "VERB"),
            ("долго", "ADV"),
        ]
        out = nominal_spans_from_pos_pairs(pairs, min_candidate_len=3)
        self.assertIn("красивый экран", out)
        self.assertIn("батарея", out)

    def test_respects_min_length(self) -> None:
        pairs = [("я", "PRON"), ("телефон", "NOUN")]
        out = nominal_spans_from_pos_pairs(pairs, min_candidate_len=10)
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
