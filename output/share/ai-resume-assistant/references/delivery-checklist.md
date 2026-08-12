# Resume delivery checklist

Use this checklist for HTML and PDF production.

## Source synchronization

- Identify the active text source.
- Use matching basenames for Markdown, plain text, HTML, and PDF when all four are delivered.
- Compare major headings, dates, numbers, links, and project names across formats.
- Ensure the latest user correction appears everywhere.
- When the resume is intended for multiple hiring platforms, keep a plain-text version whose section order, dates, metrics, and links match the designed version.

## HTML

- Use semantic headings and selectable text.
- Keep contact details readable without depending on icons.
- Use real `href` values for portfolio and project links.
- Provide print-specific CSS.
- Prefer a restrained layout that scans horizontally from top to bottom.
- Avoid decorative English labels that do not add information.

## Print CSS

- Set A4 page size and deliberate margins.
- Preserve intended colors with `print-color-adjust`.
- Replace browser-sensitive gradients with stable print colors when necessary.
- Control page breaks around headings, project blocks, and bullet groups.
- Avoid fixed heights that create bottom whitespace or clip content.

## PDF verification

- Confirm the PDF opens.
- Confirm expected page count.
- Render every page to images.
- Inspect the top, page breaks, links, accent rules, bottom balance, and avatar.
- Confirm text extraction is possible.
- Check that no glyphs, URLs, or bullets are clipped.

## Content integrity

- Do not shrink type below comfortable reading size simply to reach one page.
- Fix redundant wording and spacing before reducing font size.
- Do not delete evidence merely to create visual symmetry.
- Do not add unsupported text to fill whitespace.

## Handoff

Provide absolute clickable links to:

1. active text source;
2. HTML;
3. PDF.

Mention page count and visual verification. Name any remaining difference explicitly.
