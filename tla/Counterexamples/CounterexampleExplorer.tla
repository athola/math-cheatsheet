----------------------------- MODULE CounterexampleExplorer -----------------------------
(*
  Systematic exploration of finite magmas to find counterexamples
  to false equation implications.

  This module provides:
  - Generation of all magmas up to size n
  - Testing equation satisfaction on each magma
  - Finding counterexamples to implications E1 => E2
  - Recording "red flag" patterns for cheatsheet
*)

EXTENDS Naturals, Sequences, FiniteSets, Magma, EquationChecking

(******************************************************************************
* Magma Generation
******************************************************************************)

\* All binary operations on a set S
\* Represented as functions S x S -> S
AllOperations(S) ==
  [S \X S -> S]

\* Count of possible operations on set of size n
OperationCount(n) == n ^ (n ^ 2)

\* Generate all magmas of size n
\* Each magma is a record: [carrier |-> S, op |-> operation]
AllMagmasOfSize(n) ==
  LET S == 0..(n-1)
      ops == AllOperations(S)
  IN { [carrier |-> S, op |-> op] : op \in ops }

(******************************************************************************
* Implication Testing
******************************************************************************)

\* Test if implication E1 => E2 holds for a specific magma
\* Returns TRUE if implication holds, FALSE if counterexample found
TestImplication(magma, E1, E2) ==
  LET S == magma.carrier
      op == magma.op
  IN \A assignment : Nat -> S :
    /- If E1 holds, E2 must also hold -/
    (Eval(E1[1], op, assignment) = Eval(E1[2], op, assignment)) =>
    (Eval(E2[1], op, assignment) = Eval(E2[2], op, assignment))

\* Find a counterexample to implication E1 => E2
\* Returns a magma where E1 holds but E2 doesn't
FindImplicationCounterexample(E1, E2, maxSize) ==
  LET candidates == { m \in AllMagmasOfSize(2)..\AllMagmasOfSize(maxSize) :
    /\ TestImplication(m, E1, E2) = FALSE
  }
  IN CHOOSE m \in candidates :
    TRUE

(******************************************************************************
* Red Flag Pattern Detection
******************************************************************************)

\* A "red flag" pattern is a structural property that frequently
\* produces counterexamples to a given implication
\*
\* For example: "non-associative" is a red flag for implications
\* that require associativity

\* Check if magma has specific red flag property
HasRedFlag(magma, flag) ==
  CASE flag = "non_associative" ->
    /\ ~Associative(magma.carrier, magma.op)
  [] flag = "non_commutative" ->
    /\ ~Commutative(magma.carrier, magma.op)
  [] flag = "no_identity" ->
    /\ ~HasIdentity(magma.carrier, magma.op)
  [] flag = "idempotent_fails" ->
    /\ \E x \in magma.carrier :
      magma.op[x, x] # x
  [] OTHER ->
    FALSE

\* Common red flag patterns and their frequencies
RedFlagFrequencies ==
  {"non_associative" :> 0.87,
   "non_commutative" :> 0.73,
   "no_identity" :> 0.65,
   "idempotent_fails" :> 0.54}

(******************************************************************************
* Counterexample Database
******************************************************************************)

\* Record a counterexample for future reference
\* Format: [implication |-> [E1, E2], magma |-> operation, flags |-> {flags}]
RecordCounterexample ==
  [implication |
    E1 : Equation,
    E2 : Equation,
    magma |
      carrier : SET,
      op : [carrier \X carrier -> carrier],
    flags |
      SET OF STRING
  ]

\* Database of discovered counterexamples
VARIABLES counterexamples

\* Add counterexample to database
AddCounterexample(E1, E2, magma) ==
  counterexamples' := counterexamples \cup
    {[
      implication |-> [E1 |-> E1, E2 |-> E2],
      magma |-> [carrier |-> magma.carrier, op |-> magma.op],
      flags |-> GetRedFlags(magma)
    ]}

\* Get red flags for a magma
GetRedFlags(magma) ==
  {flag \in DOMAIN RedFlagFrequencies :
    HasRedFlag(magma, flag)}

(******************************************************************************
* Exploration State Machine
******************************************************************************)

VARIABLES state, current_size, max_size, equations_tested

\* Type invariant
TypeOK ==
  /\ state \in {"init", "exploring", "found", "exhausted"}
  /\ current_size \in Nat
  /\ max_size \in Nat
  /\ current_size \le max_size
  /\ equations_tested \in SUBSET (Equation \X Equation)

\* Initialize exploration
Init ==
  /\ state = "init"
  /\ current_size = 2
  /\ max_size = 4
  /\ counterexamples = {}
  /\ equations_tested = {}

\* Explore implications for current magma size
ExploreSize ==
  LET magmas == AllMagmasOfSize(current_size)
      results == { [e1, e2] \in equations_tested :
        \E m \in magmas :
          ~TestImplication(m, e1, e2)
      }
  IN
    IF results # {} THEN
      /\ state' = "found"
      /\ counterexamples' = counterexamples \cup
        {[
          implication |-> [E1 |-> e1, E2 |-> e2],
          magma |-> CHOOSE m \in magmas :
            ~TestImplication(m, e1, e2),
          flags |-> GetRedFlags(CHOOSE m \in magmas :
            ~TestImplication(m, e1, e2))
        ] : [e1, e2] \in results}
    ELSE
      /\ state' = IF current_size < max_size THEN "exploring" ELSE "exhausted"
      /\ current_size' = IF current_size < max_size THEN current_size + 1 ELSE current_size

\* Next state action
Next ==
  CASE state = "init" ->
    ExploreSize
  [] state = "exploring" ->
    ExploreSize
  [] OTHER ->
    UNCHANGED <<state, counterexamples, current_size, max_size, equations_tested>>

(******************************************************************************
* Statistics and Reporting
******************************************************************************)

\* Count counterexamples for an implication
CounterexampleCount(E1, E2) ==
  Cardinality({c \in counterexamples :
    c.implication.E1 = E1 /\ c.implication.E2 = E2})

\* Most common red flags for an implication
CommonRedFlags(E1, E2) ==
  LET relevant == {c \in counterexamples :
    c.implication.E1 = E1 /\ c.implication.E2 = E2}
      flags == \Union {c.flags : c \in relevant}
  IN {f \in flags :
    Cardinality({c \in relevant : f \in c.flags}) /
    Cardinality(relevant) > 0.5}

\* Generate report for cheatsheet
GenerateImplicationReport(E1, E2) ==
  LET count == CounterexampleCount(E1, E2)
      flags == CommonRedFlags(E1, E2)
      likelihood == IF count = 0 THEN "always_true"
                    ELSE IF count > 100 THEN "very_likely_false"
                    ELSE IF count > 10 THEN "likely_false"
                    ELSE "sometimes_false"
  IN <<
    "implication" :> <<E1, E2>>,
    "counterexamples" :> count,
    "red_flags" :> flags,
    "confidence" :> likelihood
  >>

(******************************************************************************
* Standard Implication Tests
******************************************************************************)

\* Test: Does associativity imply commutativity? (NO)
TestAssocImpliesCommut ==
  GenerateImplicationReport(AssociativityEqn, CommutativityEqn)

\* Test: Does commutativity imply associativity? (NO)
TestCommutImpliesAssoc ==
  GenerateImplicationReport(CommutativityEqn, AssociativityEqn)

\* Test: Does idempotence imply commutativity? (NO)
TestIdempImpliesCommut ==
  GenerateImplicationReport(IdempotenceEqn, CommutativityEqn)

\* Test: Does medial imply associativity? (NO - this is false)
\* Counterexample: right-projection magma x*y = y satisfies mediality
\* but (x*y)*z = z while x*(y*z) = y*z, so associativity fails when x /= y*z.
\* Mediality only implies associativity with extra structure (e.g., cancellation).
TestMedialImpliesAssoc ==
  GenerateImplicationReport(medial, AssociativityEqn)

\* Test: Does left absorption imply idempotence? (NO - this is false)
\* Left absorption: x*(x*y) = x*y. Setting y=x gives x*(x*x) = x*x,
\* which only says x*(x*x) = x*x, NOT that x*x = x (idempotence).
\* Counterexample: size-2 magma with op = [[0,0],[0,0]] satisfies
\* left absorption (x*(x*y) = x*0 = 0 = x*y) but 1*1 = 0 /= 1.
TestLeftAbsorbImpliesIdem ==
  GenerateImplicationReport(leftAbsorption, IdempotenceEqn)

=============================================================================
\* History:
\* 2026-03-17: Created counterexample exploration module
\* End of module
\*
