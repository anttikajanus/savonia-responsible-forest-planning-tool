"""Create the bilingual Excel workbook and serialize its XLSX package."""

import zipfile
import xml.etree.ElementTree as ET

from .serialization import stringify
from .result_precision import published_value
from ..analysis.domain import METRIC_FIELDS
from ..i18n import tr


def _cell_ref(row, col):
    letters = ""
    while col:
        col, rem = divmod(col - 1, 26)
        letters = chr(65 + rem) + letters
    return "{0}{1}".format(letters, row)

def _worksheet_xml(rows):
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ET.register_namespace("", ns)
    root = ET.Element("{%s}worksheet" % ns)
    sheet_data = ET.SubElement(root, "{%s}sheetData" % ns)
    for row_number, row in enumerate(rows, 1):
        row_el = ET.SubElement(sheet_data, "{%s}row" % ns, {"r": str(row_number)})
        for col_number, value in enumerate(row, 1):
            if value is None:
                ET.SubElement(row_el, "{%s}c" % ns, {"r": _cell_ref(row_number, col_number)})
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                attributes = {"r": _cell_ref(row_number, col_number), "t": "n"}
                if isinstance(value, float):
                    attributes["s"] = "1"  # Display 0.00; retain the exact numeric value.
                cell = ET.SubElement(row_el, "{%s}c" % ns, attributes)
                ET.SubElement(cell, "{%s}v" % ns).text = str(value)
            else:
                cell = ET.SubElement(row_el, "{%s}c" % ns, {"r": _cell_ref(row_number, col_number), "t": "inlineStr"})
                inline = ET.SubElement(cell, "{%s}is" % ns)
                text = ET.SubElement(inline, "{%s}t" % ns)
                text.text = str(value)
                if text.text and (text.text[0].isspace() or text.text[-1].isspace()):
                    text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)

def write_xlsx(path, sheets):
    """Write valid basic XLSX worksheets using inline strings and no libraries."""
    content_types = ET.Element("Types", xmlns="http://schemas.openxmlformats.org/package/2006/content-types")
    ET.SubElement(content_types, "Default", Extension="rels", ContentType="application/vnd.openxmlformats-package.relationships+xml")
    ET.SubElement(content_types, "Default", Extension="xml", ContentType="application/xml")
    ET.SubElement(content_types, "Override", PartName="/xl/workbook.xml", ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml")
    ET.SubElement(content_types, "Override", PartName="/xl/styles.xml", ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml")
    for index in range(1, len(sheets) + 1):
        ET.SubElement(content_types, "Override", PartName="/xl/worksheets/sheet{0}.xml".format(index), ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml")

    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    office_rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    root_rels = ET.Element("Relationships", xmlns=rel_ns)
    ET.SubElement(root_rels, "Relationship", Id="rId1", Type=office_rel_ns + "/officeDocument", Target="xl/workbook.xml")

    main_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ET.register_namespace("", main_ns)
    ET.register_namespace("r", office_rel_ns)
    workbook = ET.Element("{%s}workbook" % main_ns)
    sheet_list = ET.SubElement(workbook, "{%s}sheets" % main_ns)
    workbook_rels = ET.Element("Relationships", xmlns=rel_ns)
    for index, sheet_name in enumerate(sheets, 1):
        ET.SubElement(sheet_list, "{%s}sheet" % main_ns, {
            "name": sheet_name[:31], "sheetId": str(index), "{%s}id" % office_rel_ns: "rId{0}".format(index),
        })
        ET.SubElement(workbook_rels, "Relationship", {
            "Id": "rId{0}".format(index), "Type": office_rel_ns + "/worksheet",
            "Target": "worksheets/sheet{0}.xml".format(index),
        })

    ET.SubElement(workbook_rels, "Relationship", {
        "Id": "rIdStyles", "Type": office_rel_ns + "/styles", "Target": "styles.xml",
    })
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", ET.tostring(content_types, encoding="utf-8", xml_declaration=True))
        archive.writestr("_rels/.rels", ET.tostring(root_rels, encoding="utf-8", xml_declaration=True))
        archive.writestr("xl/workbook.xml", ET.tostring(workbook, encoding="utf-8", xml_declaration=True))
        archive.writestr("xl/_rels/workbook.xml.rels", ET.tostring(workbook_rels, encoding="utf-8", xml_declaration=True))
        archive.writestr("xl/styles.xml", _styles_xml(main_ns))
        for index, rows in enumerate(sheets.values(), 1):
            archive.writestr("xl/worksheets/sheet{0}.xml".format(index), _worksheet_xml(rows))
    return path

def _styles_xml(ns):
    """Default spreadsheet style plus a two-decimal numeric display style."""
    root = ET.Element("{%s}styleSheet" % ns)
    fonts = ET.SubElement(root, "{%s}fonts" % ns, count="1")
    font = ET.SubElement(fonts, "{%s}font" % ns)
    ET.SubElement(font, "{%s}sz" % ns, val="11")
    ET.SubElement(font, "{%s}name" % ns, val="Calibri")
    fills = ET.SubElement(root, "{%s}fills" % ns, count="2")
    for pattern in ("none", "gray125"):
        fill = ET.SubElement(fills, "{%s}fill" % ns)
        ET.SubElement(fill, "{%s}patternFill" % ns, patternType=pattern)
    borders = ET.SubElement(root, "{%s}borders" % ns, count="1")
    ET.SubElement(borders, "{%s}border" % ns)
    base = {"numFmtId": "0", "fontId": "0", "fillId": "0", "borderId": "0"}
    style_xfs = ET.SubElement(root, "{%s}cellStyleXfs" % ns, count="1")
    ET.SubElement(style_xfs, "{%s}xf" % ns, base)
    cell_xfs = ET.SubElement(root, "{%s}cellXfs" % ns, count="2")
    ET.SubElement(cell_xfs, "{%s}xf" % ns, {**base, "xfId": "0"})
    ET.SubElement(cell_xfs, "{%s}xf" % ns, {**base, "xfId": "0", "numFmtId": "2", "applyNumberFormat": "1"})
    cell_styles = ET.SubElement(root, "{%s}cellStyles" % ns, count="1")
    ET.SubElement(cell_styles, "{%s}cellStyle" % ns, name="Normal", xfId="0", builtinId="0")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _text_parts(value):
    # Excel allows 32767 characters per cell. 16000 also stays below that
    # limit when every character needs a UTF-16 surrogate pair.
    text = stringify(value)
    return [text[index:index + 16000] for index in range(0, len(text), 16000)] or [""]


def write_workbook(path, language, tier_rows, coverage, limitations, run_metadata=None):
    """Export already aggregated metrics and their exact coverage statistics."""
    summary = [[tr(language, key) for key in ("column_tier", "column_class")]
               + [tr(language, "metric_area_ha"), tr(language, "column_features")]
               + [tr(language, "metric_" + metric) for metric in METRIC_FIELDS]]
    summary.extend([
        [row["tier"], row["class"], published_value("area_ha", row["area_ha"]), row["feature_count"]]
        + [published_value(metric, row.get(metric)) for metric in METRIC_FIELDS]
        for row in tier_rows
    ])

    source_rows = [[tr(language, key) for key in ("column_source", "column_status", "column_details", "column_part")]]
    for row in coverage:
        details = {key: value for key, value in row.items()
                   if key not in ("service_id", "status") and value not in (None, "", [], {})}
        source_rows.extend([
            [row.get("service_id"), row.get("status"), part, index]
            for index, part in enumerate(_text_parts(details), 1)
        ])

    coverage_columns = (
        "column_tier", "column_class", "column_metric_id", "column_metric",
        "column_source", "column_status", "column_valid_area", "column_unknown_area",
        "column_represented_volume", "column_matching_area", "column_weighted_sum",
        "column_age_coverage",
    )
    metric_rows = [[tr(language, key) for key in coverage_columns]]
    for row in tier_rows:
        for metric in METRIC_FIELDS:
            statistics = row.get("indicator_coverage", {}).get(metric, {})
            metric_rows.append([
                row["tier"], row["class"], metric, tr(language, "metric_" + metric),
                statistics.get("source_id"), statistics.get("status"),
                statistics.get("valid_area_ha"), statistics.get("unknown_area_ha"),
                statistics.get("represented_volume_m3"), statistics.get("matching_area_ha"),
                statistics.get("weighted_sum"), statistics.get("coverage_percent"),
            ])

    summary.extend([[], [tr(language, "project_name")], [tr(language, "prototype_notice")]])
    note_rows = [[tr(language, "column_calculation_notes")],
                 [tr(language, "project_name")], [tr(language, "prototype_notice")]]
    note_rows.extend([[item] for item in limitations if item != tr(language, "prototype_notice")])
    if run_metadata:
        note_rows.append([tr(language, "column_run_metadata"), tr(language, "column_part"), tr(language, "column_details")])
        for record in run_metadata:
            for key, value in record.items():
                note_rows.extend([[key, index, part] for index, part in enumerate(_text_parts(value), 1)])
    return write_xlsx(path, {
        tr(language, "sheet_summary"): summary,
        tr(language, "sheet_source_coverage"): source_rows,
        tr(language, "sheet_metric_coverage"): metric_rows,
        tr(language, "sheet_notes"): note_rows,
    })

