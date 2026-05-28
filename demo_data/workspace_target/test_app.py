# test_app.py - Test suite for Product Rating Service
from app import calculate_product_rating
import pytest

def test_rating_with_reviews():
    """Verifies rating calculation when reviews exist."""
    reviews = [{'score': 4}, {'score': 5}]
    assert calculate_product_rating(reviews) == 4.5

def test_rating_with_zero_reviews():
    """Verifies rating calculation when there are no reviews."""
    reviews = []
    # This will trigger the division by zero error in the buggy app.py
    assert calculate_product_rating(reviews) == 0.0
