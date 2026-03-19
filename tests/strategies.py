"""Shared Hypothesis strategies and fixtures for property-based testing.

Provides composable strategies for generating algebraic structures
(magmas, equations, problems) with valid invariants baked in.
"""

from hypothesis import strategies as st

from data_models import Equation, Magma, Problem, Property

# ── Magma strategies ────────────────────────────────────────────


@st.composite
def magma_tables(draw, size: int = 2):
    """Generate a valid Cayley table for a magma of given size.

    Every entry is in [0, size), guaranteeing closure.
    """
    table = draw(
        st.lists(
            st.lists(
                st.integers(min_value=0, max_value=size - 1),
                min_size=size,
                max_size=size,
            ),
            min_size=size,
            max_size=size,
        )
    )
    return table


@st.composite
def magmas(draw, min_size: int = 1, max_size: int = 4):
    """Generate an arbitrary finite magma with size in [min_size, max_size]."""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    table = draw(magma_tables(size=size))
    return Magma(size=size, elements=list(range(size)), operation=table)


@st.composite
def small_magmas(draw):
    """Generate magmas of size 1-3 (fast for exhaustive property checks)."""
    return draw(magmas(min_size=1, max_size=3))


@st.composite
def size_two_magmas(draw):
    """Generate all possible size-2 magmas (16 total)."""
    return draw(magmas(min_size=2, max_size=2))


# ── Equation strategies ────────────────────────────────────────


@st.composite
def properties(draw):
    """Generate a random Property enum value."""
    return draw(st.sampled_from(list(Property)))


@st.composite
def property_lists(draw, min_size: int = 0, max_size: int = 4):
    """Generate a list of unique properties."""
    props = draw(
        st.lists(
            st.sampled_from(list(Property)),
            min_size=min_size,
            max_size=max_size,
            unique=True,
        )
    )
    return props


@st.composite
def equations(draw):
    """Generate a random Equation."""
    eq_id = draw(st.integers(min_value=1, max_value=10000))
    latex = draw(st.text(min_size=1, max_size=50))
    alphabet = st.characters(categories=("L", "N", "Z"))
    name = draw(st.text(min_size=1, max_size=30, alphabet=alphabet))
    props = draw(property_lists())
    desc = draw(st.text(max_size=100))
    return Equation(id=eq_id, latex=latex, name=name, properties=props, description=desc)


# ── Problem strategies ──────────────────────────────────────────


@st.composite
def problems(draw, max_eq_id: int = 100):
    """Generate a random Problem."""
    prob_id = draw(st.integers(min_value=1, max_value=10000))
    eq1 = draw(st.integers(min_value=1, max_value=max_eq_id))
    eq2 = draw(st.integers(min_value=1, max_value=max_eq_id))
    answer = draw(st.one_of(st.none(), st.booleans()))
    difficulty = draw(st.sampled_from(["regular", "hard"]))
    return Problem(
        id=prob_id, equation_1_id=eq1, equation_2_id=eq2,
        answer=answer, difficulty=difficulty,
    )


# ── Element strategies for magma operations ─────────────────────


def elements_of(magma: Magma):
    """Strategy for elements within a specific magma."""
    return st.integers(min_value=0, max_value=magma.size - 1)


def element_pairs(magma: Magma):
    """Strategy for pairs of elements."""
    return st.tuples(elements_of(magma), elements_of(magma))


def element_triples(magma: Magma):
    """Strategy for triples of elements."""
    return st.tuples(elements_of(magma), elements_of(magma), elements_of(magma))


# ── Term S-expression strategies (for equation checking) ────────


@st.composite
def variable_names(draw):
    """Generate a variable name (single lowercase letter)."""
    return draw(st.sampled_from(["x", "y", "z", "w"]))


@st.composite
def term_sexprs(draw, max_depth: int = 3, size: int = 2):
    """Generate a term S-expression for equation checking.

    Produces trees like ["*", ["x"], ["y"]] or ["*", ["*", ["x"], ["y"]], ["z"]].
    """
    if max_depth <= 0 or draw(st.booleans()):
        # Leaf: variable or literal
        if draw(st.booleans()):
            var = draw(variable_names())
            return [var]
        else:
            lit = draw(st.integers(min_value=0, max_value=size - 1))
            return [str(lit)]
    else:
        left = draw(term_sexprs(max_depth=max_depth - 1, size=size))
        right = draw(term_sexprs(max_depth=max_depth - 1, size=size))
        return ["*", left, right]
