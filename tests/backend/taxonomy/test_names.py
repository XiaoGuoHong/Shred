"""Taxonomy-name normalization tests at the user-input boundary."""

from __future__ import annotations

import pytest

from shred.taxonomy.names import normalize_category_name, normalize_tag_name


def test_normalize_category_name_uses_nfkc_and_whitespace_to_prevent_duplicate_lookalikes() -> None:
    assert normalize_category_name("  工　作  ") == "工 作"


def test_category_name_accepts_one_visible_character_to_preserve_minimal_categories() -> None:
    assert normalize_category_name("工") == "工"


def test_category_name_accepts_forty_visible_characters_without_rejecting_the_boundary() -> None:
    assert normalize_category_name("工" * 40) == "工" * 40


def test_category_name_rejects_empty_normalized_values_to_prevent_blank_taxonomy_nodes() -> None:
    with pytest.raises(ValueError):
        normalize_category_name("　 \t")


def test_category_name_rejects_forty_one_visible_characters_to_bound_taxonomy_labels() -> None:
    with pytest.raises(ValueError):
        normalize_category_name("工" * 41)


def test_tag_name_accepts_one_visible_character_to_preserve_short_tags() -> None:
    assert normalize_tag_name("急") == "急"


def test_tag_name_accepts_thirty_visible_characters_without_rejecting_the_boundary() -> None:
    assert normalize_tag_name("急" * 30) == "急" * 30


def test_tag_name_rejects_empty_normalized_values_to_prevent_blank_tags() -> None:
    with pytest.raises(ValueError):
        normalize_tag_name(" \n　")


def test_tag_name_rejects_thirty_one_visible_characters_to_bound_tag_labels() -> None:
    with pytest.raises(ValueError):
        normalize_tag_name("急" * 31)
