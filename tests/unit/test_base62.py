"""Unit tests for Base62 encoding and collision resistance."""

import pytest
from app.services.url_service import (
    BASE62_ALPHABET,
    encode_base62,
    generate_collision_resistant_short_code,
)


def test_encode_base62_basic():
    assert encode_base62(0) == "0"
    assert encode_base62(1) == "1"
    assert encode_base62(61) == "Z"
    assert encode_base62(62) == "10"
    assert encode_base62(3843) == "ZZ"


def test_encode_base62_large_integer():
    large_num = 1234567890123456
    encoded = encode_base62(large_num)
    assert len(encoded) > 0
    assert all(c in BASE62_ALPHABET for c in encoded)


def test_short_code_format_and_uniqueness():
    codes = set()
    sample_size = 1000

    for _ in range(sample_size):
        code = generate_collision_resistant_short_code(length=7)
        assert len(code) == 7
        assert all(c in BASE62_ALPHABET for c in code)
        codes.add(code)

    # 1,000 random 42-bit Base62 codes must have zero collisions
    assert len(codes) == sample_size
