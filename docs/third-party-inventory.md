# Third-party inventory — proposed source

Inspected November 3, 2026; classifications reviewed November 4, 2026. Scope is `release/RELEASE_SOURCE_FILES.txt`, not the
developer's entire disk, a production bundle, container image or hosted service.
The owner has adopted [RIGHTS.md](../RIGHTS.md). No legal-compliance certification is
made. Exact retained notices are in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## Distributed source and assets

| Material | Evidence/source/version | Bytes distributed and notices/action |
| --- | --- | --- |
| Twelve `frontend/src/components/ui/*.tsx` files | shadcn/ui New York registry, compared with tag `shadcn@2.3.0`; badge, button and card match after whitespace/punctuation normalization; remaining wrappers retain recognizable structure with adaptations | Source is distributed. MIT copyright/permission/disclaimer now retained verbatim. Tag is a comparison reference, not a proven original extraction revision; exact original provenance remains unresolved. |
| `frontend/src/lib/utils.ts`, theme provider and CSS theme conventions | shadcn-style composition; clsx/tailwind-merge and next-themes imports | Source distributed; retain shadcn notice conservatively. Exact copy/edit history is not established. |
| Sonner dialog pointer-events workaround in layout/global CSS | Existing comments link upstream issue 357; inspected local explanation and CSS | Source distributed; reference already retained. Whether wording was copied from an external comment is unresolved; no third-party comment license is assumed. |
| Eight `docs/assets/portfolio/*` images | D/F owned fictional captures; interview image refreshed pre-G, see gallery | Pixel bytes distributed, including rendered Lucide icons and UI. Exact Lucide ISC and bundled Feather MIT notices retained. No SVG source/font files embedded in these raster images. |
| Seven `docs/assets/real-provider/*` images | November 4 ordinary-mode browser captures; fictional content with real DeepSeek output, [provenance](assets/real-provider/README.md) | Original UI/output pixels, with documented crops and JPEG-to-PNG conversion; no generated overlays or font programs. Existing icon notices retained. Actual platform glyph identity was not recorded; no new font license is asserted. |
| Twelve synthetic fixture DOCX files | Ten resume-eval fixtures plus two portfolio fixtures, generated via python-docx; portfolio generator explicitly constructs `Document()` | ZIP/XML/template bytes distributed, including `docProps/thumbnail.jpeg` from the default template; no embedded fonts or `word/media` parts found. python-docx 1.2.0 MIT notice retained for default template-derived parts. Earlier ten fixtures' generator version is unrecorded; fictional content provenance is documented separately. |
| Two portfolio PDF fixtures | Inspected `backend/tests/fixtures/portfolio/generate.py`, hand-built PDF objects and fictional text | PDF bytes distributed; `/BaseFont /Helvetica` reference, no embedded font program. No uploaded PDF reused. |
| Fonts | Layout names `Inter`, then sans-serif; no font import, download or font file in manifest | No Inter font bytes distributed. Actual screenshot glyphs use environment fallback; original capture font identity/terms are not proven. No font license is assigned by this inventory. |
| Other binaries, vendored packages | Manifest extension/path review | No executable, DLL, native library, archive, node_modules, browser, venv, `.next` or vendored dependency tree selected. Only the 29 document/image files above are selected binary artifacts: 12 DOCX, 2 PDF and 15 screenshots. Recheck if the distribution changes. |

Upstream comparison: [tagged component registry](https://github.com/shadcn-ui/ui/tree/shadcn%402.3.0/apps/www/registry/new-york/ui).
Notice texts were taken from that tag's LICENSE.md, installed lucide-react LICENSE,
and installed python_docx-1.2.0.dist-info/licenses/LICENSE, without paraphrasing.
Retaining a notice is not proof of a complete historical provenance chain.

## Direct npm dependencies

Versions and declared licenses below come from the installed packages matching
the retained npm lock. Sources are package metadata repository links, or npm
package pages when metadata has no repository. License locations are relative to
`frontend/node_modules/` and exist after installation, not in the proposed Git tree.
All packages in this table are installed separately: their implementation bytes
are not distributed in this source manifest. Screenshot/source exceptions are
listed above. Preserve package notices when later distributing compiled output.

| Component | Locked/installed version | Declared license | Source | Inspected notice location |
| --- | --- | --- | --- | --- |
| @hookform/resolvers | 5.2.2 | MIT | [source](https://github.com/react-hook-form/resolvers) | `@hookform/resolvers/LICENSE` |
| @next/env | 16.4.1 | MIT | [source](https://github.com/vercel/next.js) | No top-level notice found; inspect upstream before binary redistribution |
| @radix-ui/react-alert-dialog | 1.1.15 | MIT | [source](https://github.com/radix-ui/primitives) | `@radix-ui/react-alert-dialog/LICENSE` |
| @radix-ui/react-avatar | 1.1.11 | MIT | [source](https://github.com/radix-ui/primitives) | `@radix-ui/react-avatar/LICENSE` |
| @radix-ui/react-dialog | 1.1.15 | MIT | [source](https://github.com/radix-ui/primitives) | `@radix-ui/react-dialog/LICENSE` |
| @radix-ui/react-dropdown-menu | 2.1.16 | MIT | [source](https://github.com/radix-ui/primitives) | `@radix-ui/react-dropdown-menu/LICENSE` |
| @radix-ui/react-label | 2.1.8 | MIT | [source](https://github.com/radix-ui/primitives) | `@radix-ui/react-label/LICENSE` |
| @radix-ui/react-progress | 1.1.8 | MIT | [source](https://github.com/radix-ui/primitives) | `@radix-ui/react-progress/LICENSE` |
| @radix-ui/react-scroll-area | 1.2.10 | MIT | [source](https://github.com/radix-ui/primitives) | `@radix-ui/react-scroll-area/LICENSE` |
| @radix-ui/react-select | 2.2.6 | MIT | [source](https://github.com/radix-ui/primitives) | `@radix-ui/react-select/LICENSE` |
| @radix-ui/react-slot | 1.2.4 | MIT | [source](https://github.com/radix-ui/primitives) | `@radix-ui/react-slot/LICENSE` |
| @radix-ui/react-tabs | 1.1.13 | MIT | [source](https://github.com/radix-ui/primitives) | `@radix-ui/react-tabs/LICENSE` |
| @radix-ui/react-tooltip | 1.2.8 | MIT | [source](https://github.com/radix-ui/primitives) | `@radix-ui/react-tooltip/LICENSE` |
| @tailwindcss/postcss | 4.2.2 | MIT | [source](https://github.com/tailwindlabs/tailwindcss) | `@tailwindcss/postcss/LICENSE` |
| @types/node | 22.19.17 | MIT | [source](https://github.com/DefinitelyTyped/DefinitelyTyped) | `@types/node/LICENSE` |
| @types/react | 19.2.14 | MIT | [source](https://github.com/DefinitelyTyped/DefinitelyTyped) | `@types/react/LICENSE` |
| @types/react-dom | 19.2.3 | MIT | [source](https://github.com/DefinitelyTyped/DefinitelyTyped) | `@types/react-dom/LICENSE` |
| class-variance-authority | 0.7.1 | Apache-2.0 | [source](https://github.com/joe-bell/cva) | `class-variance-authority/LICENSE` |
| clsx | 2.1.1 | MIT | [source](https://github.com/lukeed/clsx) | `clsx/license` |
| date-fns | 4.1.0 | MIT | [source](https://github.com/date-fns/date-fns) | `date-fns/LICENSE.md` |
| lucide-react | 1.8.0 | ISC | [source](https://github.com/lucide-icons/lucide) | `lucide-react/LICENSE` |
| next | 16.4.1 | MIT | [source](https://github.com/vercel/next.js) | `next/license.md` |
| next-themes | 0.4.6 | MIT | [source](https://github.com/pacocoursey/next-themes) | `next-themes/license.md` |
| oxlint | 1.91.0 | MIT | [source](https://github.com/oxc-project/oxc/tree/oxlint_v1.91.0) | Registry/package metadata declares MIT; no license file in installed binding; review upstream notices before binary redistribution |
| playwright | 1.64.1 | Apache-2.0 | [source](https://github.com/microsoft/playwright) | `playwright/LICENSE`, `playwright/NOTICE` |
| react | 19.2.5 | MIT | [source](https://github.com/facebook/react) | `react/LICENSE` |
| react-dom | 19.2.5 | MIT | [source](https://github.com/facebook/react) | `react-dom/LICENSE` |
| react-dropzone | 15.0.0 | MIT | [source](https://github.com/react-dropzone/react-dropzone) | `react-dropzone/LICENSE` |
| react-hook-form | 7.72.1 | MIT | [source](https://github.com/react-hook-form/react-hook-form) | `react-hook-form/LICENSE` |
| sonner | 2.0.7 | MIT | [source](https://github.com/emilkowalski/sonner) | `sonner/LICENSE.md` |
| tailwind-merge | 3.5.0 | MIT | [source](https://github.com/dcastil/tailwind-merge) | `tailwind-merge/LICENSE.md` |
| tailwindcss | 4.2.2 | MIT | [source](https://github.com/tailwindlabs/tailwindcss) | `tailwindcss/LICENSE` |
| typescript | 5.9.3 | Apache-2.0 | [source](https://github.com/microsoft/TypeScript) | `typescript/LICENSE.txt` |
| zod | 4.6.7 | MIT | [source](https://github.com/colinhacks/zod) | `zod/LICENSE` |

## Direct Python and scanner inputs

The application/development environment and scanner environment are separate.
The following input packages are installed separately from hashed locks; none of
their package implementation/native bytes is selected for Git distribution.
Notice paths are relative to each environment's `Lib/site-packages`. Metadata
license declarations identify evidence, not a legal interpretation.

| Component | Version | Metadata license | Source | Notice evidence |
| --- | --- | --- | --- | --- |
| PyJWT | 2.15.1 | MIT | [PyPI](https://pypi.org/project/PyJWT/2.15.1/) | `pyjwt-2.15.1.dist-info/licenses/LICENSE` |
| aiosqlite | 0.22.1 | MIT License | [PyPI](https://pypi.org/project/aiosqlite/0.22.1/) | `aiosqlite-0.22.1.dist-info/licenses/LICENSE` |
| alembic | 1.20.1 | MIT | [PyPI](https://pypi.org/project/alembic/1.20.1/) | `alembic-1.20.1.dist-info/licenses/LICENSE` |
| anthropic | 0.125.0 | MIT | [PyPI](https://pypi.org/project/anthropic/0.125.0/) | `anthropic-0.125.0.dist-info/licenses/LICENSE` |
| asyncpg | 0.32.0 | Apache-2.0 | [PyPI](https://pypi.org/project/asyncpg/0.32.0/) | `asyncpg-0.32.0.dist-info/licenses/LICENSE` |
| bcrypt | 5.0.0 | Apache-2.0 | [PyPI](https://pypi.org/project/bcrypt/5.0.0/) | `bcrypt-5.0.0.dist-info/LICENSE` |
| email-validator | 2.3.0 | Unlicense | [PyPI](https://pypi.org/project/email-validator/2.3.0/) | `email_validator-2.3.0.dist-info/licenses/LICENSE` |
| fastapi | 0.162.0 | MIT | [PyPI](https://pypi.org/project/fastapi/0.162.0/) | `fastapi-0.162.0.dist-info/licenses/LICENSE` |
| httpx | 0.28.1 | BSD-3-Clause | [PyPI](https://pypi.org/project/httpx/0.28.1/) | `httpx-0.28.1.dist-info/licenses/LICENSE.md` |
| openai | 2.54.0 | Apache-2.0 | [PyPI](https://pypi.org/project/openai/2.54.0/) | `openai-2.54.0.dist-info/licenses/LICENSE` |
| pdfplumber | 0.11.10 | MIT License | [PyPI](https://pypi.org/project/pdfplumber/0.11.10/) | `pdfplumber-0.11.10.dist-info/licenses/LICENSE.txt` |
| pydantic | 2.14.2 | MIT | [PyPI](https://pypi.org/project/pydantic/2.14.2/) | `pydantic-2.14.2.dist-info/licenses/LICENSE` |
| pydantic-settings | 2.16.2 | MIT | [PyPI](https://pypi.org/project/pydantic-settings/2.16.2/) | `pydantic_settings-2.16.2.dist-info/licenses/LICENSE` |
| pytest | 9.2.0 | MIT | [PyPI](https://pypi.org/project/pytest/9.2.0/) | `pytest-9.2.0.dist-info/licenses/LICENSE` |
| pytest-asyncio | 1.4.1.post1 | Apache-2.0 | [PyPI](https://pypi.org/project/pytest-asyncio/1.4.1.post1/) | `pytest_asyncio-1.4.1.post1.dist-info/licenses/LICENSE` |
| pytest-socket | 0.8.1 | MIT | [PyPI](https://pypi.org/project/pytest-socket/0.8.1/) | `pytest_socket-0.8.1.dist-info/licenses/LICENSE` |
| pytest-timeout | 2.4.0 | MIT | [PyPI](https://pypi.org/project/pytest-timeout/2.4.0/) | `pytest_timeout-2.4.0.dist-info/licenses/LICENSE` |
| python-docx | 1.2.0 | MIT | [PyPI](https://pypi.org/project/python-docx/1.2.0/) | `python_docx-1.2.0.dist-info/licenses/LICENSE` |
| python-dotenv | 1.2.4 | BSD-3-Clause | [PyPI](https://pypi.org/project/python-dotenv/1.2.4/) | `python_dotenv-1.2.4.dist-info/licenses/LICENSE` |
| python-multipart | 0.0.33 | Apache-2.0 | [PyPI](https://pypi.org/project/python-multipart/0.0.33/) | `python_multipart-0.0.33.dist-info/licenses/LICENSE.txt` |
| redis | 5.3.1 | MIT | [PyPI](https://pypi.org/project/redis/5.3.1/) | `redis-5.3.1.dist-info/LICENSE` |
| resend | 2.50.1 | MIT License | [PyPI](https://pypi.org/project/resend/2.50.1/) | `resend-2.50.1.dist-info/licenses/LICENSE.md` |
| ruff | 0.17.3 | MIT | [PyPI](https://pypi.org/project/ruff/0.17.3/) | `ruff-0.17.3.dist-info/licenses/LICENSE` |
| slowapi | 0.1.10 | MIT | [PyPI](https://pypi.org/project/slowapi/0.1.10/) | `slowapi-0.1.10.dist-info/LICENSE` |
| sqlalchemy | 2.1.6 | MIT | [PyPI](https://pypi.org/project/sqlalchemy/2.1.6/) | `sqlalchemy-2.1.6.dist-info/licenses/LICENSE` |
| uvicorn | 0.54.0 | BSD-3-Clause | [PyPI](https://pypi.org/project/uvicorn/0.54.0/) | `uvicorn-0.54.0.dist-info/licenses/LICENSE.md` |
| detect-secrets | 1.5.0 | UNKNOWN | [PyPI](https://pypi.org/project/detect-secrets/1.5.0/) | `detect_secrets-1.5.0.dist-info/LICENSE` |
| pip-audit | 2.9.0 | Apache Software License | [PyPI](https://pypi.org/project/pip-audit/2.9.0/) | `pip_audit-2.9.0.dist-info/licenses/LICENSE` |

## Bundled/native components installed separately

| Component | Version evidence / notice location | Distribution/action |
| --- | --- | --- |
| Next SWC, sharp and optional image libraries | SWC Windows x64 16.4.1 (MIT), sharp 0.35.5 (Apache-2.0), @img/sharp-win32-x64 0.35.5 (Apache-2.0 AND LGPL-3.0-or-later); npm lock/package LICENSE files | Platform binaries installed separately, excluded from source. Any future packaged build must inventory its actual selected native variants and their notices. |
| Playwright / Chromium | Playwright 1.64.1; browser mapping selects Chromium 156.0.8078.4 build 1248; playwright-core ThirdPartyNotices.txt and browser about:credits | Browser downloaded separately; not in manifest or screenshots as executable bytes. Preserve full browser notices if later redistributed. |
| pypdfium2 / PDFium | pypdfium2 5.14.0, PDFium 156.0.8076.0 from pypdfium2_raw/version.json; pypdfium2-5.14.0.dist-info/licenses/data/windows_x64/BUILD_LICENSES includes freetype, ICU, JPEG, OpenJPEG and other notices | Native parser installed separately. Inspect full PDFium and embedded-library notice set for any future packaged app; Python package license alone is insufficient. |
| lxml / libxml2 / libxslt; cryptography / OpenSSL; Pillow codecs | lxml 6.1.3 (`licenses/LICENSES.txt`), cryptography 50.0.2 (`licenses/LICENSE.APACHE`, `LICENSE.BSD`), Pillow 13.0.0 (`licenses/LICENSE`); embedded native versions not independently certified | Wheels installed separately; excluded. Current audit does not certify embedded component versions/security or authorize binary distribution. |
| Python, Node, SQLite, Windows fonts and OS | Toolchain/environment supplied independently | Not vendored. Screenshots contain rendered glyphs; no font program is selected. Hosting/runtime redistribution requires a separate exact-content review. |

## Remaining work

Confirm original UI extraction history and provenance of any copied workaround
wording; confirm earlier DOCX generator/template provenance and screenshot fallback
font terms if needed for the selected publication. Review exact public history
and any external release attachments independently. RIGHTS.md governs the owner application; third-party notices retain their separate scope. Rebuild the inventory for any future
bundled binary, exported Next output, container, fonts or downloaded visual assets.
No installed dependency's license is asserted to cover the owner's application.


## Final decision preparation evidence — November 3, 2026

This section refines the earlier unresolved-items list; it does not certify rights.
No application, fixture, test or lock bytes were changed in this investigation.

### UI source and workaround

`git log --all -- frontend/src/components/ui/button.tsx` identifies introduction
in `bf46af3` (job management). The original button already has the recognizable
New York structure. No component-generator receipt or components.json history
was found by the scoped all-ref history search. The all-ref UI/theme/utils history also includes `933e6b5` (comparison board).
A fresh normalization comparison against the retained pre-G upstream files confirms
badge, button and card match after stripping whitespace, semicolons and commas;
the other nine wrappers differ. The retained comparison files cover all twelve wrappers; the tagged [button source](https://raw.githubusercontent.com/shadcn-ui/ui/shadcn%402.3.0/apps/www/registry/new-york/ui/button.tsx)
was independently retrieved again. The tag establishes a comparison source,
not the extraction date/revision. An exact original revision remains unknown.

`git show d72867c -- frontend/src/app/layout.tsx frontend/src/app/globals.css`
locates both workaround comments and implementation in that commit. The
[upstream issue](https://github.com/emilkowalski/sonner/issues/357) contains
an April 11, 2024 comment by steven-tey proposing the Toaster class, and discussion
of body pointer events and modal dismissal. The local multi-line explanations
are not verbatim passages in the inspected issue. This supports a shared technical
idea; it cannot establish independent authorship or exclude another source.
The issue's publication is not evidence of a license for arbitrary comment prose.

Concrete fallback proposal: replace the twelve wrappers from a single recorded
upstream revision, retaining its exact license, then reapply and document local
API/styling differences; review utils/theme/CSS conventions at the same time.
Rewrite the two explanatory comments from the local Undo/modal behavior, retaining
the issue as a technical reference. Keep selectors and interaction behavior unless
separately tested. Run canonical frontend and browser checks, including dialog,
Undo and focus behavior. Removing wrappers alone would break imports; excluding
layout/global CSS would break the application. These are optional fallback proposals, not required replacements or changes made
by this preparation; see the final classifications below.

### Older DOCX: reproducible contents established

The introduction commit `27a2b08` already contains the README generator using
`Document()`, one paragraph per `resume_lines`, and save. The historical package
version/installation receipt is absent. During this preparation all ten documents
were regenerated in memory using installed python-docx 1.2.0 and their existing
JSONL lines. Every ZIP member name and decompressed member byte matched the
existing file, including template parts, thumbnail and document properties.
Paragraphs also matched each case's lines exactly. Thus no unknown content needs
to be carried forward merely to preserve coverage: the current documents can be
reconstructed from this known package and the documented fictional source.
ZIP timestamps/compression envelopes were not claimed byte-identical for the ten.
The original generator version remains unknown; content equivalence does not prove it.

The [versioned upstream template directory](https://github.com/python-openxml/python-docx/tree/v1.2.0/src/docx/templates)
and installed `python_docx-1.2.0.dist-info/licenses/LICENSE` support the retained
MIT notice. All four portfolio outputs were separately regenerated into a fresh
temporary directory and matched byte-for-byte, then removed. No fixture overwrite
was necessary. Recommended disposition: retain these contents with the reconstruction
evidence. Alternative: save a deterministic new ZIP envelope from the same regenerated
members and record new hashes; run canonical backend checks and extraction/paragraph
comparisons. Do not run the old README's live-provider evaluation command. Its
legacy setup/live-eval instructions were replaced with owned-workspace guidance
on November 4, 2026; no new live results are claimed.

### Screenshot fonts: current observation versus historical inference

A new local Playwright 1.64.1 / Chromium build 1248 blank-page probe rendered
fictional text with the layout's `Inter,sans-serif` declaration. CDP
`CSS.getPlatformFontsForNode` reported Arial / ArialMT, `isCustomFont=false`,
40 glyphs. No HTTP navigation or application/database start was used. This is
confirmed for that probe only. Arial is a plausible historical fallback, not a
proven identity for every glyph in the eight D/F/pre-G captures. No original
per-node platform-font record was retained; icons and other scripts can differ.

Microsoft's [Windows font FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq)
treats bitmap graphic output like printing and distinguishes it from font-file
redistribution. This supports a conditional Windows-font interpretation, not a
blanket license for an unidentified font. No font program is in this manifest,
and no Inter notice is added merely because CSS names Inter. Existing icon notices
remain applicable. Proposed conservative disposition: recapture all eight images
from fresh owned fictional runs with an explicitly selected, verified licensed
font; record platform-font results for visible nodes and the font notice/source.
Preserve original captures locally. Keep paths/captions or update README, gallery
and demo links together; rerun browser geometry checks because font metrics can
change layout. Alternative: exclude all eight images and remove image embeds from
README/gallery/demo docs; application tests need no weakened assertions. The retained historical images remain selected; missing historical font identity
alone does not establish a material publication concern. See the final classifications below.


## Final classifications — November 4, 2026

These classifications assess the selected source and retained evidence, not legal
compliance. No material unresolved rights/content concern was identified in these
items. New evidence of incompatible terms or non-fictional content would require
reassessment; missing historical metadata alone does not establish such evidence.

| Item | Classification | Disposition and evidence |
| --- | --- | --- |
| Twelve UI wrappers, utils/theme/CSS conventions | Adequately attributed material with incomplete historical metadata | Retain the shadcn MIT notice and comparison reference. Recognizable source and three normalized matches support attribution; the unknown original extraction revision does not itself identify incompatible material. No replacement of functional wrappers is required. |
| Sonner workaround explanations | Documentation improvement only | The existing issue link identifies the technical reference. Inspected issue text did not contain the local multi-line prose verbatim; no concrete copied substantial passage or conflicting notice was identified. Keep the reference without claiming the issue licenses arbitrary prose. Comment rewrites remain optional. |
| Ten older fictional DOCX fixtures | Adequately attributed material with incomplete historical metadata | All decompressed members reproduce from documented fictional lines and python-docx 1.2.0, whose template notice is retained. Unknown original generator version is a historical gap, not unknown carried-forward content. |
| Four portfolio PDF/DOCX fixtures | Documentation improvement only | Owned generators and exact reproduction support content provenance. No embedded font program; retain the template notice and fictional labeling. No regeneration is needed. |
| Eight fictional screenshots and rendered glyphs | Adequately attributed material with incomplete historical metadata | Owned capture evidence, fictional content and retained icon notices support inclusion. No font files are distributed. Current Arial observation is not asserted as historical proof; no evidence identifies restricted font output. Missing glyph identity alone does not justify exclusion or mandatory recapture. |
| Seven real-provider screenshots and rendered glyphs | Adequately attributed material with incomplete historical metadata | Recorded ordinary-mode capture and visual review establish fictional candidate content and real provider output, with disclosed crops and assistant-authored answers. Retain icon notices. No font program is distributed; exact glyph identity remains unrecorded. This does not establish ownership or grant additional permission for provider output. |

Optional recapture/reconstruction proposals above remain available if concrete
contrary evidence emerges. They are not prerequisites inferred from absent receipts.
Future binary or font distribution requires review of those actual bytes.
