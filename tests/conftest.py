"""Shared pytest fixtures for magma test suites.

Provides commonly used magma instances so that individual test files
don't need to redefine the same Cayley tables.
"""

import pytest

from data_models import Magma


@pytest.fixture
def xor_magma():
    """Z/2Z under XOR: associative, commutative, has identity 0, NOT idempotent."""
    return Magma(size=2, elements=[0, 1], operation=[[0, 1], [1, 0]])


@pytest.fixture
def and_magma():
    """Z/2Z under AND: associative, commutative, idempotent, has identity 1."""
    return Magma(size=2, elements=[0, 1], operation=[[0, 0], [0, 1]])


@pytest.fixture
def or_magma():
    """Z/2Z under OR: associative, commutative, idempotent, has identity 0."""
    return Magma(size=2, elements=[0, 1], operation=[[0, 1], [1, 1]])


@pytest.fixture
def trivial_magma():
    """Single-element magma: associative, commutative, idempotent, has identity 0."""
    return Magma(size=1, elements=[0], operation=[[0]])


@pytest.fixture
def z3_add_magma():
    """Z/3Z under addition: associative, commutative, has identity, NOT idempotent."""
    return Magma(size=3, elements=[0, 1, 2], operation=[[0, 1, 2], [1, 2, 0], [2, 0, 1]])


@pytest.fixture
def non_assoc_magma():
    """A non-associative magma of size 3."""
    return Magma(size=3, elements=[0, 1, 2], operation=[[0, 2, 1], [2, 1, 0], [1, 0, 2]])


def all_size_2_magmas():
    """Generate all 16 size-2 magmas using the same bit-unpacking as ALL_SIZE_2_MAGMAS.

    Bit layout for index i: table[0][0]=bit3, table[0][1]=bit2,
    table[1][0]=bit1, table[1][1]=bit0.
    """
    magmas = []
    for i in range(16):
        table = [
            [i >> 3 & 1, i >> 2 & 1],
            [i >> 1 & 1, i & 1],
        ]
        magmas.append(Magma(size=2, elements=[0, 1], operation=table))
    return magmas
