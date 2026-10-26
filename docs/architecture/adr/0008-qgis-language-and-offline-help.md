# Follow QGIS language and distribute offline bilingual help

Status: accepted  
Recorded: 2026-10-26

Resolve Finnish/English through `selected_language()` from `QgsApplication.locale()`, using Finnish for Finnish QGIS and English otherwise. QGIS is the sole language setting, ensuring wizard, global Help/About, Processing and outputs follow one application-language policy. Ship both HTML manuals and original licence/notice texts inside the package, accessible from the dock, QGIS Help → Plugins and Processing's manual URL; local essential help remains available without network access. The cost is maintaining equivalent manuals and matching anchors in both languages. [Help requirements](../../specs/help-and-language.md), [operations](../operations.md#language-and-help), [resource resolver](../../../qgis_plugin/savonia_responsible_forest_planning_tool/documentation.py).
