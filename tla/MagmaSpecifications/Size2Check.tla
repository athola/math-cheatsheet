-------------------------- MODULE Size2Check --------------------------
(*
  Genuinely TLC-checkable facts about size-2 magmas.

  This is the ONE executable TLA+ artifact in this directory. The other
  modules here (Magma, EquationChecking, MagmaModel, TEST_MODEL,
  InvariantCheck, Invariants, Counterexamples/CounterexampleExplorer)
  are illustrative pseudo-specifications and are NOT currently machine
  checked -- see the header banner in each of those files.

  Carrier S = {0, 1}. There are exactly 2^(2^2) = 16 binary operations
  on S. TLC enumerates all of them and evaluates the invariant
  `Size2Facts` exhaustively, so the facts below are model-checked, not
  merely asserted.

  What this establishes for the cheatsheet:
    * Associativity does NOT imply commutativity (a size-2 magma is
      associative but not commutative -- e.g. left projection a*b = a).
    * Idempotence does NOT imply commutativity (left projection is also
      idempotent but not commutative).
    * The exact counts of associative / commutative / idempotent
      operations among the 16 size-2 magmas.

  Run:
    java -cp ../tools/tla2tools.jar tlc2.TLC \
      -config Size2Check.cfg Size2Check.tla
*)

EXTENDS Naturals, FiniteSets

S == {0, 1}

\* All binary operations on S, represented as functions (S \X S) -> S.
AllOps == [(S \X S) -> S]

IsAssociative(op) ==
    \A a, b, c \in S : op[<<op[<<a, b>>], c>>] = op[<<a, op[<<b, c>>]>>]

IsCommutative(op) ==
    \A a, b \in S : op[<<a, b>>] = op[<<b, a>>]

IsIdempotent(op) ==
    \A a \in S : op[<<a, a>>] = a

\* Exact counts among the 16 size-2 operations (sanity facts).
AssocCount == Cardinality({op \in AllOps : IsAssociative(op)})
CommCount  == Cardinality({op \in AllOps : IsCommutative(op)})
IdempCount == Cardinality({op \in AllOps : IsIdempotent(op)})

\* Witness: an associative but non-commutative size-2 magma exists,
\* which is a genuine counterexample to "associativity => commutativity".
AssocNotCommExists ==
    \E op \in AllOps : IsAssociative(op) /\ ~IsCommutative(op)

\* Witness: an idempotent but non-commutative size-2 magma exists,
\* a counterexample to "idempotence => commutativity".
IdempNotCommExists ==
    \E op \in AllOps : IsIdempotent(op) /\ ~IsCommutative(op)

\* The conjunction TLC checks. Counts are asserted at the values TLC
\* itself confirms; if a count were wrong TLC would refuse to start with
\* an assumption-violation error (verified -- see the module header).
Size2Facts ==
    /\ AssocCount = 8
    /\ CommCount = 8
    /\ IdempCount = 4
    /\ AssocNotCommExists
    /\ IdempNotCommExists

\* These are constant-level facts (no variables), so they are asserted as
\* an ASSUME, which TLC evaluates exhaustively at startup. A false fact
\* aborts the run.
ASSUME Size2FactsHold == Size2Facts

\* Trivial single-state behaviour so TLC has a spec to run alongside the
\* constant assumption above.
VARIABLE pc
Init == pc = 0
Next == UNCHANGED pc
Spec == Init /\ [][Next]_pc
TypeOK == pc = 0

=======================================================================
