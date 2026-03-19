------------------------- MODULE InvariantCheck -------------------------
(*
  TLC model checking configuration for verifying magma invariants.

  This module instantiates Invariants.tla with concrete small magmas
  and checks all invariants via TLC's exhaustive state exploration.

  Usage:
    java -jar tla2tools.jar -config InvariantCheck.cfg InvariantCheck.tla

  BDD Scenarios:
    Feature: Exhaustive invariant verification for size-2 magmas
    Scenario: TLC checks ALL 16 operations on {0,1}
*)

EXTENDS Naturals, FiniteSets, Invariants

(******************************************************************************
* Size-2 Exhaustive Checks
*
* For S = {0, 1}, there are exactly 2^4 = 16 possible binary operations.
* TLC can enumerate all of them and verify every invariant.
******************************************************************************)

\* ── Test 1: XOR magma ────────────────────────────────────────

THEOREM XOR_Closure ==
    LET S == {0, 1}
        op == [p \in S \X S |-> (p[1] + p[2]) % 2]
    IN \A a, b \in S : op[<<a, b>>] \in S

THEOREM XOR_Associative ==
    LET S == {0, 1}
        op == [p \in S \X S |-> (p[1] + p[2]) % 2]
    IN \A a, b, c \in S :
        op[<<op[<<a, b>>], c>>] = op[<<a, op[<<b, c>>]>>]

THEOREM XOR_Commutative ==
    LET S == {0, 1}
        op == [p \in S \X S |-> (p[1] + p[2]) % 2]
    IN \A a, b \in S : op[<<a, b>>] = op[<<b, a>>]

THEOREM XOR_HasIdentity ==
    LET S == {0, 1}
        op == [p \in S \X S |-> (p[1] + p[2]) % 2]
    IN \E e \in S : \A a \in S :
        (op[<<e, a>>] = a) /\ (op[<<a, e>>] = a)

\* ── Test 2: AND magma ────────────────────────────────────────

THEOREM AND_Closure ==
    LET S == {0, 1}
        op == [p \in S \X S |-> p[1] * p[2]]
    IN \A a, b \in S : op[<<a, b>>] \in S

THEOREM AND_Idempotent ==
    LET S == {0, 1}
        op == [p \in S \X S |-> p[1] * p[2]]
    IN \A a \in S : op[<<a, a>>] = a

\* ── Test 3: Left projection (associative, not commutative) ──

THEOREM LeftProj_AssocNotComm ==
    LET S == {0, 1}
        op == [p \in S \X S |-> p[1]]
    IN /\ (\A a, b, c \in S :
            op[<<op[<<a, b>>], c>>] = op[<<a, op[<<b, c>>]>>])
       /\ (\E a, b \in S : op[<<a, b>>] /= op[<<b, a>>])

\* ── Test 4: Property counts ─────────────────────────────────

THEOREM Size2_Counts ==
    /\ CountAssociativeSize2
    /\ CountCommutativeSize2
    /\ CountIdempotentSize2
    /\ CountIdentitySize2

\* ── Test 5: All invariants for Z/3Z cyclic group ────────────

THEOREM Z3_AllInvariants ==
    LET S == {0, 1, 2}
        op == [p \in S \X S |-> (p[1] + p[2]) % 3]
    IN /\ (\A a, b \in S : op[<<a, b>>] \in S)         \* Closure
       /\ (\A a, b, c \in S :                            \* Associative
            op[<<op[<<a, b>>], c>>] = op[<<a, op[<<b, c>>]>>])
       /\ (\A a, b \in S : op[<<a, b>>] = op[<<b, a>>]) \* Commutative
       /\ (\E e \in S : \A a \in S :                     \* Has identity
            op[<<e, a>>] = a /\ op[<<a, e>>] = a)

=============================================================================
\* History:
\* 2026-03-17: Invariant checking model created
\* End of module
\*
