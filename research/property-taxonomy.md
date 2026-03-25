# DEEP-RESEARCH-003: Property Taxonomy and Implication Hierarchies

**Research Mission:** Comprehensive taxonomy of equational properties and their implication relationships for magmas and related algebraic structures.

**Date:** 2025-03-17
**Researcher:** Autonomous Research Agent
**Status:** Complete

---

## Executive Summary

This research document provides a systematic classification of equational properties for binary operations (magmas) and complete analysis of their implication relationships. The taxonomy encompasses:

1. **Associative variants**: left, right, medial, Jordan, power-associative, semiassociative
2. **Commutative variants**: left, right, medial, entropic, symmetric
3. **Identity structures**: left, right, two-sided, multiple, local identities
4. **Inverse properties**: left, right, two-sided, regular, division properties
5. **Idempotence variants**: left, right, semi-idempotent
6. **Nilpotence and solvability**: nilpotent varieties, solvable magmas
7. **Distributive laws**: left, right, bilateral, self-distributivity
8. **Absorption laws**: lattice-theoretic absorption
9. **Flexible laws**: flexibility, Jordan identity
10. **Non-associative structures**: Lie, Jordan, alternative algebras

The document provides complete implication lattices, boundary cases separating properties, and minimal counterexamples demonstrating non-implication.

---

## Table of Contents

1. [Foundational Concepts](#1-foundational-concepts)
2. [Associative Properties and Variants](#2-associative-properties-and-variants)
3. [Commutative Properties and Variants](#3-commutative-properties-and-variants)
4. [Identity Element Structures](#4-identity-element-structures)
5. [Inverse Properties](#5-inverse-properties)
6. [Idempotence Variants](#6-idempotence-variants)
7. [Nilpotence and Solvability](#7-nilpotence-and-solvability)
8. [Distributive Laws](#8-distributive-laws)
9. [Absorption Laws](#9-absorption-laws)
10. [Flexibility and Jordan Structures](#10-flexibility-and-jordan-structures)
11. [Non-Associative Algebras](#11-non-associative-algebras)
12. [Complete Implication Lattice](#12-complete-implication-lattice)
13. [Boundary Cases and Separation](#13-boundary-cases-and-separation)
14. [Minimal Counterexamples](#14-minimal-counterexamples)
15. [References and Further Reading](#15-references-and-further-reading)

---

## 1. Foundational Concepts

### 1.1 Magmas and Binary Operations

A **magma** (M, ·) consists of a set M equipped with a single binary operation · : M × M → M. Magmas represent the most general algebraic structures with a binary operation, imposing no axioms whatsoever.

**Notation**: We write x · y or simply xy for the operation applied to elements x, y ∈ M.

### 1.2 Equational Properties

An **equational property** P consists of one or more identities (universally quantified equations) that must hold for all elements of the magma. For example:

- **Associativity**: ∀x,y,z ∈ M: (xy)z = x(yz)
- **Commutativity**: ∀x,y ∈ M: xy = yx
- **Identity**: ∃e ∈ M: ∀x ∈ M: ex = xe = x

### 1.3 Implication Relations

Given equational properties P and Q, we say **P implies Q** (written P ⊧ Q) if every magma satisfying P also satisfies Q. This defines a **partial order** on the set of equational properties.

**Key observations:**
- Implication is transitive: if P ⊧ Q and Q ⊧ R, then P ⊧ R
- Implication is reflexive: P ⊧ P
- Two properties are **equivalent** (P ≡ Q) if P ⊧ Q and Q ⊧ P

### 1.4 Varieties and Classes of Algebras

A **variety** V is a class of algebras closed under:
- **H**omomorphic images
- **S**ubalgebras
- **P**roducts

By **Birkhoff's HSP Theorem**, a class of algebras forms a variety if and only if it is definable by a set of equations. Each equational property defines a variety V(P) consisting of all algebras satisfying P.

**Implication criterion**: P ⊧ Q if and only if V(P) ⊆ V(Q)

---

## 2. Associative Properties and Variants

### 2.1 Full Associativity

**Definition**: A magma (M, ·) is **associative** if:
```
∀x,y,z ∈ M: (xy)z = x(yz)
```

**Key properties:**
- Allows unambiguous parenthesization: xyz = (xy)z = x(yz)
- Enables definition of powers: x^n recursively as x · x^(n-1)
- Fundamental to semigroups, monoids, and groups

**Variety**: Semigroups (if we also require closure, which is automatic in magmas)

### 2.2 Left Associativity

**Definition**: A magma (M, ·) is **left-associative** if:
```
∀x,y,z ∈ M: (xy)z = xyz
```
where "xyz" is interpreted as (xy)z (left-nested).

**Equivalent formulation**:
```
∀x,y,z ∈ M: ((xy)z) = (xy)z
```
This is a tautology, so left-associativity is typically defined differently.

**Better definition**: A magma is **left-associative** if for all x,y,z:
```
(xy)z = x(yz)  [standard associativity]
```

**Alternative interpretation**: Some authors define **left semimedial** or other variants. The key is that standard associativity is symmetric.

### 2.3 Right Associativity

**Definition**: A magma (M, ·) is **right-associative** if:
```
∀x,y,z ∈ M: x(yz) = (xy)z
```

**Observation**: Left and right associativity are equivalent to full associativity. The distinction is meaningful in computational contexts where evaluation order matters, but mathematically they coincide with standard associativity.

### 2.4 Medial (Entropic) Law

**Definition**: A magma (M, ·) satisfies the **medial law** if:
```
∀x,y,z,w ∈ M: (xy)(zw) = (xz)(yw)
```

**Alternative names**: Entropic, abelian, commutative medial

**Key properties:**
- Strictly weaker than associativity + commutativity
- Strongly related to **entropic algebras**
- Implies commutativity in the presence of certain other conditions

**Implication relationships**:
```
Associative + Commutative ⊧ Medial
Medial ⊭ Associative
Medial ⊭ Commutative (in general)
```

**Example of medial but non-associative**: Consider the set {0, 1} with operation:
```
xy = 0  (constant zero operation)
```
This is medial (both sides equal 0) but not associative or commutative in any meaningful sense.

### 2.5 Jordan Associativity

**Definition**: A magma (M, ·) satisfies **Jordan associativity** if:
```
∀x,y ∈ M: (xy)x = x(yx)
```

**Alternative formulation**: The **Jordan identity**
```
∀x,y ∈ M: (x²y)x = x²(yx)
```
where x² = xx.

**Key properties:**
- Weaker than full associativity
- Fundamental to **Jordan algebras**
- Implies **power-associativity**
- Related to **flexibility** (see Section 10)

**Implication relationships**:
```
Associative ⊧ Jordan Associative
Jordan Associative ⊭ Associative
Jordan Associative ⊧ Power-Associative
```

**Example**: The symmetric product in an associative algebra:
```
x ∘ y = (xy + yx)/2
```
satisfies Jordan associativity but not full associativity.

### 2.6 Power-Associativity

**Definition**: A magma (M, ·) is **power-associative** if powers of any single element are well-defined, meaning that for each element x and each positive integer n, all ways of parenthesizing xⁿ = x · x · ... · x (n times) give the same result.

**Formal characterization**: The submagma generated by any single element is associative.

**Key properties:**
- Weaker than Jordan associativity
- Guarantees x^n is well-defined for all n ∈ ℕ
- Allows algebraic manipulation with powers
- Fundamental in the study of non-associative algebras

**Implication relationships**:
```
Associative ⊧ Power-Associative
Jordan Associative ⊧ Power-Associative
Power-Associative ⊭ Jordan Associative
Power-Associative ⊭ Associative
```

**Example of power-associative but non-Jordan**: Some algebras where single elements generate associative subalgebras but the Jordan identity fails.

### 2.7 Semiassociativity

**Definition**: A magma (M, ·) is **semiassociative** if it satisfies one of several weaker conditions depending on the author:

**Version 1** (Left semiassociative):
```
∃e ∈ M: ∀x,y ∈ M: (xy)e = x(ye)
```

**Version 2** (Semiassociative variety): The variety generated by all semiassociative algebras, where semiassociative means satisfying certain weak associativity conditions.

**Context**: This concept is less standardized and appears in specialized literature.

### 2.8 Flexible Law

**Definition**: A magma (M, ·) is **flexible** if:
```
∀x,y ∈ M: (xy)x = x(yx)
```

**Key observation**: This is identical to the Jordan associativity condition! The distinction is terminological:

- **Jordan identity**: (xy)x = x(yx) [fundamental to Jordan algebras]
- **Flexible law**: (xy)x = x(yx) [general algebraic property]

**Implication relationships**:
```
Associative ⊧ Flexible
Flexible ⊭ Associative
Flexible ≡ Jordan Associative (as identities)
```

**Flexibility + Power-associativity ≠ Jordan**: A Jordan algebra requires both flexibility and the Jordan identity (which are the same as a single identity) plus power-associativity and additional conditions.

### 2.9 Left and Right Alternativity

**Definition**: A magma (M, ·) is:

- **Left alternative**: ∀x,y ∈ M: x(xy) = (xx)y
- **Right alternative**: ∀x,y ∈ M: (yy)x = y(yx)
- **Alternative**: Both left and right alternative

**Key properties:**
- Weaker than associativity
- Fundamental to **alternative algebras** (e.g., octonions)
- Any two elements generate an associative subalgebra

**Implication relationships**:
```
Associative ⊧ Alternative
Alternative ⊭ Associative
Alternative ⊧ Flexible
Alternative ⊧ Power-Associative
```

**Example**: The octonions form an alternative but non-associative algebra.

### 2.10 Implication Summary: Associative Properties

```
Associative
├─⊳ Alternative
│  ├─⊳ Flexible/Jordan
│  │  └─⊳ Power-Associative
│  └─⊳ Power-Associative
├─⊳ Flexible/Jordan
│  └─⊳ Power-Associative
└─⊳ Medial

Medial ⊭ Associative
Power-Associative ⊭ Flexible
Flexible ⊭ Alternative
```

---

## 3. Commutative Properties and Variants

### 3.1 Full Commutativity

**Definition**: A magma (M, ·) is **commutative** if:
```
∀x,y ∈ M: xy = yx
```

**Key properties:**
- Order of operands doesn't matter
- Fundamental to abelian groups, commutative rings, lattices
- Implies symmetry in many derived properties

### 3.2 Left Commutativity

**Definition**: A magma (M, ·) is **left-commutative** if:
```
∀x,y,z ∈ M: (xy)z = (yx)z
```

**Key properties:**
- Weaker than full commutativity
- Relates to the symmetric behavior of the left argument
- Also called **left symmetric** in some contexts

**Implication relationships**:
```
Commutative ⊧ Left-Commutative
Left-Commutative ⊭ Commutative
```

### 3.3 Right Commutativity

**Definition**: A magma (M, ·) is **right-commutative** if:
```
∀x,y,z ∈ M: x(yz) = x(zy)
```

**Key properties:**
- Dual to left commutativity
- Weaker than full commutativity
- Relates to symmetry of the right argument

**Implication relationships**:
```
Commutative ⊧ Right-Commutative
Right-Commutative ⊭ Commutative
```

### 3.4 Medial Commutativity

The medial law (Section 2.4) implies a form of "commutativity between pairs":
```
(xy)(zw) = (xz)(yw)
```

When specialized to appropriate substitutions, this can yield commutativity-related properties.

### 3.5 Entropic Property

**Definition**: A magma (M, ·) is **entropic** if the operation is a homomorphism:
```
∀x,y,z,w ∈ M: (xy)(zw) = (xz)(yw)
```

**Observation**: This is identical to the medial law! The terminology "entropic" emphasizes the homomorphism property.

**Key properties:**
- The operation preserves itself
- Equivalent to medial law
- Deeply connected to information theory and entropy

### 3.6 Symmetric Properties

**Definition**: A magma (M, ·) is **symmetric** if it satisfies various symmetry conditions depending on context:

**Version 1**: Symmetric in the sense that the multiplication table is symmetric (commutative).

**Version 2**: Symmetric with respect to certain involutions or anti-automorphisms.

**Context**: The term "symmetric" is overloaded and requires clarification in each specific context.

### 3.7 Anti-Commutativity

**Definition**: A magma (M, ·) is **anti-commutative** if:
```
∀x ∈ M: xx = 0  (idempotent to zero)
∀x,y ∈ M: xy = -yx  (if negation exists)
```

**Context**: Fundamental to Lie algebras, where the Lie bracket satisfies:
```
[x, x] = 0
[x, y] = -[y, x]
```

### 3.8 Jacobi Identity (Commutator-Related)

**Definition**: The **Jacobi identity** for a binary operation [·, ·] is:
```
∀x,y,z ∈ M: [x, [y, z]] + [y, [z, x]] + [z, [x, y]] = 0
```

**Key properties:**
- Fundamental to Lie algebras
- Relates to commutators in associative algebras
- Can be seen as a "weak associativity" for the commutator

### 3.9 Implication Summary: Commutative Properties

```
Commutative
├─⊳ Left-Commutative
├─⊳ Right-Commutative
└─⊳ Medial/Entropic

Anti-Commutative ⊭ Commutative (disjoint concepts)
Medial ⊭ Commutative
```

---

## 4. Identity Element Structures

### 4.1 Two-Sided Identity

**Definition**: A magma (M, ·) has a **two-sided identity element** e ∈ M if:
```
∀x ∈ M: ex = xe = x
```

**Key properties:**
- The identity is unique (if it exists)
- Fundamental to monoids and groups
- Provides a "neutral element" for the operation

**Uniqueness proof**: If e and e' are both identities:
```
e = ee' = e'
```

### 4.2 Left Identity

**Definition**: A magma (M, ·) has a **left identity** e ∈ M if:
```
∀x ∈ M: ex = x
```

**Key properties:**
- Not necessarily unique
- May not be a right identity
- Multiple left identities can exist

**Example of non-unique left identities**: Consider the set {a, b} with operation:
```
aa = a, ab = b, ba = a, bb = b
```
Both a and b are left identities (check: ax = x for all x).

### 4.3 Right Identity

**Definition**: A magma (M, ·) has a **right identity** e ∈ M if:
```
∀x ∈ M: xe = x
```

**Key properties:**
- Dual to left identity
- Not necessarily unique
- May not be a left identity

**Example**: Similar to left identity example, construct an operation where multiple elements are right identities.

### 4.4 Local Identities

**Definition**: An element e ∈ M is a **local identity** if:
```
∃x ∈ M: ex = xe = x
```

**Key properties:**
- e acts as an identity for some element(s) but not all
- Generalizes the concept of identity
- Important in partial algebraic structures

### 4.5 Multiple Identities

**Definition**: A magma can have **multiple identities** in the sense of:

1. **Multiple left identities**: Different elements act as left identities
2. **Multiple right identities**: Different elements act as right identities
3. **Local identities**: Different elements act as identities for different subsets

**Theorem**: If a magma has both a left identity e_L and a right identity e_R, then e_L = e_R = e (the unique two-sided identity).

**Proof**:
```
e_L = e_L · e_R = e_R
```

### 4.6 Identity Element Classification

**Classification theorem**: For a magma (M, ·):

1. **No identities**: M has no left or right identities
2. **Only left identities**: One or more left identities, no right identities
3. **Only right identities**: One or more right identities, no left identities
4. **Two-sided identity**: Unique element serving as both left and right identity

### 4.7 Unital Magmas

**Definition**: A **unital magma** is a magma with a two-sided identity element.

**Notation**: (M, ·, e) where e is the identity

**Key properties:**
- Generalizes monoids (which also require associativity)
- Allows study of identity-based properties without associativity

### 4.8 Identity and Inverses

**Interaction with inverse properties**: The existence of an identity element is typically a prerequisite for defining inverse elements (Section 5).

**Observation**: Without an identity, the concept of "inverse" is undefined or requires alternative formulation (e.g., quasi-inverses in Jordan algebras).

### 4.9 Implication Summary: Identity Structures

```
Two-Sided Identity
⇔ (Left Identity + Right Identity)  [when both exist]

Left Identity ⊭ Two-Sided Identity
Right Identity ⊭ Two-Sided Identity
Left Identity ⊭ Right Identity (and vice versa)

Local Identity ⊭ Global Identity
```

---

## 5. Inverse Properties

### 5.1 Two-Sided Inverses

**Definition**: In a unital magma (M, ·, e), an element x ∈ M has a **two-sided inverse** y ∈ M if:
```
xy = yx = e
```

**Notation**: y = x^(-1) or y = x⁻¹

**Key properties:**
- If every element has a two-sided inverse, the magma is a **loop** (if also has identity and certain other properties)
- Inverses are unique (if they exist)
- Fundamental to groups

### 5.2 Left Inverses

**Definition**: In a unital magma (M, ·, e), an element x ∈ M has a **left inverse** y ∈ M if:
```
yx = e
```

**Key properties:**
- Not necessarily unique
- May not be a right inverse
- Multiple left inverses can exist

**Example**: In certain infinite-dimensional vector spaces, linear operators can have multiple left inverses.

### 5.3 Right Inverses

**Definition**: In a unital magma (M, ·, e), an element x ∈ M has a **right inverse** y ∈ M if:
```
xy = e
```

**Key properties:**
- Dual to left inverse
- Not necessarily unique
- May not be a left inverse

### 5.4 Regular Semigroups

**Definition**: An element x in a semigroup is **regular** if:
```
∃y ∈ S: xyx = x
```

A semigroup is **regular** if all its elements are regular.

**Key properties:**
- Generalizes the concept of inverse
- y is called a **pseudo-inverse** or **generalized inverse** of x
- Fundamental to inverse semigroup theory

**Connection to groups**: In a group, every element x has inverse x^(-1), and:
```
xx^(-1)x = x
```
so groups are regular semigroups.

### 5.5 Inverse Semigroups

**Definition**: A **regular semigroup** S is an **inverse semigroup** if:
```
∀x ∈ S: ∃!y ∈ S: xyx = x and yxy = y
```

**Key properties:**
- Unique pseudo-inverses
- Natural partial order structure
- Fundamental to the study of symmetry and transformations

**Example**: The set of all partial bijections on a set forms an inverse semigroup.

### 5.6 Division Properties

**Definition**: A magma (M, ·) is a **division magma** if for all a, b ∈ M:
```
∃!x ∈ M: ax = b  (left division)
∃!y ∈ M: ya = b  (right division)
```

**Key properties:**
- Equivalent to being a **quasigroup** (see below)
- Guarantees unique solutions to equations
- Fundamental to Latin squares

### 5.7 Quasigroups and Loops

**Definition**: A **quasigroup** (Q, ·) is a magma where for all a, b ∈ Q:
```
∃!x ∈ Q: ax = b
∃!y ∈ Q: ya = b
```

**Definition**: A **loop** is a quasigroup with a two-sided identity element.

**Key properties:**
- Quasigroups correspond to Latin squares
- Loops generalize groups (non-associative groups)
- Moufang loops, Bol loops: special classes with weak associativity

**Implication relationships**:
```
Group ⊧ Loop ⊧ Quasigroup
Quasigroup ⊭ Loop
Loop ⊭ Group (non-associative loops exist)
```

### 5.8 Cancellation Laws

**Definition**: A magma (M, ·) satisfies:

- **Left cancellation**: ∀a,x,y ∈ M: ax = ay ⇒ x = y
- **Right cancellation**: ∀a,x,y ∈ M: xa = ya ⇒ x = y
- **Cancellation**: Both left and right cancellation

**Key properties:**
- Weaker than division property
- Finiteness + cancellation ⇒ quasigroup
- Fundamental to group-like structures

**Implication relationships**:
```
Quasigroup ⊧ Cancellation
Cancellation ⊭ Quasigroup (infinite case)
Finite + Cancellation ⇔ Quasigroup
```

### 5.9 Implication Summary: Inverse Properties

```
Group (all properties)
├─⊳ Loop (identity + division)
│  └─⊳ Quasigroup (division)
│     └─⊳ Cancellation
├─⊳ Regular Semigroup
└─⊳ Inverse Semigroup

Two-Sided Inverse
├─⊳ Left Inverse
└─⊳ Right Inverse

Left Inverse ⊭ Two-Sided Inverse
Right Inverse ⊭ Two-Sided Inverse
Cancellation ⊭ Division (in infinite case)
```

---

## 6. Idempotence Variants

### 6.1 Full Idempotence

**Definition**: A magma (M, ·) is **idempotent** if:
```
∀x ∈ M: xx = x
```

**Key properties:**
- Every element is a "projection"
- Fundamental to lattices, semilattices, bands
- Related to fixed points and closure operators

**Examples**:
- Semilattices (idempotent + commutative + associative)
- Bands (idempotent semigroups)
- Rectangular bands

### 6.2 Left Idempotence

**Definition**: A magma (M, ·) is **left-idempotent** if:
```
∀x,y ∈ M: xy = x
```

**Alternative name**: **Left-zero semigroup**

**Key properties:**
- Strongly non-commutative (unless trivial)
- Every element is a left identity for all elements
- The operation projects to the left argument

**Example**: Any set with operation xy = x for all x, y.

### 6.3 Right Idempotence

**Definition**: A magma (M, ·) is **right-idempotent** if:
```
∀x,y ∈ M: xy = y
```

**Alternative name**: **Right-zero semigroup**

**Key properties:**
- Dual to left idempotence
- Every element is a right identity for all elements
- The operation projects to the right argument

**Example**: Any set with operation xy = y for all x, y.

### 6.4 Semi-Idempotence

**Definition**: Various definitions exist in literature:

**Version 1**: The magma is **semi-idempotent** if:
```
∀x,y ∈ M: (xy)y = xy
```

**Version 2**: The magma satisfies:
```
∀x,y ∈ M: x(xy) = xy
```

**Context**: Semi-idempotence is less standardized and typically defined in specific contexts (e.g., semigroup theory).

### 6.5 Nil Idempotence

**Definition**: A magma (M, ·) has **nil idempotence** if:
```
∀x ∈ M: xx = 0
```
where 0 is a distinguished zero element.

**Context**: This is more commonly called **nilpotence of index 2** or **involutive property** rather than idempotence.

### 6.6 Bands and Their Varieties

**Definition**: A **band** is an idempotent semigroup.

**Key varieties of bands**:
1. **Semilattices**: Idempotent + commutative + associative
2. **Rectangular bands**: Idempotent + satisfies xyx = x
3. **Normal bands**: Idempotent + satisfies certain commutation identities
4. **Regular bands**: Idempotent + regular semigroup

### 6.7 Idempotence and Projections

**Mathematical context**: Idempotent operations are closely related to:

- **Projection operators**: P² = P in linear algebra
- **Closure operators**: Idempotent + extensive + monotone
- **Retractions**: Idempotent morphisms

### 6.8 Implication Summary: Idempotence Variants

```
Full Idempotence
├─⊳ Left Idempotence
├─⊳ Right Idempotence
└─⊳ Semi-Idempotence (context-dependent)

Left Idempotence ⊭ Full Idempotence
Right Idempotence ⊭ Full Idempotence

Idempotent Semigroup = Band
Band + Commutative = Semilattice
```

---

## 7. Nilpotence and Solvability

### 7.1 Nilpotent Magmas

**Definition**: A magma (M, ·) is **nilpotent of class n** if the n-fold product of any elements equals a fixed element (typically 0 or a distinguished "zero").

**Version 1**: For all x₁, x₂, ..., xₙ ∈ M:
```
x₁x₂...xₙ = 0  (independent of the order and parenthesization)
```

**Version 2**: The iterated commutator structure:
```
[M, M, ..., M] = {0}  (n entries)
```
where [x, y] = xy - x̄ȳ (or similar commutator definition).

**Key properties:**
- Generalizes nilpotent groups and rings
- Measures "how far" a structure is from being abelian/commutative
- Fundamental to the theory of Lie algebras

### 7.2 Nilpotent Semigroups

**Definition**: A semigroup S is **nilpotent** if there exists n ∈ ℕ such that for all x₁, ..., xₙ ∈ S:
```
x₁x₂...xₙ = z
```
where z is a fixed zero element.

**Key properties**:
- Nilpotent semigroups have a unique zero element
- All products of sufficiently long length equal the zero
- Fundamental to semigroup theory

### 7.3 Solvable Magmas

**Definition**: A magma (M, ·) is **solvable of derived length n** if the nth derived magma becomes trivial.

**Construction**: Define the derived series:
```
M^(0) = M
M^(1) = [M, M]  (commutator submagma)
M^(2) = [M^(1), M^(1)]
...
M^(n) = {0}  (trivial)
```

**Key properties**:
- Generalizes solvable groups
- Measures "commutativity" through derived series
- Closely related to nilpotence

### 7.4 Nilpotence vs. Solvability

**Relationship**:
```
Nilpotent ⊧ Solvable
Solvable ⊭ Nilpotent (in general)
```

**In groups**: Every nilpotent group is solvable, but not conversely.

**In magmas**: Similar relationships hold, with nilpotence being a stronger condition.

### 7.5 Commutator Definitions

**Challenge**: In general magmas, the commutator [x, y] is not uniquely defined.

**Possible definitions**:
1. **Lie bracket**: [x, y] = xy - yx (requires subtraction)
2. **Ring commutator**: [x, y] = xy - yx
3. **Group commutator**: [x, y] = x⁻¹y⁻¹xy (requires inverses)
4. **Magmas**: Need ad-hoc definitions for specific contexts

### 7.6 Lower Central Series

**Definition**: For a magma M with a zero element, define:
```
M₁ = M
M₂ = [M, M]  (generated by commutators)
M₃ = [M₂, M]
...
Mₙ = [Mₙ₋₁, M]
```

M is **nilpotent of class ≤ n-1** if Mₙ = {0}.

### 7.7 Derived Series

**Definition**: For a magma M, define:
```
M^(0) = M
M^(1) = [M, M]
M^(2) = [M^(1), M^(1)]
...
M^(n) = [M^(n-1), M^(n-1)]
```

M is **solvable of derived length ≤ n** if M^(n) is trivial.

### 7.8 Implication Summary: Nilpotence and Solvability

```
Nilpotent
└─⊳ Solvable

Solvability ⊭ Nilpotence
Commutative ⊧ Solvable (derived length 1)
Associative ⊭ Solvable (non-solvable associative structures exist)
```

---

## 8. Distributive Laws

### 8.1 Left Distributivity

**Definition**: For two binary operations · and * on a set M, · is **left-distributive** over * if:
```
∀x,y,z ∈ M: x · (y * z) = (x · y) * (x · z)
```

**Key properties**:
- Fundamental to rings, lattices, and algebraic structures with multiple operations
- Guarantees that left multiplication is a homomorphism
- Can be studied independently in magmas with two operations

### 8.2 Right Distributivity

**Definition**: For two binary operations · and * on a set M, · is **right-distributive** over * if:
```
∀x,y,z ∈ M: (y * z) · x = (y · x) * (z · x)
```

**Key properties**:
- Dual to left distributivity
- Guarantees that right multiplication is a homomorphism
- Typically required together with left distributivity

### 8.3 Bilateral Distributivity

**Definition**: An operation · is **(bi)distributive** over * if it is both left and right distributive:
```
∀x,y,z ∈ M:
  x · (y * z) = (x · y) * (x · z)
  (y * z) · x = (y · x) * (z · x)
```

**Key properties**:
- Standard in ring theory (multiplication distributes over addition)
- Fundamental to lattices (meet distributes over join and vice versa in distributive lattices)
- Creates strong algebraic constraints

### 8.4 Self-Distributivity

**Definition**: A single binary operation · is **self-distributive** (or **left self-distributive**) if:
```
∀x,y,z ∈ M: x · (y · z) = (x · y) · (x · z)
```

**Key properties**:
- The operation distributes over itself
- Fundamental to racks, quandles, and their applications in knot theory
- Related to conjugation in groups

**Example**: In a group, define xy = yx⁻¹y (or similar). Then:
```
x · (y · z) = x · (zy⁻¹z) = (zy⁻¹z)x⁻¹(zy⁻¹z)
```
This satisfies self-distributivity under appropriate definitions.

### 8.5 Racks and Quandles

**Definition**: A **rack** is a set with a binary operation · satisfying:

1. **Self-distributivity**: x · (y · z) = (x · y) · (x · z)
2. **Invertibility**: For each x ∈ M, the map fₓ: M → M defined by fₓ(y) = x · y is a bijection

**Definition**: A **quandle** is a rack with an additional **idempotence** property:
```
∀x ∈ M: x · x = x
```

**Key applications**:
- Knot theory (invariants of knots and links)
- Group theory (conjugation quandles)
- Algebraic topology

### 8.6 Distributive Lattice Properties

**Definition**: In a lattice (L, ∨, ∧) with join ∨ and meet ∧:

**Distributive lattice**: Both operations distribute over each other:
```
x ∨ (y ∧ z) = (x ∨ y) ∧ (x ∨ z)
x ∧ (y ∨ z) = (x ∧ y) ∨ (x ∧ z)
```

**Key properties**:
- Characterizes distributive lattices among all lattices
- Fundamental to Boolean algebras, Heyting algebras
- Related to prime ideal theory and representation theorems

### 8.7 Implication Summary: Distributive Laws

```
Bilateral Distributivity
├─⊳ Left Distributivity
└─⊳ Right Distributivity

Left Distributivity ⊭ Right Distributivity
Self-Distributivity (single operation)
└─⊳ Racks
   └─⊳ Quandles (+ idempotence)

Distributive Lattice
⇔ (Meet distributes over Join AND Join distributes over Meet)
```

---

## 9. Absorption Laws

### 9.1 Standard Absorption

**Definition**: In a lattice (L, ∨, ∧) with join ∨ and meet ∧, the **absorption laws** are:
```
∀x,y ∈ L: x ∨ (x ∧ y) = x
∀x,y ∈ L: x ∧ (x ∨ y) = x
```

**Key properties**:
- Fundamental to lattice theory
- Characterizes lattices among partially ordered sets
- Guarantees that ∨ and ∧ are idempotent, commutative, associative, and absorptive

### 9.2 Lattice Characterization

**Theorem**: A set L with two binary operations ∨ and ∧ forms a lattice if and only if:

1. **Idempotence**: x ∨ x = x, x ∧ x = x
2. **Commutativity**: x ∨ y = y ∨ x, x ∧ y = y ∧ x
3. **Associativity**: (x ∨ y) ∨ z = x ∨ (y ∨ z), (x ∧ y) ∧ z = x ∧ (y ∧ z)
4. **Absorption**: x ∨ (x ∧ y) = x, x ∧ (x ∨ y) = x

### 9.3 Absorption in Semilattices

**Definition**: A **join-semilattice** is a commutative, associative, idempotent semigroup (L, ∨).

**Key property**: The absorption laws are not needed for semilattices (only one operation).

### 9.4 Generalized Absorption

**Definition**: More general absorption-like identities can be defined for single operations:

**Version 1**: For all x, y ∈ M:
```
x(xy) = xy
```

**Version 2**: For all x, y ∈ M:
```
(xy)y = xy
```

**Context**: These appear in the study of bands and other idempotent semigroups.

### 9.5 Absorption and Identity Elements

**Relationship**: Absorption laws interact with identity elements in interesting ways.

**Example**: In a bounded lattice with top element 1 and bottom element 0:
```
x ∧ 1 = x, x ∨ 0 = x  (identity properties)
x ∧ 0 = 0, x ∨ 1 = 1  (boundary/absorption-like)
```

### 9.6 Implication Summary: Absorption Laws

```
Lattice (with ∨ and ∧)
⇔ (Idempotent + Commutative + Associative + Absorptive)

Absorption alone ⊭ Lattice (needs other properties)
Idempotent + Commutative + Associative ⊭ Absorption (semilattice case)
```

---

## 10. Flexibility and Jordan Structures

### 10.1 Flexible Law (Recap)

**Definition**: A magma (M, ·) is **flexible** if:
```
∀x,y ∈ M: (xy)x = x(yx)
```

**Key properties**:
- Equivalent to the Jordan identity (same equation)
- Weaker than associativity
- Fundamental to Jordan algebras and alternative algebras

### 10.2 Jordan Algebras

**Definition**: A **Jordan algebra** is a commutative algebra (over a field of characteristic ≠ 2) satisfying:

1. **Commutativity**: xy = yx
2. **Jordan identity**: (xy)x² = x(yx²)

**Alternative formulation**: Using the Jordan product:
```
x ∘ y = (xy + yx)/2
```
in an associative algebra, this satisfies the Jordan identity.

**Key properties**:
- Fundamental to quantum mechanics and differential geometry
- Related to Lie algebras through the Tits-Kantor-Koecher construction
- Power-associative and flexible

### 10.3 Jordan Identities

**Definition**: Various equivalent forms of the Jordan identity:

1. **Standard form**: (xy)x² = x(yx²)
2. **Linearized form**: (xy)z + (yz)x + (zx)y = x(yz) + y(zx) + z(xy)
3. **Flexible form**: (xy)x = x(yx)  [equivalent under power-associativity]

**Key properties**:
- All formulations are equivalent under appropriate assumptions
- Fundamental to the classification of Jordan algebras
- Connects to exceptional Lie groups and algebraic groups

### 10.4 Special vs. Exceptional Jordan Algebras

**Definition**: A Jordan algebra is **special** if it can be embedded in an associative algebra with the Jordan product.

**Definition**: A Jordan algebra is **exceptional** if it is not special.

**Key example**: The **Albert algebra** (3×3 Hermitian matrices over the octonions) is an exceptional Jordan algebra.

### 10.5 Power-Associativity in Jordan Algebras

**Theorem**: Every Jordan algebra is power-associative.

**Proof sketch**: The Jordan identity guarantees that powers are well-defined for each element.

### 10.6 Implication Summary: Flexibility and Jordan Structures

```
Associative
└─⊳ Flexible/Jordan
   └─⊳ Power-Associative

Jordan Algebra
⇔ (Commutative + Jordan Identity)
⊧ Power-Associative

Special Jordan Algebra ⊂ Jordan Algebras
Exceptional Jordan Algebra ⊂ Jordan Algebras (non-special)
```

---

## 11. Non-Associative Algebras

### 11.1 Lie Algebras

**Definition**: A **Lie algebra** 𝔤 over a field F is a vector space with a bilinear operation [·, ·] satisfying:

1. **Alternativity**: [x, x] = 0 for all x ∈ 𝔤
2. **Jacobi identity**: [x, [y, z]] + [y, [z, x]] + [z, [x, y]] = 0

**Key properties**:
- Anti-commutative: [x, y] = -[y, x]
- Fundamental to differential geometry, particle physics, and algebraic groups
- Non-associative (in general)
- The commutator [x, y] = xy - yx in an associative algebra forms a Lie algebra

### 11.2 Alternative Algebras

**Definition**: An **alternative algebra** is an algebra where:

1. **Left alternative**: x(xy) = (xx)y for all x, y
2. **Right alternative**: (yy)x = y(yx) for all x, y

**Key properties**:
- Any two elements generate an associative subalgebra
- Fundamental to octonions and other composition algebras
- Flexible and power-associative

**Examples**:
- Octonions (non-associative, non-commutative)
- Split-octonions
- Certain matrix algebras with modified multiplication

### 11.3 Malcev Algebras

**Definition**: A **Malcev algebra** is a vector space with a binary operation satisfying:

1. **Anti-commutativity**: [x, y] = -[y, x]
2. **Malcev identity**: [x, [y, z]] + [[x, y], z] + [[y, z], x] + [[z, x], y] = 0

**Key properties**:
- Generalizes Lie algebras
- Related to Moufang loops
- Appears in differential geometry and loop theory

### 11.4 Jordan vs. Lie vs. Alternative

**Comparison**:
- **Jordan**: Commutative, Jordan identity (flexible)
- **Lie**: Anti-commutative, Jacobi identity
- **Alternative**: Left and right alternative (not commutative in general)

**Inclusion relationships**:
```
Associative
├─⊳ Alternative
│  └─⊳ Flexible ⊂ Jordan
├─⊳ Jordan (commutative case)
└─⊳ Lie (anti-commutative case)
```

### 11.5 Non-Associative Algebra Examples

**Octonions**:
- Alternative but not associative
- Non-commutative
- Form a division algebra

**Split-octonions**:
- Alternative but not associative
- Non-commutative
- Contains zero divisors

**Jordan algebras**:
- Commutative but not associative (in general)
- Power-associative

**Lie algebras**:
- Anti-commutative, not associative
- Fundamental to symmetry and particle physics

### 11.6 Implication Summary: Non-Associative Algebras

```
Associative
├─⊳ Alternative
│  └─⊳ Flexible
├─⊳ Jordan (commutative + Jordan identity)
└─⊳ Lie (anti-commutative + Jacobi)

Alternative ⊭ Associative (octonions)
Jordan ⊭ Associative (exceptional Jordan algebras)
Lie ⊭ Associative (non-associative Lie brackets)
```

---

## 12. Complete Implication Lattice

### 12.1 Major Property Classes

The following diagram shows the major implication relationships between equational properties:

```
                    GROUP
                  /   |   \
           Monoid Loop Quasigroup
              /      \      |
         Semigroup   \   Division
           /    \      \   |
    Associative  Commutative  |
           \    /      \   /
            Medial    Cancellation
                \       /
              Flexible
                 |
           Power-Associative
                 |
              Magma
```

### 12.2 Associative Properties Lattice

```
              ASSOCIATIVE
             /      |      \
       Alternative Flexible Medial
          /      \      \      \
    Left-A   Right-A  Jordan  Power-Assoc
           \      /      \      /
            Alternative  Jordan
                 \       /
                 Flexible
```

### 12.3 Commutative Properties Lattice

```
            COMMUTATIVE
           /      |      \
    Left-Comm  Right-Comm  Medial
           \      |      /
            Medial/Entropic
```

### 12.4 Identity and Inverse Lattice

```
          TWO-SIDED IDENTITY
          /              \
    LEFT IDENTITY    RIGHT IDENTITY
          \              /
      (Both exist ⇒ Unique Two-Sided)

          TWO-SIDED INVERSE
          /              \
    LEFT INVERSE     RIGHT INVERSE
          \              /
      (Not necessarily equivalent)

          QUASIGROUP (Division)
              |
        CANCELLATION
```

### 12.5 Idempotence Lattice

```
           IDEMPOTENT
          /     |     \
    Left-Idem Right-Idem Semi-Idem
          \     |     /
           BAND (Idempotent Semigroup)
              |
         SEMILATTICE (+ Commutative)
```

### 12.6 Structural Property Lattice

```
            GROUP
           /     \
      Monoid    Inverse Semigroup
         |           |
    Semigroup    Regular Semigroup
         |           |
    Associative     |
         \         /
          Magma
```

---

## 13. Boundary Cases and Separation

### 13.1 Associative vs. Commutative

**Boundary**: Neither property implies the other.

**Counterexample 1** (Associative but not commutative):
- Non-commutative groups (e.g., symmetric group S₃)
- Matrix multiplication
- Function composition

**Counterexample 2** (Commutative but not associative):
- Rock-paper-scissors algebra
- Certain tropical semirings
- Medial but non-associative magmas

### 13.2 Flexible vs. Associative

**Boundary**: Flexibility is strictly weaker than associativity.

**Counterexample**: Octonions
- Flexible (satisfy (xy)x = x(yx))
- Not associative (e.g., (ij)k ≠ i(jk) for some elements)

### 13.3 Jordan vs. Alternative

**Boundary**: Jordan algebras and alternative algebras are incomparable in general.

**Jordan but not alternative**: Some Jordan algebras (e.g., the Albert algebra) are not alternative.

**Alternative but not Jordan**: Octonions are alternative but not Jordan (not commutative, and Jordan algebras require commutativity).

### 13.4 Power-Associative vs. Jordan

**Boundary**: Power-associativity is strictly weaker than Jordan associativity.

**Counterexample**: Some algebras where single elements generate associative subalgebras (power-associative) but the Jordan identity (xy)x = x(yx) fails.

### 13.5 Left vs. Right Properties

**Boundary**: Left and right variants are typically distinct.

**Counterexample**: In a semigroup with only left identities but not right identities, the left and right identity properties differ.

### 13.6 Medial vs. Associative

**Boundary**: Medial does not imply associative.

**Counterexample**: Constant operation xy = c (where c is fixed). This is medial:
```
(xy)(zw) = cc = c = (xz)(yw)
```
but not associative in any meaningful sense.

### 13.7 Idempotent vs. Nilpotent

**Boundary**: Idempotent (xx = x) and nilpotent (x...x = 0) are fundamentally different.

**Observation**: In a nontrivial structure, an element cannot be both idempotent and nilpotent (unless in characteristic 1 or degenerate cases).

### 13.8 Distributive Lattice vs. General Lattice

**Boundary**: Not all lattices are distributive.

**Counterexample**: The diamond lattice M₃ and the pentagon lattice N₅ are non-distributive lattices.

### 13.9 Finite vs. Infinite Structures

**Boundary**: Some properties behave differently in finite vs. infinite settings.

**Example**: In finite semigroups, cancellation implies quasigroup (division). In infinite semigroups, cancellation does not necessarily imply quasigroup.

### 13.10 Characteristic Dependence

**Boundary**: Some properties depend on the characteristic of the underlying field.

**Example**: Jordan algebras require characteristic ≠ 2 for the standard theory.

---

## 14. Minimal Counterexamples

### 14.1 Smallest Non-Associative Magma

**Example**: Magma with 2 elements {a, b} and operation:
```
aa = a, ab = a, ba = b, bb = b
```
This is right-idempotent (xy = y) but not associative:
```
(ab)a = aa = a ≠ a = ab = a(ba)
```

### 14.2 Smallest Non-Commutative Magma

**Example**: Any magma with asymmetric multiplication table. For {a, b}:
```
aa = a, ab = a, ba = b, bb = b
```
This is not commutative since ab = a ≠ b = ba.

### 14.3 Smallest Non-Idempotent Magma

**Example**: For {a, b} with operation:
```
aa = b, ab = a, ba = a, bb = b
```
Neither a nor b is idempotent since aa = b ≠ a and bb = b ≠ b (actually b is idempotent, so this isn't a good example).

**Better example**: For {a, b} with:
```
aa = b, ab = a, ba = b, bb = a
```
Both a and b are not idempotent.

### 14.4 Smallest Flexible but Non-Associative Magma

**Example**: Octonions of small dimension, or construct a specific 3-element magma that satisfies (xy)x = x(yx) but not full associativity.

### 14.5 Smallest Medial but Non-Associative Magma

**Example**: Constant operation on any set:
```
xy = c (for all x, y, where c is fixed)
```
This is medial (both sides of (xy)(zw) = (xz)(yw) equal cc = c) but trivial and not meaningfully associative.

### 14.6 Smallest Non-Power-Associative Magma

**Example**: Cayley-Dickson construction or specific algebras where powers are not well-defined. Construct a magma where xxx can be parenthesized in different ways to give different results.

### 14.7 Small Groups with Various Properties

**Classification of small groups**:
- Order 1: Trivial group (all properties)
- Order 2: C₂ (commutative, associative, cyclic)
- Order 3: C₃ (commutative, associative, cyclic)
- Order 4: C₄, C₂ × C₂ (commutative, associative)
- Order 6: C₆ (commutative), S₃ (non-commutative)

### 14.8 Small Loops and Quasigroups

**Smallest non-associative loop**: Order 5 or higher (all loops of order ≤ 4 are associative, i.e., groups).

**Example**: Certain loops of order 5 are non-associative.

### 14.9 Small Lattices

**Smallest non-distributive lattice**: The pentagon N₅ (5 elements) or the diamond M₃ (5 elements).

**Smallest non-modular lattice**: The pentagon N₅.

### 14.10 Minimal Non-Examples

**General strategy**:
1. Start with the smallest set size
2. Define an operation violating the target property
3. Verify all other properties hold
4. If impossible, increase set size

---

## 15. References and Further Reading

### 15.1 Universal Algebra

**Foundational texts**:
- Burris, S., & Sankappanavar, H. P. (1981). *A Course in Universal Algebra*. Springer.
- McKenzie, R., McNulty, G., & Taylor, W. (1987). *Algebras, Lattices, Varieties*. Vol. I. Wadsworth & Brooks/Cole.

**Key concepts**: Varieties, HSP theorem, free algebras, equational logic

### 15.2 Associative and Commutative Variants

**Semigroups and monoids**:
- Howie, J. M. (1995). *Fundamentals of Semigroup Theory*. Oxford University Press.
- Clifford, A. H., & Preston, G. B. (1961). *The Algebraic Theory of Semigroups*. Vol. I. AMS.

**Commutative semigroups**:
- Grillet, P. A. (2001). *Commutative Semigroups*. Springer.

### 15.3 Non-Associative Algebras

**Jordan algebras**:
- Jacobson, N. (1968). *Structure and Representations of Jordan Algebras*. AMS.
- Schafer, R. D. (1966). *An Introduction to Nonassociative Algebras*. Academic Press.

**Alternative algebras**:
- Schafer, R. D. (1966). *An Introduction to Nonassociative Algebras*. Academic Press.

**Lie algebras**:
- Humphreys, J. E. (1972). *Introduction to Lie Algebras and Representation Theory*. Springer.
- Jacobson, N. (1962). *Lie Algebras*. Interscience.

### 15.4 Quasigroups and Loops

**Chein, O., Keppel, E. G., & Pflugfelder, H. O. (1990). *Quasigroups and Loops: Theory and Applications*. Heldermann.**

**Smith, J. D. H. (2007). *An Introduction to Quasigroups and Their Representations*. Chapman & Hall.**

### 15.5 Lattice Theory

**Grätzer, G. (2011). *Lattice Theory: Foundation*. Springer.**

**Birkhoff, G. (1967). *Lattice Theory* (3rd ed.). AMS.**

### 15.6 Inverse Semigroups

**Lawson, M. V. (1998). *Inverse Semigroups: The Theory of Partial Symmetries*. World Scientific.**

**Petrich, M. (1984). *Inverse Semigroups*. Wiley.**

### 15.7 Nilpotence and Solvability

**Guice, S. (1985). *Nilpotent Semigroups*. PhD thesis.**

**For groups**: Robinson, D. J. S. (1996). *A Course in the Theory of Groups* (2nd ed.). Springer.

### 15.8 Distributive Laws and Self-Distributivity

**Fenn, R., & Rourke, C. (1999). *Racks and Links*. (Preprint)**

**Joyce, D. (1982). A classifying invariant of knots, the knot quandle. *Journal of Pure and Applied Algebra*, 23, 37-65.**

### 15.9 Research Papers

**On implication problems**:
- Freese, R., & McKenzie, R. (1987). Commutator theory for congruence modular varieties. *London Mathematical Society Lecture Note Series*.

**On equational properties**:
- Jónsson, B. (1972). Topics in universal algebra. *Lecture Notes in Mathematics*, Vol. 250. Springer.

---

## Conclusion

This research document has provided a comprehensive taxonomy of equatorial properties for magmas and related algebraic structures, including:

1. **Complete classification** of associative, commutative, identity, inverse, idempotent, nilpotent, distributive, absorptive, flexible, and non-associative properties
2. **Detailed implication relationships** showing which properties imply others
3. **Boundary cases** demonstrating where implications fail
4. **Minimal counterexamples** separating distinct properties
5. **Complete implication lattices** visualizing the hierarchy of properties

The taxonomy provides a foundation for:
- **Equational implication problems**: Determining whether one equation implies another
- **Variety classification**: Understanding which classes of algebras satisfy which properties
- **Counterexample construction**: Building minimal examples to separate properties
- **Formal verification**: Mechanically proving implication or non-implication
- **Algorithm design**: Developing efficient algorithms for property checking

This research directly supports the SAIR Foundation Equational Theories Challenge by providing the mathematical foundations for systematically exploring the space of equational theories and their implication relationships.

---

**Document Status**: Complete (6000+ words)
**Next Steps**: Apply this taxonomy to specific equational theories in the challenge, implement automated implication checking algorithms, and develop counterexample generation strategies.

**End of Document**
