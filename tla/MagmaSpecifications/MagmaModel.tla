----------------------------- MODULE MagmaModel -----------------------------
(*
  Concrete magma models for testing.
  Provides specific small magmas for model checking.
*)

EXTENDS Naturals, Sequences, FiniteSets, Magma

(******************************************************************************
* Small Finite Magmas for Testing
******************************************************************************)

\* Trivial magma: single element {0}
M1 ==
    LET S == {0}
        op == [x \in S, y \in S |-> 0]
    IN S

\* Two-element magma: {0, 1}
\* Operation: addition mod 2 (XOR)
M2_XOR ==
    LET S == {0, 1}
        op == [x \in S, y \in S |-> (x + y) % 2]
    IN S

\* Two-element magma: {0, 1}
\* Operation: AND
M2_AND ==
    LET S == {0, 1}
        op == [x \in S, y \in S |-> x * y]
    IN S

\* Two-element magma: {0, 1}
\* Operation: OR
M2_OR ==
    LET S == {0, 1}
        op == [x \in S, y \in S |-> x + y - x * y]
    IN S

\* Three-element cyclic group (Z/3Z)
M3_Z3 ==
    LET S == {0, 1, 2}
        op == [x \in S, y \in S |-> (x + y) % 3]
    IN S

\* Four-element Klein four-group
M4_Klein ==
    LET S == {"e", "a", "b", "c"}
        op == [x, y \in S |->
            CASE x = "e" THEN y
            [] y = "e" THEN x
            [] x = y THEN "e"
            [] x = "a" /\ y = "b" THEN "c"
            [] x = "a" /\ y = "c" THEN "b"
            [] x = "b" /\ y = "c" THEN "a"
            [] x = "b" /\ y = "a" THEN "c"
            [] x = "c" /\ y = "a" THEN "b"
            [] x = "c" /\ y = "b" THEN "a"
        ]
    IN S

(******************************************************************************
* Counterexample Magmas
******************************************************************************)

\* Magma where associativity fails
\* Size 3, defined by Cayley table
\* Verification: (0*1)*2 = 0*2 = 1, but 0*(1*2) = 0*0 = 0, so 1 /= 0.
NonAssociativeMagma ==
    LET S == {0, 1, 2}
        \* Table:
        \*   * | 0 1 2
        \*   --+------
        \*   0 | 0 0 1
        \*   1 | 1 0 0
        \*   2 | 0 1 0
        op == [x \in S, y \in S |->
            CASE x = 0 /\ y = 0 THEN 0
            [] x = 0 /\ y = 1 THEN 0
            [] x = 0 /\ y = 2 THEN 1
            [] x = 1 /\ y = 0 THEN 1
            [] x = 1 /\ y = 1 THEN 0
            [] x = 1 /\ y = 2 THEN 0
            [] x = 2 /\ y = 0 THEN 0
            [] x = 2 /\ y = 1 THEN 1
            [] x = 2 /\ y = 2 THEN 0
        ]
    IN S

\* Magma where commutativity fails
NonCommutativeMagma ==
    LET S == {0, 1, 2}
        \* Non-commutative operation (subtraction-like)
        op == [x \in S, y \in S |-> (x - y) %% 3]
    IN S

(******************************************************************************
* Model Configuration
******************************************************************************)

\* Current magma under test (change this for different models)
CurrentMagma == M2_XOR

\* Current operation
CurrentOp ==
    LET S == {0, 1}
    IN [x \in S, y \in S |-> (x + y) % 2]

\* Helper to check if current magma is associative
IsCurrentAssociative ==
    Associative

\* Helper to check if current magma is commutative
IsCurrentCommutative ==
    Commutative

(******************************************************************************
* Property Checking
******************************************************************************)

\* Check all standard properties for current magma
CheckAllProperties ==
    /\ TypeOK
    /\ IsFiniteMagma
    /\ MagmaSize = 2

=============================================================================
\* History:
\* 2026-03-17: Created concrete magma models
\* End of module
\*
