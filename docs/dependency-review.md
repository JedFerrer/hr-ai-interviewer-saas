# Dependency tooling and lint coverage

The locked frontend uses **Oxlint 1.91.0** with project-owned compatibility checks.
This avoids the former ESLint/plugin dependency compatibility and advisory problems
without forced overrides, patched packages or audit suppression. Runtime Next stays
16.4.1. Every dependency audit finding fails the canonical check; remediation is
mandatory without exceptions. Lock versions describe this checkout, not a claim
that no newer advisory exists.

## Tooling and lint coverage

[Oxlint 1.91.0](https://registry.npmjs.org/oxlint/1.91.0) is pinned exactly with
registry integrity hashes, including its Windows binding. Its Node range is
`^20.19.0 || >=22.12.0`, satisfied by verified Node 22.16.0. The new graph contains
neither ESLint nor minimatch. No fork or private package maintenance is introduced.
The existing `npm ci --fetch-retries=0` workflow installs it reproducibly;
Renovate's npm manager sees the direct pin.

`npm run lint` runs `.oxlintrc.json` and then `scripts/lint-compat.mjs`. Strict
`tsc --noEmit`, Node tests, production build, HTTP demo and Chromium smoke remain.
Native rules are [documented by Oxc](https://oxc.rs/docs/guide/usage/linter/rules.html).
Compiler rules such as [immutability](https://oxc.rs/docs/guide/usage/linter/rules/react/immutability.html)
use shared compiler analysis. No alpha JavaScript plugin bridge is needed.

The former effective Next core-web-vitals configuration enabled 62 rules. Of these,
56 map to explicit native rules with the same severity/options. The six remaining
rules are accounted for below. Different analyzers need not produce identical
results for every possible program.

| Coverage | Replacement |
| --- | --- |
| React recommended | Native rules; deprecated API aliases and lifecycle names checked with the locked TypeScript AST checker |
| Hooks | Explicit native rules-of-hooks and exhaustive-deps |
| React Compiler | Explicit static-components, use-memo, preserve-manual-memoization, incompatible-library, immutability, globals, refs, set-state-in-effect/render, error-boundaries, purity and unsupported-syntax |
| Compiler config/gating | Former lint config supplied no compiler options; Next compiler is not enabled. Compatibility checker fails on introducing Next/Babel compiler configuration until its option/gating validation is integrated and tested. |
| JSX uses-react/uses-vars | Native JSX scope analysis replaces ESLint bookkeeping; automatic JSX runtime needs no React import. Unused bindings remain visible. |
| Next core-web-vitals/recommended | Explicit native Next rules; internal location navigation warnings retained by compatibility checker |
| Accessibility | All six former explicit rules and Image alt-text options retained |
| TypeScript/general correctness | Strict tsc retained; native syntactic TypeScript, core JavaScript and Oxc correctness checks added. Type-aware Oxlint rules are not enabled or claimed. |
| Anonymous default exports | Native import warning retained |

`frontend/tests/lint.test.mjs` runs actual negative snippets through the installed
binary for React, hooks, compiler, Next, accessibility, TypeScript and correctness.
It also exercises deprecated aliases/lifecycles, navigation, valid unrelated APIs
and the compiler-configuration guard. These tests run in canonical frontend checks.

The compatibility checker is project-owned code, not copied plugin implementation.
It detects imported React aliases, deprecated APIs/lifecycles and literal/template
prefix internal navigation. It is conservative about lifecycle names; it does not
reproduce every ESLint scope-resolution or constant-folding edge case. Future
compiler configuration or React/Next rule changes require updating this checker
and tests. Native equivalents may replace it after coverage is verified.

The demo banner's effect-local counters use a mutable object instead of reassigned
captured bindings, preserving observer behavior under compiler immutability checks.
Two intentional full-page auth-navigation warnings remain visible, alongside eight
newly detected unused-binding warnings. None of the former rules was disabled to
hide warnings. Full document auth navigation clears sensitive in-memory state.

## Audit commands and limitations

After the [canonical locked installation](quality-checks.md#installation), including
the separate scanner environment, run from repository root in PowerShell:

```powershell
.venv/Scripts/python.exe scripts/check.py dependencies
.venv/Scripts/python.exe scripts/check.py lint
.venv/Scripts/python.exe scripts/check.py frontend
```

The dependency command audits both Python locks and the npm lock. The lint command
checks Python correctness; frontend checks include the actual lint regression
snippets, strict TypeScript, Node contracts and production build. Follow
[lock maintenance](quality-checks.md#updating-locks-and-checks) when updating inputs.

Advisories change over time. npm/pip-audit do not certify native bindings, Chromium,
PDFium, OS libraries, malicious packages or real-provider behavior. A dated audit
pass is not evidence for changed locks or future advisories. Preserve findings and
run relevant checks for the changed source; follow-up commits need CI for their
own SHA. See the [third-party inventory](third-party-inventory.md) for attribution
and distribution limits. No publication authorization is implied.
