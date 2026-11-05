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


## Provenance qualifications

The shadcn tag is a comparison reference, not a proven extraction revision. No
original component-generator receipt was found. The Sonner issue explains the
technical idea; inspected issue text did not contain the local explanation verbatim.
That observation cannot establish independent authorship or license arbitrary prose.

All decompressed ZIP members of the ten older DOCX fixtures reproduce from their
documented fictional lines using python-docx 1.2.0. ZIP envelopes were not claimed
byte-identical, and the original generator version remains unknown. The four
portfolio fixtures reproduce byte-for-byte from their owned generators. Retain the
[versioned template reference](https://github.com/python-openxml/python-docx/tree/v1.2.0/src/docx/templates)
and the applicable template notice; content equivalence does not establish original
creation history.

A separate Chromium probe reported Arial/ArialMT for `Inter,sans-serif`; it does
not identify every historical screenshot glyph. No font program is distributed.
[Windows font output guidance](https://learn.microsoft.com/en-us/typography/fonts/font-faq)
distinguishes bitmap output from font redistribution, but cannot establish terms
for an unidentified font. Retain screenshot provenance and icon notices without
inferring additional ownership or permission.

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

Reassess attribution or reconstruct affected assets if concrete contrary evidence
emerges. Missing receipts alone do not require replacing functional source or assets.
Future binary or font distribution requires review of those actual bytes.
