"""Regression cases for authorship boundaries and archive-copy identity."""
import json
from pathlib import Path
import unittest

from export_v2_words import own_words, remove_archive_copies, validate_public


def record(identifier, source="ChatGPT", stamp="2026-01-01T12:00:05+01:00",
           text="toto som napisal ja", conversation="one", locator=None):
    return {"id": identifier, "zdroj": source, "datum": stamp, "datum_presnost": "cas",
            "normalized_text": text, "lokator": locator or identifier,
            "rozhovor_id": conversation, "slov": len(text.split()),
            "segmenty": [[0, len(text), "vlastny", len(text.split())]]}


class AuthorshipBoundaries(unittest.TestCase):
    def test_only_own_spans_count_in_mixed_message(self):
        r = record("mixed", text="moje slova\ncudzi clanok\nmoj diktat")
        lines = r["normalized_text"].splitlines(keepends=True)
        second = len(lines[0])
        third = second + len(lines[1])
        r["segmenty"] = [[0, second, "vlastny", 2], [second, third, "vlozeny_cudzi", 2],
                         [third, len(r["normalized_text"]), "vlastny", 2]]
        self.assertEqual(own_words(r), (4, 4))

    def test_converter_copy_is_not_new_writing(self):
        r = record("converter", text="moje slova [DEDUPED_CONTEXT_BLOCK] copied excerpt [END_DEDUPED_CONTEXT_BLOCK]")
        self.assertEqual(own_words(r), (6, 2))

    def test_invalid_spans_fail_instead_of_double_counting(self):
        r = record("broken")
        r["segmenty"].append([1, 5, "vlastny", 1])
        with self.assertRaises(ValueError):
            own_words(r)


class ArchiveIdentity(unittest.TestCase):
    def test_old_pdf_copy_matches_native_message_with_minute_precision(self):
        kept, removed = remove_archive_copies([
            record("b", "stary_gpt", "2026-01-01T12:00:00+01:00"), record("a")])
        self.assertEqual([r["id"] for r in kept], ["a"])
        self.assertEqual([r["id"] for r in removed], ["b"])

    def test_repeated_writing_at_another_time_survives(self):
        kept, removed = remove_archive_copies([
            record("a"), record("b", stamp="2026-01-02T12:00:05+01:00")])
        self.assertEqual(len(kept), 2)
        self.assertEqual(removed, [])

    def test_repeated_messages_within_one_export_are_preserved(self):
        kept, removed = remove_archive_copies([
            record("a"), record("b", stamp="2026-01-01T12:00:45+01:00"),
            record("c", "stary_gpt", "2026-01-01T12:00:00+01:00")])
        self.assertEqual({r["id"] for r in kept}, {"a", "b"})
        self.assertEqual([r["id"] for r in removed], ["c"])

    def test_fork_copy_uses_full_timestamp(self):
        a, b = record("a", "Claude"), record("b", "Claude", conversation="fork")
        self.assertEqual(tuple(map(len, remove_archive_copies([a, b]))), (1, 1))
        b["datum"] = "2026-01-01T12:00:06+01:00"
        self.assertEqual(tuple(map(len, remove_archive_copies([a, b]))), (2, 0))

    def test_pdf_missing_glyphs_do_not_create_more_own_writing(self):
        a = record("a", "Kortex", text="chcem vedieť či mám začať písať")
        b = record("b", "Kortex_pdf_vyber", text="chcem vedie i mám za a písa")
        kept, removed = remove_archive_copies([b, a])
        self.assertEqual([r["id"] for r in kept], ["a"])
        self.assertEqual([r["id"] for r in removed], ["b"])

    def test_same_wording_from_different_tools_is_not_an_export_copy(self):
        self.assertEqual(tuple(map(len, remove_archive_copies([
            record("a"), record("b", "Claude")]))), (2, 0))


class PublicSnapshot(unittest.TestCase):
    def setUp(self):
        self.snapshot = json.loads((Path(__file__).resolve().parent.parent / "data/v2-writing.json").read_text())

    def test_unexpected_private_field_is_rejected(self):
        self.snapshot["prompt_text"] = "private fixture"
        with self.assertRaises(ValueError):
            validate_public(self.snapshot)

    def test_total_cannot_drift_from_source_groups(self):
        self.snapshot["sources"][0]["words"] += 1
        with self.assertRaises(ValueError):
            validate_public(self.snapshot)


if __name__ == "__main__":
    unittest.main()
