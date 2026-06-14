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

\* Equation satisfaction for concrete encoded equations is NOT defined in
\* this module. The earlier `EquationHolds(Eqn) == TRUE` placeholder was a
\* vacuous stub (it claimed every equation holds) and has been removed to
\* avoid implying a capability the module does not have. For an actual
\* executable check over size-2 magmas, see Size2Check.tla, which defines
\* IsAssociative / IsCommutative / IsIdempotent directly and is verified
\* by TLC.

(******************************************************************************
* Finite Magma Properties
******************************************************************************)

\* A magma is finite if its carrier set is finite.
\* (The previous version used an undefined `Infinity`; FiniteSets provides
\* the proper predicate IsFiniteSet.)
IsFiniteMagma == IsFiniteSet(S)

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
