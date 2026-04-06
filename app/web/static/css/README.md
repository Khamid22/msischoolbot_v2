# CSS Architecture

## Folder Purpose
- `settings`: design tokens and theme variables.
- `generic`: global reset only.
- `elements`: bare element defaults (`body`, headings, links, inputs).
- `layouts`: reusable app/page shell layout rules.
- `components`: reusable UI blocks (alerts, forms, buttons, tables, overlays).
- `pages`: page-specific styling (`portal/admin`, `student dashboard`).
- `platform`: platform-specific overrides (`.tg-miniapp` only).
- `utilities`: helper/motion utility styles.
- `legacy`: temporary migration fallback files (not imported by default).

## Naming Rules
- Component selectors: prefer stable component names (`.primary-btn`, `.admin-table`, etc.) unless doing a dedicated rename migration.
- New reusable wrappers: `c-` prefix (example: `.c-card`, `.c-table`).
- Layout objects: `l-` prefix (example: `.l-shell`, `.l-grid`).
- Page scopes: `p-` prefix (example: `.p-admin-home`) for new work.
- State classes: `is-*` and `has-*` only.

## How To Add A New Component
1. Add a file in `components/` with a clear plain-text name.
2. Add its `@import` to `main.source.css` in the components section.
3. Keep responsive rules in the same file as the base selector.
4. Run `python3 scripts/build_css_bundle.py` or restart the app to rebuild `main.css`.
5. Reuse existing tokens (`--radius-*`, `--muted`, etc.) before adding new values.

## How To Add A New Page
1. Add a file in `pages/` with a clear plain-text name.
2. Scope page-specific rules to the page wrapper class.
3. Import it in `main.source.css` after shared components.
4. Run `python3 scripts/build_css_bundle.py` or restart the app to rebuild `main.css`.

## Debugging: "Where Is This Style Coming From?"
1. Inspect element in browser devtools.
2. Check the winning rule file path shown by devtools.
3. If rule is in `platform`, it is Telegram-specific.
4. If rule is in `pages`, it is page-specific and should stay there.
5. If reusable, move it to `components` and keep page files thin.

## Common Pitfalls
- Do not place `.tg-miniapp` outside `platform/telegram.css`.
- Do not duplicate the same selector in multiple layer folders.
- Do not add random breakpoints; reuse existing project breakpoints.
- Do not edit `legacy` unless running a controlled fallback.
- Do not add new runtime `@import` chains to files linked from templates.
