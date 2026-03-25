----------------------------- MODULE Magma -----------------------------
(*
  Magma specification for finite algebraic structures.
  A magma is a set with a binary operation.
*)

EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS S        (* The carrier set *)
CONSTANTS op       (* Binary operation: S x S -> S *)

(******************************************************************************
* Magma Axioms
******************************************************************************)

\* A magma requires no axioms - any set with binary operation is a magma
MagmaAxiom == TRUE

\* Associativity: (a op b) op c = a op (b op c)
Associative == \A a, b, c \in S :
    op[op[a, b], c] = op[a, op[b, c]]

\* Commutativity: a op b = b op a
Commutative == \A a, b \in S :
    op[a, b] = op[b, a]

\* Identity element exists
HasIdentity == \E e \in S :
    \A a \in S :
        (op[e, a] = a) /\ (op[a, e] = a)

\* Left identity
LeftIdentity(e) == \A a \in S : op[e, a] = a

\* Right identity
RightIdentity(e) == \A a \in S : op[a, e] = a

(******************************************************************************
* Equation Satisfaction
******************************************************************************)

\* Check if a specific equation holds in the magma
\* Equations are encoded as pairs of term representations

\* Example: Check associativity as equation ((x*y)*z) = (x*(y*z))
\* We use a trick: evaluate for all possible values of variables

EquationHolds(Eqn) ==
    \* This would need equation-specific evaluation
    \* Placeholder for equation checking
    TRUE

(******************************************************************************
* Finite Magma Properties
******************************************************************************)

\* A magma is finite if its carrier set is finite
IsFiniteMagma == Cardinality(S) < Infinity

\* Size of the magma
MagmaSize == Cardinality(S)

\* Generate Cayley table for the operation
CayleyTable ==
    [x \in S, y \in S |-> op[x, y]]

(******************************************************************************
* Model Checking Helpers
******************************************************************************)

\* Type correctness invariant
TypeOK ==
    \A a, b \in S : op[a, b] \in S

=============================================================================
\* History:
\* 2026-03-17: Initial magma specification created
\* End of module
\*
