# Help, language and identity specification

[Operations](../architecture/operations.md) owns the language/help design and logging implementation; [distribution](../architecture/distribution.md) owns software inventory, licence decisions and data-attribution details.

## HL-01 Language selection and consistency

- Follow QGIS's application language: Finnish for Finnish QGIS, English for other or unavailable languages. QGIS is the sole language setting; the plugin has no independent language selector.
- Use this choice consistently for wizard/menu/control labels, tooltips, accessibility names, source readiness, progress/errors, Processing help, About, managed project names, temporary AOI labels and new output presentation.
- A run retains one resolved language across messages and outputs. Refresh plugin-owned visible text and any open About dialog when the application language is refreshed; subsequent manual launches use that language. An already open browser manual need not change automatically.
- Keep stored source IDs, field IDs, class/status codes and serialized keys language-neutral. Retain locale-appropriate numeric/date presentation and explicit units without changing interchange values.
- Finnish and English text and message placeholders must be complete for every supported user flow. Help explains changing QGIS's language and restarting as prompted.

## HL-02 Offline help and recovery

- Provide Help and About in QGIS **Help → Plugins**, usable before opening the wizard, and from the wizard in both docked and floating modes.
- Help opens the selected-language packaged HTML manual in the system browser. The same manual resolver serves global and dock entry points. A clearly labelled online documentation link supplements the local manual.
- Write the Finnish and English manuals for users who have already installed the plugin. Cover project setup, required sources/readiness, area selection, wizard and Processing use, result review, units, missing evidence, interpretation limits, troubleshooting, support and data credits. Keep installation, release maintenance, development setup, internal schemas and detailed implementation contracts in their repository documentation owners rather than the user manuals.
- Essential instructions, local links and complete applicable licence/notice texts work without internet access. Online source retrieval still requires connectivity.
- Missing/unreadable resources or browser-launch failure produce a concise localized message with a corrective next step and diagnostics. Do not claim success or silently open another language. External website failure does not prevent opening local help or notices.

## HL-03 Processing help

Provide bilingual short help explaining the algorithm, inputs, outputs and limits, plus a link to the packaged manual's Processing section in the QGIS language. Matching section links must work in both manuals after ZIP installation, including installation paths with spaces or non-ASCII characters. Keep instructions aligned with the current shared workflow and source requirements.

Explain the explicit required sawlog price, its eligibility and constant unit-price
meaning, recoverable stand-overlap warnings and possible duplicate contributions.
Distinguish the €/m³ assumption from calculated sawlog value in euros, including
unrounded-volume multiplication, zero/unknown stock and incomplete group totals.
Describe readable criterion checks and retained metric coverage without presenting
removed independent indicator status or diagnostic fields as current interfaces.

## HL-04 Identity, credits and attribution

- Use **Savonia - Responsible Forest Planning** in English and **Savonia - Vastuullinen metsäsuunnittelu** in Finnish. Identify Antti Kajanus as author and describe Savonia as the source use case.
- Prominently state unfinished personal-learning-prototype status and the absence of Savonia endorsement/approval in repository documentation, Plugin Manager information, About, Processing help and newly generated provenance/workbook notes.
- Working menu, toolbar, wizard, algorithm and result labels use the localized project name without prototype suffixes. The wizard description explains the next user action; it has no prototype banner above the form.
- About reads the installed name/version from authoritative metadata and provides offline help, online documentation, repository, issue tracker, project licence, third-party notices/inventory and separate data-source credits. Preserve the experimental flag and existing internal identifiers.
- Keep original required legal texts intact and accessible offline. The project's MIT licence does not replace third-party software or dataset terms. Software credits, service attribution and portable export attribution have distinct purposes.
- Preserve provider/dataset credits, terms references and change notices in new outputs. Map-visible OpenStreetMap attribution remains an explicit [open item](../open-questions.md#acceptance-and-distribution), rather than a completed effect of About credits.

## HL-05 Accessible controls

Every plugin-owned button and toolbar action has a recognizable icon and a translated tooltip describing the action. Keep visible text alongside icons where applicable. The compact output-folder ellipsis retains a translated tooltip and accessible name. Drawing and redock icons have usable standard fallbacks if a QGIS theme omits their preferred assets; controls remain identifiable and operable. The dedicated redock symbol distinguishes docking from a generic window action.

Acceptance covers Finnish, English and English fallback; language refresh; closed/docked/floating help access; packaged local links/notices; missing-resource/browser errors; installed metadata; output notices; and reload/unload without duplicates. Existing automated/native evidence and pending interactive/browser/disconnected checks remain in the [verification register](../open-questions.md).
