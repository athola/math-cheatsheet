/-!
# Basic Equational Theory Structures

This module defines the foundational algebraic structures:
- Magma: a set with a binary operation
- AssociativeMagma: semigroup
- CommutativeMagma: commutative binary operation
- Monoid: associative with identity
- Group: monoid with inverses
-/

namespace EquationalTheories

/-- A Magma is a set with a binary operation.
    This is the most basic algebraic structure. -/
structure Magma (Carrier : Type) where
  op : Carrier → Carrier → Carrier

/-- An associative magma (semigroup) -/
structure AssociativeMagma (Carrier : Type) where
  op : Carrier → Carrier → Carrier
  assoc : ∀ a b c, op (op a b) c = op a (op b c)

/-- A commutative magma -/
structure CommutativeMagma (Carrier : Type) where
  op : Carrier → Carrier → Carrier
  comm : ∀ a b, op a b = op b a

/-- A monoid: associative magma with identity -/
structure MonoidStr (Carrier : Type) where
  op : Carrier → Carrier → Carrier
  e : Carrier
  id_left : ∀ a, op e a = a
  id_right : ∀ a, op a e = a
  assoc : ∀ a b c, op (op a b) c = op a (op b c)

/-- A group: monoid with inverses -/
structure Group (Carrier : Type) extends MonoidStr Carrier where
  inv : Carrier → Carrier
  inv_left : ∀ a, op (inv a) a = e
  inv_right : ∀ a, op a (inv a) = e

end EquationalTheories
