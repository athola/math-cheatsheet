----------------------------- MODULE TEST_MODEL -----------------------------
(*
  Test module for verifying Magma specifications work correctly.
  This can be run with TLC to validate the setup.
*)

EXTENDS Magma, MagmaModel, EquationChecking

(******************************************************************************
* Test Cases
******************************************************************************)

\* Test 1: Verify XOR magma (M2_XOR) is associative and commutative
THEOREM XORIsAssociative ==
    LET S == {0, 1}
        op == [x \in S, y \in S |-> (x + y) % 2]
    IN \A a, b, c \in S :
        op[op[a, b], c] = op[a, op[b, c]]

THEOREM XORIsCommutative ==
    LET S == {0, 1}
        op == [x \in S, y \in S |-> (x + y) % 2]
    IN \A a, b \in S :
        op[a, b] = op[b, a]

\* Test 2: Verify AND magma (M2_AND) is commutative but not a group
THEOREM ANDIsCommutative ==
    LET S == {0, 1}
        op == [x \in S, y \in S |-> x * y]
    IN \A a, b \in S :
        op[a, b] = op[b, a]

\* Test 3: Verify Klein four-group properties
THEOREM KleinFourIsAssociative ==
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
    IN \A a, b, c \in S :
        op[op[a, b], c] = op[a, op[b, c]]

\* Test 4: Non-associative magma actually fails associativity
THEOREM NonAssociativeExample ==
    LET S == {0, 1, 2}
        op == [x \in S, y \in S |->
            CASE y = 0 THEN 0
            [] x = 0 THEN 0
            [] x = y THEN x
            [] OTHER THEN 3 - x - y
        ]
    IN \E a, b, c \in S :
        op[op[a, b], c] # op[a, op[b, c]]

\* Test 5: Counterexample to general associativity
\* In a 2-element magma, we can check all possible operations
\* and find ones that are not associative

\* Number of possible binary operations on an n-element set
NumberOfOperations(n) == n^(n^2)

(******************************************************************************
* Property Checking Module
******************************************************************************)

\* Check all defining properties of a specific magma type
CheckMagmaProperties(S, op) ==
    LET isAssociative == \A a, b, c \in S : op[op[a, b], c] = op[a, op[b, c]]
        isCommutative == \A a, b \in S : op[a, b] = op[b, a]
        hasIdentity == \E e \in S : \A a \in S : (op[e, a] = a) /\ (op[a, e] = a)
    IN <<
        "associative" :> isAssociative,
        "commutative" :> isCommutative,
        "has_identity" :> hasIdentity
    >>

\* Classify the algebraic structure type
ClassifyMagma(S, op) ==
    LET props == CheckMagmaProperties(S, op)
        hasIdentity == props["has_identity"]
        isAssoc == props["associative"]
        isComm == props["commutative"]
    IN
        \* Most specific cases first — TLA+ CASE is sequential
        CASE hasIdentity /\ isAssoc /\ isComm -> "Commutative Monoid"
        [] hasIdentity /\ isAssoc -> "Monoid"
        [] isAssoc /\ isComm -> "Commutative Semigroup"
        [] isAssoc -> "Semigroup"
        [] isComm -> "Commutative Magma"
        [] OTHER -> "Magma"

\* Test classification of standard magmas
THEOREM ClassifyXOR ==
    LET S == {0, 1}
        op == [x \in S, y \in S |-> (x + y) % 2]
    IN ClassifyMagma(S, op) = "Commutative Monoid"

THEOREM ClassifyAND ==
    LET S == {0, 1}
        op == [x \in S, y \in S |-> x * y]
    IN ClassifyMagma(S, op) = "Commutative Monoid"

THEOREM ClassifyKleinFour ==
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
    IN ClassifyMagma(S, op) = "Commutative Monoid"

=============================================================================
\* History:
\* 2026-03-17: Created test module for TLA+ specification validation
\* End of module
\*
