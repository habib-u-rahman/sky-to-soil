"""Builds the 2-3 page PDF farm plan for POST /report/pdf using reportlab.

Note: rendered in English only, regardless of the requested advisor
language -- reportlab's base fonts don't shape/reorder Urdu (Nastaliq)
script correctly without extra font + bidi-reshaping dependencies, so a
garbled Urdu PDF would be worse than an explicit English-only limitation.
The advisor explanation embedded here is always fetched in English.
"""

from __future__ import annotations

import datetime as dt
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.data.crop_repo import crops_by_id

SLOT_LABELS = {"Y1_kharif": "Year 1 - Kharif", "Y1_rabi": "Year 1 - Rabi", "Y2_kharif": "Year 2 - Kharif", "Y2_rabi": "Year 2 - Rabi"}


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="S2STitle", parent=styles["Title"], fontSize=20, spaceAfter=4))
    styles.add(ParagraphStyle(name="S2SSection", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1b4332")))
    styles.add(ParagraphStyle(name="S2SSub", parent=styles["Heading3"], spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(name="S2SBody", parent=styles["BodyText"], spaceAfter=4, leading=14))
    styles.add(ParagraphStyle(name="S2SSmall", parent=styles["BodyText"], fontSize=8.5, leading=11, textColor=colors.HexColor("#444444")))
    return styles


def _rotation_crop_names(rotation: dict) -> dict:
    lookup = crops_by_id()
    return {slot: (lookup[cid]["name"] if cid and cid in lookup else "Fallow / cover crop") for slot, cid in rotation.items()}


def _rotation_table(rotations: list[dict], styles) -> Table:
    header = ["#", "Year 1 Kharif", "Year 1 Rabi", "Year 2 Kharif", "Year 2 Rabi", "Score", "Weighted"]
    rows = [header]
    for i, entry in enumerate(rotations, start=1):
        names = _rotation_crop_names(entry["rotation"])
        rows.append(
            [
                str(i),
                names["Y1_kharif"],
                names["Y1_rabi"],
                names["Y2_kharif"],
                names["Y2_rabi"],
                f"{entry['base_score_0_100']:.0f}",
                f"{entry['priority_weighted_score_0_100']:.0f}",
            ]
        )
    table = Table(rows, hAlign="LEFT", colWidths=[1.2 * cm, 3.1 * cm, 3.1 * cm, 3.1 * cm, 3.1 * cm, 1.6 * cm, 1.9 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d6a4f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#aaaaaa")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f6f3")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _climate_table(climate: dict | None, styles) -> list:
    if not climate:
        return [Paragraph("Climate trend data was not available for this location at report generation time.", styles["S2SBody"])]

    baseline, recent, deltas = climate["baseline"], climate["recent"], climate["deltas"]
    rows = [
        ["Metric", f"Baseline ({baseline['start_year']}-{baseline['end_year']})", f"Recent ({recent['start_year']}-{recent['end_year']})", "Change"],
        ["Mean max temp (°C)", f"{baseline.get('mean_tmax_c', 'n/a')}", f"{recent.get('mean_tmax_c', 'n/a')}", f"{deltas.get('mean_tmax_c', 'n/a')}"],
        ["Mean min temp (°C)", f"{baseline.get('mean_tmin_c', 'n/a')}", f"{recent.get('mean_tmin_c', 'n/a')}", f"{deltas.get('mean_tmin_c', 'n/a')}"],
        [
            "Kharif rainfall (mm)",
            f"{baseline.get('seasonal_rainfall_mm', {}).get('kharif_mm', 'n/a')}",
            f"{recent.get('seasonal_rainfall_mm', {}).get('kharif_mm', 'n/a')}",
            f"{deltas.get('seasonal_rainfall_mm', {}).get('kharif_mm', 'n/a') if isinstance(deltas.get('seasonal_rainfall_mm'), dict) else 'n/a'}",
        ],
        [
            "Rabi rainfall (mm)",
            f"{baseline.get('seasonal_rainfall_mm', {}).get('rabi_mm', 'n/a')}",
            f"{recent.get('seasonal_rainfall_mm', {}).get('rabi_mm', 'n/a')}",
            f"{deltas.get('seasonal_rainfall_mm', {}).get('rabi_mm', 'n/a') if isinstance(deltas.get('seasonal_rainfall_mm'), dict) else 'n/a'}",
        ],
    ]
    table = Table(rows, hAlign="LEFT", colWidths=[4.2 * cm, 4.5 * cm, 4.5 * cm, 2.8 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#40798c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#aaaaaa")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef4f6")]),
            ]
        )
    )

    trend_lines = []
    for t in climate.get("trends", []):
        marker = "significant" if t.get("significant_at_0_10") else "not significant"
        trend_lines.append(f"{t['variable']}: {t['mk_trend']} ({marker})")

    flow: list = [table]
    if trend_lines:
        flow.append(Spacer(1, 6))
        flow.append(Paragraph("Trend tests (Mann-Kendall, 1% significance threshold at p&lt;0.10): " + "; ".join(trend_lines), styles["S2SSmall"]))
    return flow


def _soil_paragraph(soil: dict | None, styles) -> Paragraph:
    if not soil or soil.get("status") != "ok" or not soil.get("layers"):
        return Paragraph("Soil data was unavailable for this location; values should be entered manually (see /soil/presets for typical starting values by texture).", styles["S2SBody"])

    from app.science.soil_suitability import classify_texture, weighted_profile_mean

    layers = soil["layers"]
    ph = weighted_profile_mean(layers, "phh2o")
    clay = weighted_profile_mean(layers, "clay_pct")
    sand = weighted_profile_mean(layers, "sand_pct")
    silt = weighted_profile_mean(layers, "silt_pct")
    soc = weighted_profile_mean(layers, "soc_g_kg")
    texture = classify_texture(clay, sand, silt) or "unknown"

    text = (
        f"Depth-weighted (0-30cm) soil pH: <b>{ph if ph is not None else 'n/a'}</b>, texture class: "
        f"<b>{texture}</b> (clay {clay if clay is not None else 'n/a'}%, sand {sand if sand is not None else 'n/a'}%, "
        f"silt {silt if silt is not None else 'n/a'}%), soil organic carbon: "
        f"<b>{soc if soc is not None else 'n/a'} g/kg</b>."
    )
    return Paragraph(text, styles["S2SBody"])


def build_pdf_bytes(
    analysis: dict,
    current_crops: list[str],
    top_n: int,
    advisor_text: str | None,
    advisor_technical_note: str | None,
    advisor_kb_sources: list[str] | None,
) -> bytes:
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, topMargin=1.6 * cm, bottomMargin=1.6 * cm, leftMargin=1.6 * cm, rightMargin=1.6 * cm
    )

    location = analysis.get("location", {})
    generated_at = analysis.get("generated_at") or dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    story: list = []
    story.append(Paragraph("Sky-to-Soil Farm Plan", styles["S2STitle"]))
    story.append(
        Paragraph(
            f"Location: {location.get('lat', 'n/a')}, {location.get('lon', 'n/a')} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Generated: {generated_at} &nbsp;&nbsp;|&nbsp;&nbsp; Current crops: {', '.join(current_crops) or 'none given'}",
            styles["S2SSmall"],
        )
    )

    story.append(Paragraph("Climate shift summary", styles["S2SSection"]))
    story.extend(_climate_table(analysis.get("climate"), styles))

    story.append(Paragraph("Soil", styles["S2SSection"]))
    story.append(_soil_paragraph(analysis.get("soil"), styles))

    rotations = (analysis.get("rotations") or {}).get("top", [])[:top_n]
    story.append(Paragraph(f"Top {len(rotations)} recommended rotations", styles["S2SSection"]))
    if rotations:
        story.append(_rotation_table(rotations, styles))
        story.append(Spacer(1, 6))
        for i, entry in enumerate(rotations, start=1):
            if entry.get("reasons"):
                story.append(Paragraph(f"<b>#{i}</b>: " + " ".join(entry["reasons"][:2]), styles["S2SSmall"]))
    else:
        story.append(Paragraph("No scored rotations were available to include in this report.", styles["S2SBody"]))

    story.append(Paragraph("AI Agronomist explanation", styles["S2SSection"]))
    if advisor_text:
        for paragraph in advisor_text.split("\n"):
            if paragraph.strip():
                story.append(Paragraph(paragraph.strip(), styles["S2SBody"]))
    else:
        story.append(Paragraph("AI explanation was not available for this report.", styles["S2SBody"]))
    if advisor_technical_note:
        story.append(Paragraph("For extension officers", styles["S2SSub"]))
        story.append(Paragraph(advisor_technical_note, styles["S2SSmall"]))

    story.append(Paragraph("Data sources and disclaimer", styles["S2SSection"]))
    sources = (analysis.get("rotations") or {}).get("source", {})
    source_lines = [
        "Climate: NASA POWER (daily agroclimatology).",
        "Soil: ISRIC SoilGrids (or manual entry / /soil/presets typical values if unavailable).",
        "Vegetation: ORNL DAAC MODIS MOD13Q1 NDVI.",
        "Rotation scoring: Sky-to-Soil rotation optimizer (FAO-56 crop water balance, heat-stress-day counting, soil pH/texture suitability).",
    ]
    if advisor_kb_sources:
        source_lines.append("AI explanation background: " + ", ".join(advisor_kb_sources) + ".")
    if sources.get("message"):
        source_lines.append(f"Note: {sources['message']}")
    for line in source_lines:
        story.append(Paragraph(line, styles["S2SSmall"]))

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "<b>Disclaimer:</b> This report is generated by an automated decision-support tool and is not a "
            "guarantee of yield, income, or outcome. Local soil, water, pest, and market conditions vary; please "
            "confirm this plan with your local agricultural extension officer before making changes.",
            styles["S2SSmall"],
        )
    )

    doc.build(story)
    return buffer.getvalue()
