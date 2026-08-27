---
name: tdd-workflow
description: >-
  Use when the user asks you to implement a new feature, add functionality, or
  develop something new. Also use when the user asks you to fix a bug or defect.
---

# Test-Driven Development (TDD) Workflow

The Test-Driven Developmen (TDD) Workflow is used to step by step implement a feature, by first writing a failing test (red), then making it pass (green), and finally refactor.

To start the workflow you need an **end goal** that shall be implemented. The **end goal** shall be supplied by the caller of the skill. If you don't have an **end goal** ask the user for it.

Another precondition is that all unit tests passes.

## Step 1 - Decide next step

You start each iteration by deciding on the **next step** that takes you closer to the **end goal**.

The **next step** shall be testable by a single unit test.

Two common strategies are:
- **Top down** - Start at the top of the code and work down to the bottom.
- **Bottom up** - Start at the bottom and work up to the top.

Use the same strategy for each iteration.

## Step 2 - Write a failing unit test (red)

Delegate to a subagent to write a unit test for the *next step*.

**Note**: this step is mandatory, and a failing end to end test is **not** a failing unit test.

**Sub agent prompt**
- Include a description of **next step**.
- Specify that a single unit test shall be written for it using the /unit-test-design skill.
- Ideally no implementation files shall be change. One exception is dummy implementation that are required for the code to compile. For example if the goal is to test the add(int, int) function, and the function doesn''t exist it's ok to create a dummy implementation of it that always returns 0.
- The test shall fail in the expected way. For example if the test calls add(2, 1) it shall trigger an assert that 0 != 3.
- When the test has been implemented and fails as expected, the sub agent shall finish by creating a commit with the changes. The cmmit message shall start with "Red: ".

## Step 3 - Make the test pass (green)

Delegate to a subagent to make the test pass.

**Sub agent prompt**
- Point to the commit that added the unit test.
- Specify that the goal is to change the implementation so that the test passes.
- No changes to the test is allowed.
- All unit tests shall pass not just the new one.
- When all unit tests pass, the sub agent shall finish by create a commit the changes. The commit message shall start with "Green: ".

## Step 4 - Refactor

The purpose of this step is to keep the code clean and prevent rot and must be performed in each iteration. The reason to review all code is to see the whole picture and not just focus on the changed code.

**Note**: This step is mandatory, i.e., the review needs to always be performed, however if there are no findings the commit part can be skipped.

### Review all code

Delegate to a subagent to make a review of all code.

**Sub agent prompt**
- Tell the subagent to review all code in the project.
- Do **not** send any information about **end goal**, **next step**, what test have been written, or how it was fixed.
- The result shall be a description of the **review findings**.

### Handle the review comments

Delegate to a subagent to handle the **review findings**.

**Sub agent prompt**
- The **review findings**.
- Instructions to use its justment which findings shall be fixed.
- A separate commit shall be made for each fixed finding. The commit messages shall start with "Refactor: ".

## Step 5 - Check if **end goal** has been reached

Evaluate if the **end goal** has been reached. If the **end goal* has not been reached, do another itertion of Step 1 to 4.
