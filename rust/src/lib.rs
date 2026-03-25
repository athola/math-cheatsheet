use pyo3::prelude::*;
use rayon::prelude::*;
use std::sync::atomic::{AtomicU64, Ordering};

/// A finite magma stored as a flat Cayley table.
///
/// The operation table is stored row-major: op(a, b) = table[a * size + b].
/// Using u8 elements since we only enumerate magmas up to size ~4.
#[pyclass]
#[derive(Clone)]
struct Magma {
    #[pyo3(get)]
    size: u8,
    table: Vec<u8>,
}

#[pymethods]
impl Magma {
    #[new]
    fn new(size: u8, operation: Vec<Vec<u8>>) -> PyResult<Self> {
        if size == 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Magma size must be at least 1",
            ));
        }
        let n = size as usize;
        if operation.len() != n {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Operation table rows must match size",
            ));
        }
        let mut table = Vec::with_capacity(n * n);
        for row in &operation {
            if row.len() != n {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "Operation table columns must match size",
                ));
            }
            for &v in row {
                if v >= size {
                    return Err(pyo3::exceptions::PyValueError::new_err(
                        format!("Table entry {} out of range [0, {})", v, size),
                    ));
                }
            }
            table.extend_from_slice(row);
        }
        Ok(Magma { size, table })
    }

    /// Get op(a, b).
    fn op(&self, a: u8, b: u8) -> PyResult<u8> {
        if a >= self.size || b >= self.size {
            return Err(pyo3::exceptions::PyValueError::new_err(
                format!("Indices ({}, {}) out of range for magma of size {}", a, b, self.size)
            ));
        }
        Ok(self.table[a as usize * self.size as usize + b as usize])
    }

    /// Check associativity: (a*b)*c == a*(b*c) for all a,b,c.
    fn is_associative(&self) -> bool {
        let n = self.size as usize;
        let t = &self.table;
        for a in 0..n {
            for b in 0..n {
                let ab = t[a * n + b] as usize;
                for c in 0..n {
                    let lhs = t[ab * n + c];
                    let bc = t[b * n + c] as usize;
                    let rhs = t[a * n + bc];
                    if lhs != rhs {
                        return false;
                    }
                }
            }
        }
        true
    }

    /// Check commutativity: a*b == b*a for all a,b.
    fn is_commutative(&self) -> bool {
        let n = self.size as usize;
        let t = &self.table;
        for a in 0..n {
            for b in (a + 1)..n {
                if t[a * n + b] != t[b * n + a] {
                    return false;
                }
            }
        }
        true
    }

    /// Find identity element, or return None.
    fn has_identity(&self) -> Option<u8> {
        let n = self.size as usize;
        let t = &self.table;
        for e in 0..n {
            let mut is_id = true;
            for a in 0..n {
                if t[e * n + a] != a as u8 || t[a * n + e] != a as u8 {
                    is_id = false;
                    break;
                }
            }
            if is_id {
                return Some(e as u8);
            }
        }
        None
    }

    /// Check idempotency: a*a == a for all a.
    fn is_idempotent(&self) -> bool {
        let n = self.size as usize;
        let t = &self.table;
        for a in 0..n {
            if t[a * n + a] != a as u8 {
                return false;
            }
        }
        true
    }

    /// Return the Cayley table as nested Python lists of ints.
    #[getter]
    fn operation(&self) -> Vec<Vec<u16>> {
        let n = self.size as usize;
        (0..n)
            .map(|i| {
                self.table[i * n..(i + 1) * n]
                    .iter()
                    .map(|&v| v as u16)
                    .collect()
            })
            .collect()
    }

    /// Return element list [0, 1, ..., size-1].
    #[getter]
    fn elements(&self) -> Vec<u16> {
        (0..self.size).map(|v| v as u16).collect()
    }

    /// Cayley table as string for display.
    fn cayley_table_str(&self) -> String {
        let n = self.size as usize;
        let mut result = String::new();
        result.push_str("   ");
        for j in 0..n {
            result.push_str(&format!("{j} "));
        }
        result.push('\n');
        result.push_str("  ");
        for _ in 0..2 * n + 1 {
            result.push('-');
        }
        result.push('\n');
        for i in 0..n {
            result.push_str(&format!("{i}| "));
            for j in 0..n {
                result.push_str(&format!("{} ", self.table[i * n + j]));
            }
            result.push('\n');
        }
        result
    }

    /// Convert to TLA+ representation.
    fn to_tla(&self) -> String {
        let n = self.size as usize;
        let mut parts = Vec::new();
        for a in 0..n {
            for b in 0..n {
                parts.push(format!(
                    "<<{a}, {b}>> |-> {}",
                    self.table[a * n + b]
                ));
            }
        }
        format!("[{}]", parts.join(", "))
    }

    fn __repr__(&self) -> String {
        format!("Magma(size={})", self.size)
    }
}

/// Generate all magmas of a given size.
///
/// Returns a list of Magma objects. Size is capped at 3 (3^9 = 19683 magmas).
/// For size 4+, use `count_properties` or `count_properties_parallel` instead.
#[pyfunction]
fn generate_all_magmas(size: u8) -> PyResult<Vec<Magma>> {
    if size == 0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Magma size must be at least 1",
        ));
    }
    if size > 3 {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Size {size} too large for exhaustive object generation (max 3); use count_properties for size 4"
        )));
    }
    let n = size as usize;
    let n64 = n as u64;
    let cells = n * n;
    let total: u64 = n64.pow(cells as u32);

    let mut magmas = Vec::with_capacity(total as usize);

    for i in 0..total {
        let mut table = vec![0u8; cells];
        let mut temp = i;
        for cell in 0..cells {
            table[cell] = (temp % n64) as u8;
            temp /= n64;
        }
        magmas.push(Magma { size, table });
    }

    Ok(magmas)
}

/// Count magmas matching each property combination (no Python object overhead per magma).
///
/// Returns a dict: {"total", "associative", "commutative", "has_identity", "idempotent",
///                   "assoc_and_comm", "monoid"}.
#[pyfunction]
fn count_properties(size: u8) -> PyResult<PropertyCounts> {
    if size == 0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Magma size must be at least 1",
        ));
    }
    if size > 4 {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Size {size} too large"
        )));
    }
    let n = size as usize;
    let n64 = n as u64;
    let cells = n * n;
    let total: u64 = n64.pow(cells as u32);

    let mut counts = PropertyCounts {
        total,
        associative: 0,
        commutative: 0,
        has_identity: 0,
        idempotent: 0,
        assoc_and_comm: 0,
        monoid: 0,
    };

    // Reuse a single table allocation across all iterations
    let mut table = vec![0u8; cells];
    for i in 0..total {
        let mut temp = i;
        for cell in 0..cells {
            table[cell] = (temp % n64) as u8;
            temp /= n64;
        }

        let assoc = is_assoc_raw(&table, n);
        let comm = is_comm_raw(&table, n);
        let has_id = has_identity_raw(&table, n);
        let idemp = is_idemp_raw(&table, n);

        if assoc {
            counts.associative += 1;
        }
        if comm {
            counts.commutative += 1;
        }
        if has_id {
            counts.has_identity += 1;
        }
        if idemp {
            counts.idempotent += 1;
        }
        if assoc && comm {
            counts.assoc_and_comm += 1;
        }
        if assoc && has_id {
            counts.monoid += 1;
        }
    }

    Ok(counts)
}

/// Search for counterexamples: magmas where premise holds but conclusion fails.
///
/// Returns a list of Magma objects (up to `limit` results).
/// `premise` and `conclusion` are property names:
///   "associative", "commutative", "has_identity", "idempotent".
#[pyfunction]
#[pyo3(signature = (premise, conclusion, max_size=3, limit=100))]
fn find_counterexamples(
    premise: &str,
    conclusion: &str,
    max_size: u8,
    limit: usize,
) -> PyResult<Vec<Magma>> {
    let check_premise = property_checker(premise)?;
    let check_conclusion = property_checker(conclusion)?;

    let mut results = Vec::new();

    for size in 2..=max_size {
        if size > 4 {
            break;
        }
        let n = size as usize;
        let n64 = n as u64;
        let cells = n * n;
        let total: u64 = n64.pow(cells as u32);

        let mut table = vec![0u8; cells];
        for i in 0..total {
            if results.len() >= limit {
                return Ok(results);
            }

            let mut temp = i;
            for cell in 0..cells {
                table[cell] = (temp % n64) as u8;
                temp /= n64;
            }

            if check_premise(&table, n) && !check_conclusion(&table, n) {
                results.push(Magma { size, table: table.clone() });
            }
        }
    }

    Ok(results)
}

// ── Raw property checkers (operate on flat table slices) ──

fn is_assoc_raw(t: &[u8], n: usize) -> bool {
    for a in 0..n {
        for b in 0..n {
            let ab = t[a * n + b] as usize;
            for c in 0..n {
                if t[ab * n + c] != t[a * n + t[b * n + c] as usize] {
                    return false;
                }
            }
        }
    }
    true
}

fn is_comm_raw(t: &[u8], n: usize) -> bool {
    for a in 0..n {
        for b in (a + 1)..n {
            if t[a * n + b] != t[b * n + a] {
                return false;
            }
        }
    }
    true
}

fn has_identity_raw(t: &[u8], n: usize) -> bool {
    for e in 0..n {
        let mut is_id = true;
        for a in 0..n {
            if t[e * n + a] != a as u8 || t[a * n + e] != a as u8 {
                is_id = false;
                break;
            }
        }
        if is_id {
            return true;
        }
    }
    false
}

fn is_idemp_raw(t: &[u8], n: usize) -> bool {
    for a in 0..n {
        if t[a * n + a] != a as u8 {
            return false;
        }
    }
    true
}

fn property_checker(name: &str) -> PyResult<fn(&[u8], usize) -> bool> {
    match name {
        "associative" => Ok(is_assoc_raw),
        "commutative" => Ok(is_comm_raw),
        "has_identity" => Ok(has_identity_raw),
        "idempotent" => Ok(is_idemp_raw),
        _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Unknown property: {name}"
        ))),
    }
}

/// Property count results returned from count_properties().
#[pyclass]
#[derive(Clone)]
struct PropertyCounts {
    #[pyo3(get)]
    total: u64,
    #[pyo3(get)]
    associative: u64,
    #[pyo3(get)]
    commutative: u64,
    #[pyo3(get)]
    has_identity: u64,
    #[pyo3(get)]
    idempotent: u64,
    #[pyo3(get)]
    assoc_and_comm: u64,
    #[pyo3(get)]
    monoid: u64,
}

#[pymethods]
impl PropertyCounts {
    fn __repr__(&self) -> String {
        format!(
            "PropertyCounts(total={}, assoc={}, comm={}, id={}, idemp={})",
            self.total, self.associative, self.commutative, self.has_identity, self.idempotent
        )
    }
}

// ── Parallel property counting (Rayon) ──

/// Like count_properties but uses all CPU cores via Rayon.
///
/// Speedup scales with available CPU cores. For size 4 this is the
/// only feasible approach (4.3 billion magmas).
#[pyfunction]
fn count_properties_parallel(py: Python<'_>, size: u8) -> PyResult<PropertyCounts> {
    if size == 0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Magma size must be at least 1",
        ));
    }
    if size > 4 {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Size {size} too large"
        )));
    }
    let n = size as usize;
    let n64 = n as u64;
    let cells = n * n;
    let total: u64 = n64.pow(cells as u32);

    let a_assoc = AtomicU64::new(0);
    let a_comm = AtomicU64::new(0);
    let a_id = AtomicU64::new(0);
    let a_idemp = AtomicU64::new(0);
    let a_ac = AtomicU64::new(0);
    let a_monoid = AtomicU64::new(0);

    py.allow_threads(|| {
        (0..total).into_par_iter().for_each_init(
            || vec![0u8; cells],
            |table, i| {
                let mut temp = i;
                for cell in 0..cells {
                    table[cell] = (temp % n64) as u8;
                    temp /= n64;
                }

                let assoc = is_assoc_raw(table, n);
                let comm = is_comm_raw(table, n);
                let has_id = has_identity_raw(table, n);
                let idemp = is_idemp_raw(table, n);

                if assoc {
                    a_assoc.fetch_add(1, Ordering::Relaxed);
                }
                if comm {
                    a_comm.fetch_add(1, Ordering::Relaxed);
                }
                if has_id {
                    a_id.fetch_add(1, Ordering::Relaxed);
                }
                if idemp {
                    a_idemp.fetch_add(1, Ordering::Relaxed);
                }
                if assoc && comm {
                    a_ac.fetch_add(1, Ordering::Relaxed);
                }
                if assoc && has_id {
                    a_monoid.fetch_add(1, Ordering::Relaxed);
                }
            },
        );
    });

    Ok(PropertyCounts {
        total,
        associative: a_assoc.load(Ordering::Relaxed),
        commutative: a_comm.load(Ordering::Relaxed),
        has_identity: a_id.load(Ordering::Relaxed),
        idempotent: a_idemp.load(Ordering::Relaxed),
        assoc_and_comm: a_ac.load(Ordering::Relaxed),
        monoid: a_monoid.load(Ordering::Relaxed),
    })
}

// ── Equation term evaluator ──
//
// Terms are represented as nested lists (S-expressions):
//   ["*", left, right]   — binary operation
//   ["x"]                — variable x
//   ["0"], ["1"], ...    — literal element
//
// An equation is (lhs_term, rhs_term).

/// Recursive term representation for equation processing.
#[derive(Clone, Debug)]
enum Term {
    Var(String),
    Lit(u8),
    Op(Box<Term>, Box<Term>),
}

impl Term {
    fn compute(&self, table: &[u8], n: usize, vars: &std::collections::HashMap<String, u8>) -> u8 {
        match self {
            Term::Var(name) => *vars.get(name).unwrap_or_else(|| {
                panic!(
                    "Variable '{}' not in assignment — list all term variables in the 'variables' parameter",
                    name
                )
            }),
            Term::Lit(v) => {
                assert!(
                    (*v as usize) < n,
                    "Literal {} out of range for magma of size {}",
                    v,
                    n
                );
                *v
            }
            Term::Op(l, r) => {
                let lv = l.compute(table, n, vars) as usize;
                let rv = r.compute(table, n, vars) as usize;
                table[lv * n + rv]
            }
        }
    }
}

/// Parse a term from a Python nested list.
///
/// Format: ["*", left, right] | ["x"] | ["0"]
fn parse_term(obj: &Bound<'_, pyo3::types::PyAny>) -> PyResult<Term> {
    let list: Vec<Bound<'_, pyo3::types::PyAny>> = obj.extract()?;
    if list.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err("Empty term"));
    }
    let tag: String = list[0].extract()?;
    if tag == "*" {
        if list.len() != 3 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Op term must be [\"*\", left, right]",
            ));
        }
        let left = parse_term(&list[1])?;
        let right = parse_term(&list[2])?;
        Ok(Term::Op(Box::new(left), Box::new(right)))
    } else if tag.len() == 1 && tag.chars().next().unwrap().is_ascii_lowercase() {
        Ok(Term::Var(tag))
    } else if let Ok(v) = tag.parse::<u8>() {
        Ok(Term::Lit(v))
    } else {
        // Treat as variable name
        Ok(Term::Var(tag))
    }
}

/// Check if an equation (lhs == rhs) holds for ALL assignments in a magma.
///
/// `lhs` and `rhs` are term S-expressions: ["*", ["x"], ["y"]] for x*y.
/// `variables` is the list of variable names to quantify over.
///
/// Returns True if the equation holds universally in this magma.
#[pyfunction]
fn check_equation(
    magma: &Magma,
    lhs: &Bound<'_, pyo3::types::PyAny>,
    rhs: &Bound<'_, pyo3::types::PyAny>,
    variables: Vec<String>,
) -> PyResult<bool> {
    let lhs_term = parse_term(lhs)?;
    let rhs_term = parse_term(rhs)?;
    let n = magma.size as usize;

    Ok(check_eq_all_assignments(
        &magma.table,
        n,
        &lhs_term,
        &rhs_term,
        &variables,
    ))
}

fn check_eq_all_assignments(
    table: &[u8],
    n: usize,
    lhs: &Term,
    rhs: &Term,
    variables: &[String],
) -> bool {
    let mut assignment = std::collections::HashMap::new();
    check_eq_recurse(table, n, lhs, rhs, variables, 0, &mut assignment)
}

fn check_eq_recurse(
    table: &[u8],
    n: usize,
    lhs: &Term,
    rhs: &Term,
    variables: &[String],
    depth: usize,
    assignment: &mut std::collections::HashMap<String, u8>,
) -> bool {
    if depth == variables.len() {
        return lhs.compute(table, n, assignment) == rhs.compute(table, n, assignment);
    }
    for val in 0..n as u8 {
        assignment.insert(variables[depth].clone(), val);
        if !check_eq_recurse(table, n, lhs, rhs, variables, depth + 1, assignment) {
            return false;
        }
    }
    true
}

/// Search for a counterexample magma: one where equation `premise` holds
/// but equation `conclusion` does not.
///
/// Each equation is (lhs, rhs, variables) where lhs/rhs are term S-expressions.
/// Returns the first counterexample Magma found, or None.
#[pyfunction]
#[pyo3(signature = (premise_lhs, premise_rhs, premise_vars, conclusion_lhs, conclusion_rhs, conclusion_vars, max_size=3))]
fn search_equation_counterexample(
    py: Python<'_>,
    premise_lhs: &Bound<'_, pyo3::types::PyAny>,
    premise_rhs: &Bound<'_, pyo3::types::PyAny>,
    premise_vars: Vec<String>,
    conclusion_lhs: &Bound<'_, pyo3::types::PyAny>,
    conclusion_rhs: &Bound<'_, pyo3::types::PyAny>,
    conclusion_vars: Vec<String>,
    max_size: u8,
) -> PyResult<Option<Magma>> {
    let p_lhs = parse_term(premise_lhs)?;
    let p_rhs = parse_term(premise_rhs)?;
    let c_lhs = parse_term(conclusion_lhs)?;
    let c_rhs = parse_term(conclusion_rhs)?;

    for size in 2..=max_size.min(4) {
        let n = size as usize;
        let n64 = n as u64;
        let cells = n * n;
        let total: u64 = n64.pow(cells as u32);

        let mut table = vec![0u8; cells];
        for i in 0..total {
            // Allow Ctrl-C to interrupt
            if i % 10000 == 0 {
                py.check_signals()?;
            }

            let mut temp = i;
            for cell in 0..cells {
                table[cell] = (temp % n64) as u8;
                temp /= n64;
            }

            let premise_holds =
                check_eq_all_assignments(&table, n, &p_lhs, &p_rhs, &premise_vars);
            if premise_holds {
                let conclusion_holds =
                    check_eq_all_assignments(&table, n, &c_lhs, &c_rhs, &conclusion_vars);
                if !conclusion_holds {
                    return Ok(Some(Magma { size, table }));
                }
            }
        }
    }
    Ok(None)
}

// ── Multi-property filter ──

/// Filter magmas by multiple property predicates in a single Rust pass.
///
/// `required` - properties that MUST hold (e.g. ["associative", "commutative"])
/// `forbidden` - properties that must NOT hold (e.g. ["idempotent"])
///
/// Returns matching Magma objects up to `limit`.
#[pyfunction]
#[pyo3(signature = (required, forbidden, max_size=3, limit=100))]
fn filter_magmas(
    required: Vec<String>,
    forbidden: Vec<String>,
    max_size: u8,
    limit: usize,
) -> PyResult<Vec<Magma>> {
    let req_checks: Vec<fn(&[u8], usize) -> bool> = required
        .iter()
        .map(|s| property_checker(s))
        .collect::<PyResult<_>>()?;
    let forb_checks: Vec<fn(&[u8], usize) -> bool> = forbidden
        .iter()
        .map(|s| property_checker(s))
        .collect::<PyResult<_>>()?;

    let mut results = Vec::new();

    for size in 2..=max_size.min(4) {
        let n = size as usize;
        let n64 = n as u64;
        let cells = n * n;
        let total: u64 = n64.pow(cells as u32);

        let mut table = vec![0u8; cells];
        for i in 0..total {
            if results.len() >= limit {
                return Ok(results);
            }

            let mut temp = i;
            for cell in 0..cells {
                table[cell] = (temp % n64) as u8;
                temp /= n64;
            }

            let all_req = req_checks.iter().all(|check| check(&table, n));
            if !all_req {
                continue;
            }
            let no_forb = forb_checks.iter().all(|check| !check(&table, n));
            if no_forb {
                results.push(Magma { size, table: table.clone() });
            }
        }
    }

    Ok(results)
}

#[pymodule]
fn magma_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Magma>()?;
    m.add_class::<PropertyCounts>()?;
    m.add_function(wrap_pyfunction!(generate_all_magmas, m)?)?;
    m.add_function(wrap_pyfunction!(count_properties, m)?)?;
    m.add_function(wrap_pyfunction!(count_properties_parallel, m)?)?;
    m.add_function(wrap_pyfunction!(find_counterexamples, m)?)?;
    m.add_function(wrap_pyfunction!(filter_magmas, m)?)?;
    m.add_function(wrap_pyfunction!(check_equation, m)?)?;
    m.add_function(wrap_pyfunction!(search_equation_counterexample, m)?)?;
    Ok(())
}

// ── Property-based invariant tests (proptest) ──────────────────
//
// Full-scope invariant tests using proptest to verify algebraic properties
// that must hold for ALL finite magmas, not just hand-picked examples.
//
// Organized by BDD scenarios:
//   Feature: Magma algebraic invariants
//   Scenario: Given ANY Cayley table, THEN [invariant] holds

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    // ── Strategies ─────────────────────────────────────────────

    /// Generate a valid Cayley table (flat Vec<u8>) of given size.
    /// Every entry is in [0, size), guaranteeing closure.
    fn arb_table(size: usize) -> impl Strategy<Value = Vec<u8>> {
        let cells = size * size;
        proptest::collection::vec(0..size as u8, cells)
    }

    /// Generate a size-2 Cayley table (4 entries, each in {0, 1}).
    fn arb_table_2() -> impl Strategy<Value = Vec<u8>> {
        arb_table(2)
    }

    /// Generate a size-3 Cayley table (9 entries, each in {0, 1, 2}).
    fn arb_table_3() -> impl Strategy<Value = Vec<u8>> {
        arb_table(3)
    }

    // ── Feature: Closure invariant ─────────────────────────────
    // Given: ANY valid Cayley table
    // Then: op(a, b) ∈ {0, ..., n-1}

    proptest! {
        #![proptest_config(ProptestConfig::with_cases(256))]

        #[test]
        fn closure_size_2(table in arb_table_2()) {
            let n = 2usize;
            for a in 0..n {
                for b in 0..n {
                    let result = table[a * n + b];
                    prop_assert!(result < n as u8,
                        "op({}, {}) = {} >= size {}", a, b, result, n);
                }
            }
        }

        #[test]
        fn closure_size_3(table in arb_table_3()) {
            let n = 3usize;
            for a in 0..n {
                for b in 0..n {
                    let result = table[a * n + b];
                    prop_assert!(result < n as u8,
                        "op({}, {}) = {} >= size {}", a, b, result, n);
                }
            }
        }
    }

    // ── Feature: Raw checker ↔ Magma method agreement ──────────
    // Given: ANY Cayley table
    // Then: Raw function and Magma method return the same result

    proptest! {
        #![proptest_config(ProptestConfig::with_cases(256))]

        #[test]
        fn raw_vs_struct_associativity_2(table in arb_table_2()) {
            let n = 2usize;
            let m = Magma { size: n as u8, table: table.clone() };
            prop_assert_eq!(is_assoc_raw(&table, n), m.is_associative());
        }

        #[test]
        fn raw_vs_struct_commutativity_2(table in arb_table_2()) {
            let n = 2usize;
            let m = Magma { size: n as u8, table: table.clone() };
            prop_assert_eq!(is_comm_raw(&table, n), m.is_commutative());
        }

        #[test]
        fn raw_vs_struct_identity_2(table in arb_table_2()) {
            let n = 2usize;
            let m = Magma { size: n as u8, table: table.clone() };
            prop_assert_eq!(has_identity_raw(&table, n), m.has_identity().is_some());
        }

        #[test]
        fn raw_vs_struct_idempotent_2(table in arb_table_2()) {
            let n = 2usize;
            let m = Magma { size: n as u8, table: table.clone() };
            prop_assert_eq!(is_idemp_raw(&table, n), m.is_idempotent());
        }

        #[test]
        fn raw_vs_struct_associativity_3(table in arb_table_3()) {
            let n = 3usize;
            let m = Magma { size: n as u8, table: table.clone() };
            prop_assert_eq!(is_assoc_raw(&table, n), m.is_associative());
        }

        #[test]
        fn raw_vs_struct_commutativity_3(table in arb_table_3()) {
            let n = 3usize;
            let m = Magma { size: n as u8, table: table.clone() };
            prop_assert_eq!(is_comm_raw(&table, n), m.is_commutative());
        }
    }

    // ── Feature: Commutativity ↔ table symmetry ────────────────
    // Given: ANY Cayley table
    // Then: is_comm_raw(t, n) ↔ t[a*n+b] == t[b*n+a] for all a,b

    proptest! {
        #![proptest_config(ProptestConfig::with_cases(512))]

        #[test]
        fn commutativity_iff_symmetric_2(table in arb_table_2()) {
            let n = 2usize;
            let symmetric = (0..n).all(|a|
                (0..n).all(|b| table[a * n + b] == table[b * n + a])
            );
            prop_assert_eq!(is_comm_raw(&table, n), symmetric);
        }

        #[test]
        fn commutativity_iff_symmetric_3(table in arb_table_3()) {
            let n = 3usize;
            let symmetric = (0..n).all(|a|
                (0..n).all(|b| table[a * n + b] == table[b * n + a])
            );
            prop_assert_eq!(is_comm_raw(&table, n), symmetric);
        }
    }

    // ── Feature: Idempotence ↔ diagonal property ───────────────
    // Given: ANY Cayley table
    // Then: is_idemp_raw(t, n) ↔ t[a*n+a] == a for all a

    proptest! {
        #![proptest_config(ProptestConfig::with_cases(512))]

        #[test]
        fn idempotence_iff_diagonal_2(table in arb_table_2()) {
            let n = 2usize;
            let diag_identity = (0..n).all(|a| table[a * n + a] == a as u8);
            prop_assert_eq!(is_idemp_raw(&table, n), diag_identity);
        }

        #[test]
        fn idempotence_iff_diagonal_3(table in arb_table_3()) {
            let n = 3usize;
            let diag_identity = (0..n).all(|a| table[a * n + a] == a as u8);
            prop_assert_eq!(is_idemp_raw(&table, n), diag_identity);
        }
    }

    // ── Feature: Identity uniqueness ───────────────────────────
    // Given: ANY Cayley table
    // Then: At most one element is a two-sided identity

    proptest! {
        #![proptest_config(ProptestConfig::with_cases(256))]

        #[test]
        fn identity_unique_2(table in arb_table_2()) {
            let n = 2usize;
            let m = Magma { size: n as u8, table: table.clone() };
            let mut identities = Vec::new();
            for e in 0..n {
                let is_id = (0..n).all(|a|
                    table[e * n + a] == a as u8 && table[a * n + e] == a as u8
                );
                if is_id {
                    identities.push(e);
                }
            }
            prop_assert!(identities.len() <= 1,
                "Multiple identities: {:?}", identities);

            // Also check Magma method agrees
            match m.has_identity() {
                Some(e) => prop_assert_eq!(identities, vec![e as usize]),
                None => prop_assert!(identities.is_empty()),
            }
        }

        #[test]
        fn identity_unique_3(table in arb_table_3()) {
            let n = 3usize;
            let mut count = 0u8;
            for e in 0..n {
                let is_id = (0..n).all(|a|
                    table[e * n + a] == a as u8 && table[a * n + e] == a as u8
                );
                if is_id {
                    count += 1;
                }
            }
            prop_assert!(count <= 1, "Found {} identities", count);
        }
    }

    // ── Feature: Exhaustive enumeration count ──────────────────
    // Given: n ∈ {1, 2, 3}
    // Then: Total magmas = n^(n²)

    #[test]
    fn exhaustive_size_1_count() {
        // 1^1 = 1
        let n = 1usize;
        let cells = n * n;
        let total: u64 = (n as u64).pow(cells as u32);
        assert_eq!(total, 1);
    }

    #[test]
    fn exhaustive_size_2_count() {
        // 2^4 = 16
        let n = 2usize;
        let cells = n * n;
        let total: u64 = (n as u64).pow(cells as u32);
        assert_eq!(total, 16);
    }

    #[test]
    fn exhaustive_size_3_count() {
        // 3^9 = 19683
        let n = 3usize;
        let cells = n * n;
        let total: u64 = (n as u64).pow(cells as u32);
        assert_eq!(total, 19683);
    }

    // ── Feature: Exhaustive size-2 property census ─────────────
    // Given: ALL 16 size-2 magmas
    // Then: Property counts match mathematical expectation

    #[test]
    fn exhaustive_size_2_property_census() {
        let n = 2usize;
        let cells = n * n;
        let total: u64 = (n as u64).pow(cells as u32);

        let mut assoc = 0u64;
        let mut comm = 0u64;
        let mut has_id = 0u64;
        let mut idemp = 0u64;

        for i in 0..total {
            let mut table = vec![0u8; cells];
            let mut temp = i;
            for cell in 0..cells {
                table[cell] = (temp % n as u64) as u8;
                temp /= n as u64;
            }
            if is_assoc_raw(&table, n) { assoc += 1; }
            if is_comm_raw(&table, n) { comm += 1; }
            if has_identity_raw(&table, n) { has_id += 1; }
            if is_idemp_raw(&table, n) { idemp += 1; }
        }

        assert_eq!(assoc, 8, "Expected 8 associative magmas");
        assert_eq!(comm, 8, "Expected 8 commutative magmas");
        assert_eq!(has_id, 4, "Expected 4 magmas with identity");
        assert_eq!(idemp, 4, "Expected 4 idempotent magmas");
    }

    // ── Feature: Property independence ─────────────────────────
    // Given: ALL size-2 magmas
    // Then: All four (assoc, comm) combinations exist

    #[test]
    fn property_independence_witnessed() {
        let n = 2usize;
        let cells = n * n;
        let total: u64 = (n as u64).pow(cells as u32);

        let mut tt = false; // assoc ∧ comm
        let mut tf = false; // assoc ∧ ¬comm
        let mut ft = false; // ¬assoc ∧ comm
        let mut ff = false; // ¬assoc ∧ ¬comm

        for i in 0..total {
            let mut table = vec![0u8; cells];
            let mut temp = i;
            for cell in 0..cells {
                table[cell] = (temp % n as u64) as u8;
                temp /= n as u64;
            }
            match (is_assoc_raw(&table, n), is_comm_raw(&table, n)) {
                (true, true) => tt = true,
                (true, false) => tf = true,
                (false, true) => ft = true,
                (false, false) => ff = true,
            }
        }

        assert!(tt, "No associative+commutative magma found");
        assert!(tf, "No associative+¬commutative magma found");
        assert!(ft, "No ¬associative+commutative magma found");
        assert!(ff, "No ¬associative+¬commutative magma found");
    }

    // ── Feature: Term computation determinism ──────────────────
    // Given: ANY term and assignment
    // Then: compute() returns the same result each time

    #[test]
    fn term_var_compute_deterministic() {
        let mut vars = std::collections::HashMap::new();
        vars.insert("x".to_string(), 1u8);
        let term = Term::Var("x".to_string());
        let table = vec![0u8, 1, 1, 0]; // XOR on {0,1}
        let r1 = term.compute(&table, 2, &vars);
        let r2 = term.compute(&table, 2, &vars);
        assert_eq!(r1, r2);
    }

    #[test]
    fn term_op_compute_deterministic() {
        let mut vars = std::collections::HashMap::new();
        vars.insert("x".to_string(), 0u8);
        vars.insert("y".to_string(), 1u8);
        let term = Term::Op(
            Box::new(Term::Var("x".to_string())),
            Box::new(Term::Var("y".to_string())),
        );
        let table = vec![0u8, 1, 1, 0]; // XOR
        let r1 = term.compute(&table, 2, &vars);
        let r2 = term.compute(&table, 2, &vars);
        assert_eq!(r1, r2);
    }

    // ── Feature: Trivial magma (size 1) has all properties ─────

    #[test]
    fn trivial_magma_all_properties() {
        let table = vec![0u8];
        let n = 1usize;
        assert!(is_assoc_raw(&table, n));
        assert!(is_comm_raw(&table, n));
        assert!(has_identity_raw(&table, n));
        assert!(is_idemp_raw(&table, n));
    }

    // ── Feature: TLA+ output format ────────────────────────────

    proptest! {
        #![proptest_config(ProptestConfig::with_cases(64))]

        #[test]
        fn tla_output_brackets(table in arb_table_2()) {
            let m = Magma { size: 2, table };
            let tla = m.to_tla();
            prop_assert!(tla.starts_with('['));
            prop_assert!(tla.ends_with(']'));
        }

        #[test]
        fn tla_output_entry_count_2(table in arb_table_2()) {
            let m = Magma { size: 2, table };
            let tla = m.to_tla();
            let count = tla.matches("|->").count();
            prop_assert_eq!(count, 4); // 2*2 entries
        }

        #[test]
        fn tla_output_entry_count_3(table in arb_table_3()) {
            let m = Magma { size: 3, table };
            let tla = m.to_tla();
            let count = tla.matches("|->").count();
            prop_assert_eq!(count, 9); // 3*3 entries
        }
    }

    // ── Feature: Cayley table string format ────────────────────

    proptest! {
        #![proptest_config(ProptestConfig::with_cases(64))]

        #[test]
        fn cayley_str_has_correct_rows(table in arb_table_2()) {
            let m = Magma { size: 2, table };
            let s = m.cayley_table_str();
            let lines: Vec<&str> = s.trim().lines().collect();
            // header + separator + 2 data rows
            prop_assert_eq!(lines.len(), 4);
        }
    }

    // ── Feature: Equation ↔ property checker agreement ─────────
    // Given: The associativity equation as S-expression terms
    // Then: check_eq_all_assignments matches is_assoc_raw for all size-2

    #[test]
    fn equation_matches_property_exhaustive_size_2() {
        let n = 2usize;
        let cells = n * n;
        let total: u64 = (n as u64).pow(cells as u32);

        // Associativity: (x*y)*z = x*(y*z)
        let lhs = Term::Op(
            Box::new(Term::Op(
                Box::new(Term::Var("x".to_string())),
                Box::new(Term::Var("y".to_string())),
            )),
            Box::new(Term::Var("z".to_string())),
        );
        let rhs = Term::Op(
            Box::new(Term::Var("x".to_string())),
            Box::new(Term::Op(
                Box::new(Term::Var("y".to_string())),
                Box::new(Term::Var("z".to_string())),
            )),
        );
        let vars = vec!["x".to_string(), "y".to_string(), "z".to_string()];

        for i in 0..total {
            let mut table = vec![0u8; cells];
            let mut temp = i;
            for cell in 0..cells {
                table[cell] = (temp % n as u64) as u8;
                temp /= n as u64;
            }

            let eq_result = check_eq_all_assignments(&table, n, &lhs, &rhs, &vars);
            let prop_result = is_assoc_raw(&table, n);
            assert_eq!(eq_result, prop_result,
                "Equation vs property disagreement for table {:?}", table);
        }
    }

    // ── Feature: Commutativity equation ↔ is_comm_raw ──────────

    #[test]
    fn comm_equation_matches_property_exhaustive_size_2() {
        let n = 2usize;
        let cells = n * n;
        let total: u64 = (n as u64).pow(cells as u32);

        // Commutativity: x*y = y*x
        let lhs = Term::Op(
            Box::new(Term::Var("x".to_string())),
            Box::new(Term::Var("y".to_string())),
        );
        let rhs = Term::Op(
            Box::new(Term::Var("y".to_string())),
            Box::new(Term::Var("x".to_string())),
        );
        let vars = vec!["x".to_string(), "y".to_string()];

        for i in 0..total {
            let mut table = vec![0u8; cells];
            let mut temp = i;
            for cell in 0..cells {
                table[cell] = (temp % n as u64) as u8;
                temp /= n as u64;
            }

            let eq_result = check_eq_all_assignments(&table, n, &lhs, &rhs, &vars);
            let prop_result = is_comm_raw(&table, n);
            assert_eq!(eq_result, prop_result,
                "Commutativity equation vs property disagreement for table {:?}", table);
        }
    }
}
