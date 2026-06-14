------------------------- MODULE InvariantCheck -------------------------
(*
  STATUS: ILLUSTRATIVE PSEUDO-SPEC -- NOT MACHINE-CHECKED.
  This module does NOT check under SANY/TLC (SANY reports ~30 semantic
  errors). Its assertions are written as THEOREM declarations, which TLC
  does not verify -- THEOREMs require a proof system such as TLAPS, not
  the model checker -- so despite the "verification" framing nothing here
  is actually checked. It is retained only to sketch the intended size-2
  enumeration. The executable, TLC-verified spec is Size2Check.tla, which
  performs the real size-2 enumeration (counts and non-implication
  witnesses). Do not cite this file as evidence of model checking.

  This module was intended to instantiate Invariants.tla with concrete
  small magmas and check all invariants via TLC's state exploration.
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
