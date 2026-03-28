import EquationalTheories.Basic
import EquationalTheories.Core

/-!
# Property-Based Invariant Tests for Equational Theories

This module verifies full-scope algebraic invariants using Lean's type system
as a property-based testing framework. Each theorem is a universally quantified
statement that Lean's kernel verifies for ALL possible inputs.

## BDD Scenarios
- Feature: Implication reflexivity and transitivity
- Feature: Term evaluation determinism
- Feature: Equation satisfaction well-definedness
- Feature: Property independence witnesses
-/

namespace EquationalTheories.Invariants

open EquationalTheories

/-! ## Feature: Implication is a preorder (reflexive + transitive) -/

/-- Given: ANY equation e
    Then: e implies itself (reflexivity). -/
theorem implication_reflexivity (e : Equation) : implies e e := by
  intro α m h
  exact h

/-- Given: ANY three equations e₁, e₂, e₃
    Then: (e₁ ⇒ e₂) ∧ (e₂ ⇒ e₃) → (e₁ ⇒ e₃) (transitivity). -/
theorem implication_transitivity {e₁ e₂ e₃ : Equation}
    (h₁₂ : implies e₁ e₂) (h₂₃ : implies e₂ e₃) : implies e₁ e₃ := by
  intro α m h₁
  exact h₂₃ m (h₁₂ m h₁)

/-- Equivalence is reflexive. -/
theorem equivalence_reflexivity (e : Equation) : equivalent e e :=
  ⟨implication_reflexivity e, implication_reflexivity e⟩

/-- Equivalence is symmetric. -/
theorem equivalence_symmetry {e₁ e₂ : Equation}
    (h : equivalent e₁ e₂) : equivalent e₂ e₁ :=
  ⟨h.2, h.1⟩

/-- Equivalence is transitive. -/
theorem equivalence_transitivity {e₁ e₂ e₃ : Equation}
    (h₁₂ : equivalent e₁ e₂) (h₂₃ : equivalent e₂ e₃) : equivalent e₁ e₃ :=
  ⟨implication_transitivity h₁₂.1 h₂₃.1, implication_transitivity h₂₃.2 h₁₂.2⟩

/-! ## Feature: Term evaluation consistency -/

/-- Given: ANY term t, operation op, and assignment σ
    Then: satisfies(op, σ, var n) = σ(n). -/
theorem satisfies_var {α : Type} (op : α → α → α) (σ : Nat → α) (n : Nat) :
    satisfies op σ (Term.var n) = σ n := by
  rfl

/-- Given: ANY terms l, r, operation op, and assignment σ
    Then: satisfies(op, σ, l * r) = op(satisfies(op, σ, l), satisfies(op, σ, r)). -/
theorem satisfies_app {α : Type} (op : α → α → α) (σ : Nat → α) (l r : Term) :
    satisfies op σ (Term.app l r) = op (satisfies op σ l) (satisfies op σ r) := by
  rfl

/-! ## Feature: Equation structural invariants -/

/-- Term size is non-negative (trivially true by Nat). -/
theorem term_size_nonneg (t : Term) : t.size ≥ 0 := Nat.zero_le _

/-- Variables of a variable term is exactly {n}. -/
theorem vars_of_var (n : Nat) : (Term.var n).vars = {n} := by rfl

/-- Variables of an application is the union of sub-term variables. -/
theorem vars_of_app (l r : Term) :
    (Term.app l r).vars = l.vars ∪ r.vars := by rfl

/-! ## Feature: Standard equation well-formedness -/

/-- Associativity equation uses exactly variables {0, 1, 2}. -/
theorem assoc_vars : StdEqn.associativity.lhs.vars ∪ StdEqn.associativity.rhs.vars = {0, 1, 2} := by
  simp [StdEqn.associativity, Term.vars]
  ext x
  simp [Finset.mem_union, Finset.mem_insert, Finset.mem_singleton]

/-- Commutativity equation uses exactly variables {0, 1}. -/
theorem comm_vars : StdEqn.commutativity.lhs.vars ∪ StdEqn.commutativity.rhs.vars = {0, 1} := by
  simp [StdEqn.commutativity, Term.vars]
  ext x
  simp [Finset.mem_union, Finset.mem_insert, Finset.mem_singleton]
  omega

/-- Idempotence equation uses exactly variable {0}. -/
theorem idemp_vars : StdEqn.idempotence.lhs.vars ∪ StdEqn.idempotence.rhs.vars = {0} := by
  simp [StdEqn.idempotence, Term.vars]

/-! ## Feature: Concrete magma property verification

Verify properties on concrete finite magmas (Bool as carrier).
These serve as compile-time witnesses that our definitions are correct. -/

/-- XOR on Bool is commutative. -/
theorem bool_xor_commutative :
    MagmaSatisfies (⟨xor⟩ : Magma Bool) StdEqn.commutativity := by
  intro σ
  simp [satisfies, StdEqn.commutativity]
  cases σ 0 <;> cases σ 1 <;> rfl

/-- XOR on Bool is associative. -/
theorem bool_xor_associative :
    MagmaSatisfies (⟨xor⟩ : Magma Bool) StdEqn.associativity := by
  intro σ
  simp [satisfies, StdEqn.associativity]

/-- AND on Bool is commutative. -/
theorem bool_and_commutative :
    MagmaSatisfies (⟨(· && ·)⟩ : Magma Bool) StdEqn.commutativity := by
  intro σ
  simp [satisfies, StdEqn.commutativity]
  cases σ 0 <;> cases σ 1 <;> rfl

/-- AND on Bool is idempotent. -/
theorem bool_and_idempotent :
    MagmaSatisfies (⟨(· && ·)⟩ : Magma Bool) StdEqn.idempotence := by
  intro σ
  simp [satisfies, StdEqn.idempotence]

/-! ## Feature: Non-implication witnesses with explicit countermodels

Concrete finite magmas on Bool (= Fin 2) that witness non-implications
between standard equations. Each proof constructs an explicit countermodel
and a specific variable assignment that separates the two properties. -/

/-- NAND on Bool: a ◇ b = ¬(a ∧ b). Commutative but not associative. -/
private def nandMagma : Magma Bool := ⟨fun a b => !(a && b)⟩

/-- Left projection on Bool: a ◇ b = a. Associative and idempotent but not commutative. -/
private def lprojMagma : Magma Bool := ⟨fun a _ => a⟩

private theorem nandMagma_comm : MagmaSatisfies nandMagma StdEqn.commutativity := by
  intro σ
  simp [satisfies, StdEqn.commutativity, nandMagma]
  cases σ 0 <;> cases σ 1 <;> rfl

private theorem nandMagma_not_assoc : ¬ MagmaSatisfies nandMagma StdEqn.associativity := by
  intro h
  have := h (fun n => if n = 2 then true else false)
  simp [satisfies, StdEqn.associativity, nandMagma] at this

private theorem lprojMagma_assoc : MagmaSatisfies lprojMagma StdEqn.associativity := by
  intro σ
  simp [satisfies, StdEqn.associativity, lprojMagma]

private theorem lprojMagma_idemp : MagmaSatisfies lprojMagma StdEqn.idempotence := by
  intro σ
  simp [satisfies, StdEqn.idempotence, lprojMagma]

private theorem lprojMagma_not_comm : ¬ MagmaSatisfies lprojMagma StdEqn.commutativity := by
  intro h
  have := h (fun n => if n = 0 then false else true)
  simp [satisfies, StdEqn.commutativity, lprojMagma] at this

/-- Commutativity does NOT imply associativity.
    Witness: NAND on Bool is commutative but not associative. -/
theorem comm_not_implies_assoc : ¬ implies StdEqn.commutativity StdEqn.associativity := by
  intro h
  exact nandMagma_not_assoc (h nandMagma nandMagma_comm)

/-- Associativity does NOT imply commutativity.
    Witness: left projection on Bool is associative but not commutative. -/
theorem assoc_not_implies_comm : ¬ implies StdEqn.associativity StdEqn.commutativity := by
  intro h
  exact lprojMagma_not_comm (h lprojMagma lprojMagma_assoc)

/-- Idempotence does NOT imply commutativity.
    Witness: left projection on Bool is idempotent but not commutative. -/
theorem idemp_not_implies_comm : ¬ implies StdEqn.idempotence StdEqn.commutativity := by
  intro h
  exact lprojMagma_not_comm (h lprojMagma lprojMagma_idemp)

/-! ## Feature: Term size invariants -/

/-- Size of a variable is 0. -/
theorem var_size_zero (n : Nat) : (Term.var n).size = 0 := rfl

/-- Size of an application is 1 + sum of subtree sizes. -/
theorem app_size (l r : Term) :
    (Term.app l r).size = 1 + l.size + r.size := rfl

/-- Associativity equation has size 2 on each side. -/
theorem assoc_lhs_size : StdEqn.associativity.lhs.size = 2 := rfl
theorem assoc_rhs_size : StdEqn.associativity.rhs.size = 2 := rfl

/-- Commutativity equation has size 1 on each side. -/
theorem comm_lhs_size : StdEqn.commutativity.lhs.size = 1 := rfl
theorem comm_rhs_size : StdEqn.commutativity.rhs.size = 1 := rfl

end EquationalTheories.Invariants
