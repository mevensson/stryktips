---
name: unit-test-design
description: >-
  A checklist for writing tight unit tests. Use when writing or reviewing unit
  tests. Also use when the user asks about unit test structure, naming,
  determinism, or design.
---

# Unit Test Design

A reference checklist. Each entry is a single rule; apply every rule when writing or reviewing.

## AAA structure
Every test has exactly three phases, visually separated by a blank line:

```
# Arrange
builder = MyBuilder().with_name("test").build()

# Act
result = sut.do_the_thing(builder)

# Assert
assert result == expected
```

A phase may be empty (no `# Arrange` needed when set-up is trivial), but the structure stays.

## Name connects to AAA
The test name maps to the three phases. A part may be omitted when it's obvious from context or empty:

```
test__valid_name__returns_the_name  # Given/When/Then — one convention
test_given_valid_name_when_queried_then_returns  # Another
test_fails_on_invalid_input         # When/Then only — Given is obvious
```

Pick one naming convention per project and apply it consistently.

## One behaviour per test
Test exactly one logical behaviour. One assertion on the outcome. Supporting assertions that verify the test itself (e.g., "the fixture is not None") are ok; assertions on distinct behaviours belong in separate tests.

## Builder factories
Use builders (method chaining with sensible defaults) to set up test state and test input. A test may use several builders for different objects.

```python
# Defaults give a valid object
user = UserBuilder().build()
order = OrderBuilder().build()

# Test changes only what matters
user = UserBuilder().with_name("edge case").build()
order = OrderBuilder().with_items(0).build()
```

In languages with keyword/default arguments (Python, Kotlin), constructor-based builders are acceptable:

```python
User(name="edge case")
Order(items=[])
```

## Test the contract, not the implementation
Test the public API's observable behaviour. Do not test private methods, internal state, or implementation details. A test that breaks after a safe refactor is testing the wrong thing.

## Favour real objects over mocks
Use the real collaborator when feasible. Reserve mocks, stubs, and fakes for IO boundaries — network, filesystem, clock, external services. Within the domain layer, test with real objects.

## Deterministic
Every run of the same test produces the same result. Seed all randomness, freeze time, avoid shared mutable state, and never depend on the order of an unsorted collection.

If a non-deterministic test genuinely serves the design better (rare), ask the user for permission with a written justification. Otherwise, make it deterministic.

## Fast
A unit test completes in milliseconds. If a test takes visible time, the abstraction level is wrong — the test is testing too much at once or leaning on a heavy collaborator that should be a test double.
