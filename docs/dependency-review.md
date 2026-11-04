# Dependency remediation and lint coverage

Reviewed November 4, 2026 (Asia/Manila). The frontend now uses **Oxlint 1.91.0**
instead of ESLint 9.39.5 and eslint-config-next 16.4.1. Next runtime stays 16.4.1.
A clean npm installation reports **zero vulnerabilities**. No risk exception,
advisory suppression, threshold change, package alias, minimatch override or
patched dependency is used. Every audit finding still fails the canonical check.
Hosted CI has not run.

## Root cause and revalidation

[GHSA-g3hv-75wg-m249 / CVE-2026-118764](https://github.com/advisories/GHSA-g3hv-75wg-m249)
lists minimatch below 11.0.1 as affected and 11.0.1 as fixed. It describes glob
preprocessing amplification at optimization level 2 or higher. The former lock
contained minimatch 3.1.5 and 10.2.6 through ESLint, Next lint configuration,
React/accessibility/import plugins and TypeScript parser tooling: 16 moderate
package records from one advisory. Legacy 3.x lacks that preprocessing branch
and uses a callable CommonJS API; this discrepancy was never used to suppress
findings. Development tooling still processes contributed source/config in CI.

The [ESLint support policy](https://eslint.org/version-support/) confirms v9 is
unmaintained. November 4 registry queries still returned ESLint 10.14.0 requiring
minimatch `^10.2.6`, and typescript-estree 8.72.1 requiring `^10.2.2`. React
7.37.5, jsx-a11y 6.10.2 and import 2.32.0 still exclude ESLint 10 in their peers.
Next lint config 16.4.4 still consumes these plugins. The unsuccessful prior
10.14.0/16.4.4 install was not repeated: the constraints had not changed.
Forcing minimatch 11 would break older consumers' declared ranges/callable API.

Authoritative metadata: [ESLint](https://registry.npmjs.org/eslint/10.14.0),
[Next config](https://registry.npmjs.org/eslint-config-next/16.4.4),
[TypeScript parser](https://registry.npmjs.org/@typescript-eslint%2Ftypescript-estree/8.72.1),
[React](https://registry.npmjs.org/eslint-plugin-react/7.37.5),
[accessibility](https://registry.npmjs.org/eslint-plugin-jsx-a11y/6.10.2),
[imports](https://registry.npmjs.org/eslint-plugin-import/2.32.0).

## Implemented migration

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

## Verification boundaries

Clean npm installation and the lint coverage tests pass locally. Full canonical
results are recorded in the private cleanup handoff; public checks require no
handoff. Python/scanner locks are unchanged. Earlier pytest remediation remains
pytest 9.2.0 with pytest-asyncio 1.4.1.post1, addressing
[GHSA-6w46-j5rx-g56g](https://github.com/advisories/GHSA-6w46-j5rx-g56g).

Advisories change over time. npm/pip-audit do not certify native bindings, Chromium,
PDFium, OS libraries, malicious packages or real-provider behavior. No exploit
traffic or credential verification was performed. Re-run audits for the exact
release. Hosted CI, remaining provenance review, exact refs and explicit publication
authorization remain outstanding. Existing history is preserved. No private
reporting channel is being configured, by owner decision.
