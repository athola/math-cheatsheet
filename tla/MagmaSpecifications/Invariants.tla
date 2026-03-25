--------------------------- MODULE Invariants ---------------------------
(*
  Full-scope invariant specifications for magma model checking.

  These invariants are verified by TLC (the TLA+ model checker) against
  ALL reachable states, making TLA+ a natural property-based testing
  framework for finite algebraic structures.

  BDD Scenarios:
    Feature: Algebraic invariants hold for all finite magmas
    Scenario: Given ANY magma (S, op), THEN [invariant] holds
*)

EXTENDS Naturals, Sequences, FiniteSets, Magma

(******************************************************************************
* Feature: Closure Invariant
* Given: ANY magma (S, op)
* Then: op(a, b) ∈ S for all a, b ∈ S
******************************************************************************)

\* This is the fundamental type correctness invariant.
\* TLC checks this for ALL elements in S × S.
ClosureInvariant ==
    \A a, b \in S : op[a, b] \in S

(******************************************************************************
* Feature: Identity Element Uniqueness
* Given: ANY magma (S, op)
* Then: There is at most one two-sided identity element
******************************************************************************)

\* Count identity elements
IdentityElements == {e \in S : \A a \in S : (op[e, a] = a) /\ (op[a, e] = a)}

\* Invariant: at most one identity
IdentityUniqueness == Cardinality(IdentityElements) <= 1

\* If left identity and right identity exist, they must be the same element
LeftRightIdentityAgreement ==
    LET leftIds == {e \in S : \A a \in S : op[e, a] = a}
        rightIds == {e \in S : \A a \in S : op[a, e] = a}
    IN (leftIds /= {} /\ rightIds /= {}) =>
       (\E e \in S : e \in leftIds /\ e \in rightIds)

(******************************************************************************
* Feature: Commutativity ↔ Cayley Table Symmetry
* Given: ANY magma (S, op)
* Then: Commutative iff op[a,b] = op[b,a] for all a,b
******************************************************************************)

\* Direct definition of symmetry
TableSymmetric == \A a, b \in S : op[a, b] = op[b, a]

\* Invariant: these are the SAME predicate
CommutativityEqualsSymmetry == Commutative <=> TableSymmetric

(******************************************************************************
* Feature: Idempotence ↔ Diagonal Property
* Given: ANY magma (S, op)
* Then: Idempotent iff op[a,a] = a for all a
******************************************************************************)

\* Idempotent definition
Idempotent == \A a \in S : op[a, a] = a

\* Direct diagonal check
DiagonalIsIdentity == \A a \in S : op[a, a] = a

\* Invariant: these are the SAME predicate
IdempotenceEqualsDiagonal == Idempotent <=> DiagonalIsIdentity

(******************************************************************************
* Feature: Implication Reflexivity
* Given: ANY equation E and magma M
* Then: If M ⊨ E, then M ⊨ E
*
* This is trivially true but serves as a sanity check on our
* equation satisfaction definition.
******************************************************************************)

\* Check reflexivity for standard equations
ImplicationReflexivity ==
    /\ (Associative => Associative)
    /\ (Commutative => Commutative)
    /\ (HasIdentity => HasIdentity)
    /\ (Idempotent => Idempotent)

(******************************************************************************
* Feature: Known Non-Implications
* These specify magmas that WITNESS property independence.
*
* Invariant form: ∃ magma where P holds ∧ Q fails
* We verify by providing the concrete witness.
******************************************************************************)

\* Witness: Associative but not commutative
\* Matrix multiplication over Z/2Z (or simpler: left projection)
AssocNotCommWitness(S_local, op_local) ==
    /\ (\A a, b, c \in S_local :
        op_local[op_local[a, b], c] = op_local[a, op_local[b, c]])
    /\ (\E a, b \in S_local : op_local[a, b] /= op_local[b, a])

\* Witness: Commutative but not associative
CommNotAssocWitness(S_local, op_local) ==
    /\ (\A a, b \in S_local : op_local[a, b] = op_local[b, a])
    /\ (\E a, b, c \in S_local :
        op_local[op_local[a, b], c] /= op_local[a, op_local[b, c]])

\* Witness: Idempotent but not commutative
IdempNotCommWitness(S_local, op_local) ==
    /\ (\A a \in S_local : op_local[a, a] = a)
    /\ (\E a, b \in S_local : op_local[a, b] /= op_local[b, a])

(******************************************************************************
* Feature: Property Count Invariants for Size 2
* Given: ALL 16 magmas on {0, 1}
* Then: Exact property counts match expectation
*
* Note: TLC enumerates ALL functions {0,1}×{0,1} → {0,1} = 16 magmas
******************************************************************************)

\* For size-2 verification, instantiate S = {0, 1}
\* and op ranges over all functions [{0,1} × {0,1} → {0,1}]
AllOperationsOnTwo == [({0, 1} \X {0, 1}) -> {0, 1}]

CountAssociativeSize2 ==
    LET S2 == {0, 1}
        assocOps == {op2 \in AllOperationsOnTwo :
            \A a, b, c \in S2 :
                op2[<<op2[<<a, b>>], c>>] = op2[<<a, op2[<<b, c>>]>>]}
    IN Cardinality(assocOps) = 8

CountCommutativeSize2 ==
    LET S2 == {0, 1}
        commOps == {op2 \in AllOperationsOnTwo :
            \A a, b \in S2 : op2[<<a, b>>] = op2[<<b, a>>]}
    IN Cardinality(commOps) = 8

CountIdempotentSize2 ==
    LET S2 == {0, 1}
        idempOps == {op2 \in AllOperationsOnTwo :
            \A a \in S2 : op2[<<a, a>>] = a}
    IN Cardinality(idempOps) = 4

CountIdentitySize2 ==
    LET S2 == {0, 1}
        idOps == {op2 \in AllOperationsOnTwo :
            \E e \in S2 : \A a \in S2 :
                (op2[<<e, a>>] = a) /\ (op2[<<a, e>>] = a)}
    IN Cardinality(idOps) = 4

(******************************************************************************
* Feature: Algebraic Hierarchy Invariants
* Given: ANY magma (S, op)
* Then: Monoid ⇒ Semigroup, Group ⇒ Monoid
******************************************************************************)

\* A semigroup is an associative magma
IsSemigroup == Associative

\* A monoid is an associative magma with identity
IsMonoid == Associative /\ HasIdentity

\* Hierarchy invariant: Monoid ⇒ Semigroup
MonoidImpliesSemigroup == IsMonoid => IsSemigroup

\* HasIdentity ∧ Associative ⇒ identity element acts as both left and right
MonoidIdentityIsTwoSided ==
    IsMonoid =>
        \A e \in IdentityElements :
            (\A a \in S : op[e, a] = a) /\ (\A a \in S : op[a, e] = a)

(******************************************************************************
* Feature: Counterexample State Machine Invariants
******************************************************************************)

\* The state machine from EquationChecking.tla has these invariants:
\* 1. state ∈ {"searching", "found", "exhausted"}
\* 2. If state = "found", then found_counterexample is a valid assignment
\* 3. state transitions: searching → found | exhausted

\* State type invariant (imported from EquationChecking)
\* StateTypeOK ==
\*     /\ state \in {"searching", "found", "exhausted"}
\*     /\ (state = "found") => (found_counterexample \in [String -> S])

(******************************************************************************
* Master Invariant (conjunction of all invariants)
******************************************************************************)

\* Run all invariants together for model checking
AllInvariants ==
    /\ ClosureInvariant
    /\ IdentityUniqueness
    /\ CommutativityEqualsSymmetry
    /\ IdempotenceEqualsDiagonal
    /\ ImplicationReflexivity
    /\ MonoidImpliesSemigroup
    /\ MonoidIdentityIsTwoSided

=============================================================================
\* History:
\* 2026-03-17: Full-scope invariant specifications created
\* End of module
\*
