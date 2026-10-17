# Design

Native GitHub profile README for Adam Rudavský / XVADUR. GitHub owns the typography, navigation, links and reading surface. The profile adds Adam's existing wordmark, actual work and a personal voice.

## Reading order

The orange XVADUR signature leads into an introduction to Adam, his route from healthcare to building with AI, and his own Minecraft analogy. Two pairs of real project images show Hriech, Korpus, Jakub and Lucia. Each project's description uses the full reading width: phones must not squeeze prose into parallel table columns. Writing and the question behind the work follow the projects. A compact dated measurement section comes near the end, before the invitation to make contact.

The main README is English; README.sk.md carries the same structure in Slovak. The English Minecraft quotation is a translation of the Slovak original on Adam's website.

## Identity

The banner uses the existing geometric XVADUR wordmark on #ED4E26. The ink is #101C20. It is a self-contained SVG with outlined letters, an explicit background, a title, description and an equivalent HTML alt. It works independently of GitHub's or the operating system's theme.

Project images retain their own palettes and original pixels. They are previews, linked to the work, not background decoration. Asset sources and historical-interface caveats are recorded in assets/work/README.md. No new illustration or portrait was generated.

## Native layout and accessibility

Project previews are paired at 49% width. Their descriptions sit below, across the full content width, in semantic headings and paragraphs. This is deliberately native Markdown and supported HTML: no custom CSS, JavaScript, nested app interface or external statistics service.

Each image has a descriptive alt. Work status is written beside its link: public publication, private lab, wider system in development, or booking demonstration. The contact invitation and writing link are ordinary keyboard-accessible links. The page follows GitHub's own text, focus and contrast behavior.

## Measurements

The profile shows one short line of counts and the frozen snapshot date. A native details element holds the writing calendar, exact counts, provider counters, source shares and methodology link. No token grand total, live-counter claim or ranking is added.

The frozen source remains data/profile.json. scripts/render_profile.py owns the generated metrics block in both languages. Sixteen legacy board/calendar/source SVGs remain reproducible supporting assets. The opening board no longer appears in the README.

Every generated SVG now has an explicit white or #0D1117 ground. This prevents unreadable dark text on GitHub's dark background when GitHub's selected theme differs from the operating-system preference used by picture media queries.

## Verification boundary

scripts/build_preview.py provides a labelled approximation for local inspection in both languages and themes. Native GitHub is the final renderer. Check the published profile after updating the repository, including its narrow viewport and expanded measurement notebook. The frozen aggregate is dated 2026-10-13 and is not presented as a live 2026-10-17 total.
