"""Regression tests for the eval grounding metric (no Gemini calls)."""
from evals.scorers import grounded, stem, fuzzy_match


def test_stem_plurals():
    assert stem("tables") == "table"
    assert stem("boxes") == "box"
    assert stem("policies") == "policy"
    assert stem("class") == "class"   # no over-stripping of -ss
    assert stem("queue") == "queue"


def test_grounded_handles_plural_and_acronym():
    text = "A stack follows LIFO; both are fundamental abstract data types."
    assert grounded("Abstract Data Type (ADT)", text)      # acronym in parens
    assert grounded("Hash Tables", "consider a hash table implementation")  # plural


def test_grounded_negative_control():
    assert not grounded("Photosynthesis", "a variable stores a value")


def test_grounded_full_phrase():
    assert grounded("Gradient Descent", "we use gradient descent to optimize")


def test_fuzzy_match_variants():
    assert fuzzy_match("Big O", ["Big-O Notation"])
    assert fuzzy_match("Light-Dependent Reactions", ["the light dependent reactions capture energy"])
    assert not fuzzy_match("Recursion", ["Photosynthesis", "Mitosis"])
