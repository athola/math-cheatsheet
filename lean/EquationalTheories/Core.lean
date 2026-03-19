import Mathlib.Data.Finset.Basic
import EquationalTheories.Basic

/-!
# Core Equational Theory

This module defines the foundational concepts for equational logic:
- Terms: algebraic expressions built from variables and operations
- Equations: pairs of terms with implicit universal quantification
- Equation satisfaction: when does a magma satisfy an equation?
- Implication: when does one equation imply another?
-/

namespace EquationalTheories

/-! ## Terms -/

/-- A term in the language of magmas is either a variable or an application of the binary operation.
    Variables are represented by natural numbers (de Bruijn indices or similar). -/
inductive Term where
  | var : Nat → Term      -- Variable x₀, x₁, x₂, ...
  | app : Term → Term → Term  -- Application t₁ * t₂
  deriving Repr

instance : Inhabited Term where
  default := Term.var 0

/-- Pretty printing for terms -/
def Term.toString (t : Term) : String :=
  match t with
  | Term.var n => s!"x{n}"
  | Term.app l r =>
    match l, r with
    | Term.app _ _, Term.app _ _ => s!"({l.toString} * {r.toString})"
    | Term.app _ _, _ => s!"({l.toString} * {r.toString})"
    | _, Term.app _ _ => s!"{l.toString} * ({r.toString})"
    | _, _ => s!"{l.toString} * {r.toString}"

instance : ToString Term := ⟨Term.toString⟩

/-- Variables appearing in a term -/
def Term.vars (t : Term) : Finset Nat :=
  match t with
  | Term.var n => {n}
  | Term.app l r => l.vars ∪ r.vars

/-- Size of a term (number of operation symbols) -/
def Term.size (t : Term) : Nat :=
  match t with
  | Term.var _ => 0
  | Term.app l r => 1 + l.size + r.size

/-! ## Equations -/

/-- An equation is a pair of terms (lhs = rhs).
    Variables are implicitly universally quantified. -/
structure Equation where
  lhs : Term
  rhs : Term
  deriving Repr

instance : ToString Equation where
  toString e := s!"{e.lhs} = {e.rhs}"

/-! ## Equation Satisfaction -/

/-- Evaluate a term under a variable assignment using a magma's operation.
    This is defined by structural recursion on the term. -/
def satisfies {α : Type} (op : α → α → α) (assignment : Nat → α) : Term → α
  | Term.var n => assignment n
  | Term.app l r =>
    let lhs := satisfies op assignment l
    let rhs := satisfies op assignment r
    op lhs rhs

/-- A magma satisfies an equation if all variable assignments make the equation true. -/
def MagmaSatisfies {α : Type} (m : Magma α) (e : Equation) : Prop :=
  ∀ assignment : Nat → α,
    satisfies m.op assignment e.lhs = satisfies m.op assignment e.rhs

/-! ## Standard Equations -/

namespace StdEqn

  -- Associativity: (x * y) * z = x * (y * z)
  def associativity : Equation :=
    ⟨Term.app (Term.app (Term.var 0) (Term.var 1)) (Term.var 2),
     Term.app (Term.var 0) (Term.app (Term.var 1) (Term.var 2))⟩

  -- Commutativity: x * y = y * x
  def commutativity : Equation :=
    ⟨Term.app (Term.var 0) (Term.var 1),
     Term.app (Term.var 1) (Term.var 0)⟩

  -- Idempotence: x * x = x
  def idempotence : Equation :=
    ⟨Term.app (Term.var 0) (Term.var 0),
     Term.var 0⟩

  -- Left identity with parameter e: e * x = x
  -- Note: This checks whether a *specific* e is a left identity.
  -- Existence of a left identity (∃e, ∀x, e*x = x) is not expressible
  -- as a single universally-quantified equation. The Python Magma.has_identity()
  -- correctly searches over all elements; use this definition with a concrete
  -- witness when e is already known.
  def leftIdentity (e : Term) : Equation :=
    ⟨Term.app e (Term.var 0), Term.var 0⟩

  -- Right identity with parameter e: x * e = x
  -- Same caveat as leftIdentity: parameterized by a specific candidate e.
  def rightIdentity (e : Term) : Equation :=
    ⟨Term.app (Term.var 0) e, Term.var 0⟩

  -- Left distributivity: x * (y * z) = (x * y) * (x * z)
  def leftDistributivity : Equation :=
    ⟨Term.app (Term.var 0) (Term.app (Term.var 1) (Term.var 2)),
     Term.app (Term.app (Term.var 0) (Term.var 1)) (Term.app (Term.var 0) (Term.var 2))⟩

  -- Right distributivity: (x * y) * z = (x * z) * (y * z)
  def rightDistributivity : Equation :=
    ⟨Term.app (Term.app (Term.var 0) (Term.var 1)) (Term.var 2),
     Term.app (Term.app (Term.var 0) (Term.var 2)) (Term.app (Term.var 1) (Term.var 2))⟩

  -- Medial: (x * y) * (z * w) = (x * z) * (y * w)
  def medial : Equation :=
    ⟨Term.app (Term.app (Term.var 0) (Term.var 1)) (Term.app (Term.var 2) (Term.var 3)),
     Term.app (Term.app (Term.var 0) (Term.var 2)) (Term.app (Term.var 1) (Term.var 3))⟩

  -- Left semimedial: (x * y) * (x * z) = x * (y * z)
  def leftSemimedial : Equation :=
    ⟨Term.app (Term.app (Term.var 0) (Term.var 1)) (Term.app (Term.var 0) (Term.var 2)),
     Term.app (Term.var 0) (Term.app (Term.var 1) (Term.var 2))⟩

  -- Left absorption: x * (x * y) = x * y
  def leftAbsorption : Equation :=
    ⟨Term.app (Term.var 0) (Term.app (Term.var 0) (Term.var 1)),
     Term.app (Term.var 0) (Term.var 1)⟩

  -- Right absorption: (x * y) * y = x * y
  def rightAbsorption : Equation :=
    ⟨Term.app (Term.app (Term.var 0) (Term.var 1)) (Term.var 1),
     Term.app (Term.var 0) (Term.var 1)⟩

  -- Entropic: (x * y) * (z * w) = (x * z) * (y * w) [same as medial]
  def entropic : Equation := medial

end StdEqn

/-! ## Equation Implication -/

/-- Equation e₁ implies equation e₂ if every magma satisfying e₁ also satisfies e₂.
    This is the central notion for the STEP dataset.
    Note: quantifies over Type (= Type 0). For finite magma competition use this
    suffices; for full generality, use `Type*` or explicit universe variables. -/
def implies (e₁ e₂ : Equation) : Prop :=
  ∀ {α : Type} (m : Magma α),
    MagmaSatisfies m e₁ → MagmaSatisfies m e₂

/-- Equivalence of equations: e₁ and e₂ are equivalent if each implies the other -/
def equivalent (e₁ e₂ : Equation) : Prop :=
  (implies e₁ e₂) ∧ (implies e₂ e₁)

/-! ## Common Implication Patterns -/

namespace TrivialImplications

  -- Every equation implies itself (reflexivity)
  theorem implies_refl (e : Equation) : implies e e := by
    intros α m h₁
    assumption

  -- Implication is transitive
  theorem implies_trans {e₁ e₂ e₃ : Equation}
    (h₁₂ : implies e₁ e₂) (h₂₃ : implies e₂ e₃) : implies e₁ e₃ := by
    intros α m h₁
    apply h₂₃
    apply h₁₂
    assumption

  -- Implication is equivalent to logical implication of satisfaction
  theorem implies_iff {e₁ e₂ : Equation} :
    (implies e₁ e₂) ↔
    (∀ (α : Type) (m : Magma α), MagmaSatisfies m e₁ → MagmaSatisfies m e₂) := by
    rfl

end TrivialImplications

open StdEqn TrivialImplications

end EquationalTheories
