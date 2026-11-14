# Git Commit Guidelines

These guidelines establish a consistent and readable commit history across the project. All contributors should follow these conventions to make changes easier to understand, review, and maintain.

## 1. General Rules

- All commit messages must be written in **English**.
- Use the **Conventional Commits** naming convention.
- Keep messages clear, concise, and descriptive.
- Each commit should represent one logical change whenever possible.
- Describe **what changed**, rather than the steps taken to make the change.
- Avoid generic or meaningless commit messages.

## 2. Commit Message Format

Use the following structure:

```text
type: short description
```

Optionally, include a scope to identify the affected component:

```text
type(scope): short description
```

A scope is recommended when it adds meaningful context but is not required.

For larger changes, include an optional commit body to explain the motivation, relevant details, or impact.

## 3. Commit Types

| Type | Purpose |
|---|---|
| `feat` | Introduce new functionality or capabilities |
| `fix` | Correct bugs or unexpected behavior |
| `docs` | Add or update documentation |
| `test` | Add, update, or improve tests |
| `refactor` | Restructure code without changing its expected behavior |
| `chore` | Perform maintenance or general housekeeping |
| `style` | Apply formatting or non-functional styling changes |
| `build` | Update dependencies, packaging, or build configuration |
| `perf` | Improve performance or resource efficiency |
| `ci` | Update automation or continuous integration workflows |
| `revert` | Revert a previous commit |

Choose the type that best represents the **primary purpose** of the change.

## 4. Writing Guidelines

- Start the description with a lowercase action verb.
- Prefer verbs such as `add`, `update`, `remove`, `fix`, `improve`, `simplify`, `prevent`, or `validate`.
- Use the imperative form (e.g., `add validation` instead of `added validation`).
- Do not end the description with a period.
- Keep the subject line reasonably short, preferably within 72 characters.
- Avoid unnecessary details, personal references, or task history.
- Use the commit body for additional context when necessary.

**Avoid messages such as:**

```text
update
fix stuff
changes
final version
work in progress
misc fixes
```

## 5. Examples

### Features

```text
feat: add data export functionality
feat: implement input validation
feat(api): add pagination support
```

### Bug Fixes

```text
fix: prevent duplicate records
fix: handle missing configuration
fix(auth): resolve session expiration issue
```

### Documentation

```text
docs: update README
docs: add setup instructions
docs: clarify contribution guidelines
```

### Testing

```text
test: add validation tests
test: improve edge case coverage
```

### Refactoring and Maintenance

```text
refactor: simplify data processing
chore: organize project structure
style: format source files
build: update project dependencies
perf: optimize file processing
ci: update automated checks
```

## 6. Breaking Changes

When a commit introduces an intentional change that is incompatible with existing functionality, add `!` after the type or optional scope.

```text
feat!: change configuration format
refactor(api)!: remove deprecated endpoints
```

Use the commit body to explain the impact and any necessary migration steps.

Alternatively, include a `BREAKING CHANGE:` footer in the commit message.

## 7. Commit Best Practices

Before creating a commit:

1. Review the modified files.
2. Ensure the changes are relevant to the commit.
3. Run applicable tests or checks.
4. Avoid committing credentials, temporary files, or unnecessary generated content.
5. Write a message that accurately summarizes the change.

When possible, separate unrelated modifications into different commits.

o maintain a clean, consistent, and meaningful Git history—not to enforce unnecessary complexity.**