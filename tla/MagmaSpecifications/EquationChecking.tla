--------------------------- MODULE EquationChecking ---------------------------
(*
  Module for checking equation satisfaction in magmas.
  Provides tools for verifying implications between equations.
*)

EXTENDS Naturals, Sequences, FiniteSets, Magma

(******************************************************************************
* Term Representation
******************************************************************************)

\* Terms are represented as sequences:
\* "x" is a variable
\* ["*", t1, t2] represents (t1 * t2) where t1, t2 are terms

VARIABLES VarAssignment  (* Maps variable names to elements of S *)

(******************************************************************************
* Term Evaluation
******************************************************************************)

\* Evaluate a term given a variable assignment
RECURSIVE Eval(_)

\* Variable: look up in assignment
Eval([name]) ==
    IF IsSequence(name) THEN
        CASE name[1] = "*" \* It's an operation application
            LET op1 == Eval(name[2])
                op2 == Eval(name[3])
            IN op[op1, op2]
        ELSE
            \* Simple variable name (as string)
            VarAssignment[name]
    ELSE
        \* Atomic value (shouldn't happen in our encoding)
        name

(******************************************************************************
* Equation Satisfaction
******************************************************************************)

\* An equation is satisfied if for all variable assignments,
\* the LHS equals the RHS
EquationSatisfied(eqn) ==
    LET lhs == eqn[1]
        rhs == eqn[2]
        vars == GetVariables(lhs) \cup GetVariables(rhs)
    IN \A assign \in AllAssignments(vars) :
        Eval(lhs) = Eval(rhs)

\* Get all variables in a term
RECURSIVE GetVariables(_)

GetVariables(term) ==
    IF IsSequence(term) THEN
        IF Len(term) = 1 THEN
            {term}  \* Variable
        ELSE
            GetVariables(term[2]) \cup GetVariables(term[3])
    ELSE
        {}  \* Not a sequence (constant value)

\* All possible assignments of variables to S
AllAssignments(vars) ==
    [vars -> S]

(******************************************************************************
* Counterexample Finding
******************************************************************************)

\* Find a counterexample to an equation
FindCounterexample(eqn) ==
    LET lhs == eqn[1]
        rhs == eqn[2]
        vars == GetVariables(lhs) \cup GetVariables(rhs)
        allAssigns == AllAssignments(vars)
    IN CHOOSE assign \in allAssigns :
        /\ Eval(lhs) # Eval(rhs)

\* Check if E1 implies E2 (E1 => E2)
\* E1 implies E2 if every magma satisfying E1 also satisfies E2
\* For a specific magma, we check: if E1 holds, does E2 hold?
ImplicationHolds(E1, E2) ==
    EquationSatisfied(E1) => EquationSatisfied(E2)

\* Find counterexample to implication E1 => E2
\* This is a state where E1 holds but E2 doesn't
FindImplicationCounterexample(E1, E2) ==
    CHOOSE assign \in AllAssignments(
        GetVariables(E1[1]) \cup GetVariables(E1[2]) \cup
        GetVariables(E2[1]) \cup GetVariables(E2[2])
    ) :
        /\ Eval(E1[1]) = Eval(E1[2])  \* E1 holds
        /\ Eval(E2[1]) # Eval(E2[2])  \* E2 doesn't hold

(******************************************************************************
* Common Equation Templates
******************************************************************************)

\* Associativity: (x*y)*z = x*(y*z)
AssociativityEqn ==
    [["*", ["*", ["x"], ["y"]], ["z"]],
     ["*", ["x"], ["*", ["y"], ["z"]]]]

\* Commutativity: x*y = y*x
CommutativityEqn ==
    [["*", ["x"], ["y"]],
     ["*", ["y"], ["x"]]]

\* Left identity with e: e*x = x
LeftIdentityEqn(e) ==
    [["*", [e], ["x"]],
     ["x"]]

\* Right identity with e: x*e = x
RightIdentityEqn(e) ==
    [["*", ["x"], [e]],
     ["x"]]

\* Idempotence: x*x = x
IdempotenceEqn ==
    [["*", ["x"], ["x"]],
     ["x"]]

\* Left cancellation: x*y = x*z => y = z
\* This requires implication structure
LeftCancellationEqn ==
    \* Encoded as: for all x,y,z, (x*y = x*z) => (y = z)
    \* This is higher-order and requires special handling
    [["*", ["x"], ["y"]],
     ["*", ["x"], ["z"]]]

(******************************************************************************
* State Machine for Magma Exploration
******************************************************************************)

VARIABLES state, found_counterexample

\* Type invariant for the state machine
TypeOK ==
    /\ state \in {"searching", "found", "exhausted"}
    /\ found_counterexample \in
        BOOLEAN \cup
        {[op1 \in S, op2 \in S, op3 \in S, assign \in ([String -> S])]}

Init ==
    /\ state = "searching"
    /\ found_counterexample = FALSE

SearchForCounterexample(eqn) ==
    LET counterexample == FindCounterexample(eqn)
    IN
        IF counterexample \in [String -> S] THEN
            /\ state' = "found"
            /\ found_counterexample' = counterexample
        ELSE
            /\ state' = "exhausted"
            /\ found_counterexample' = FALSE

Next ==
    CASE state = "searching" ->
        \* Would have equation as parameter
        /\ TRUE
    [] OTHER ->
        UNCHANGED <<state, found_counterexample>>

=============================================================================
\* History:
\* 2026-03-17: Initial equation checking module
\* End of module
\*
