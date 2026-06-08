from __future__ import annotations
from datetime import datetime
from io import BytesIO
from .helpers import fmt_brl, period_label, transactions_for_period

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
except Exception:
    colors = A4 = getSampleStyleSheet = cm = SimpleDocTemplate = Paragraph = Spacer = Table = TableStyle = None


def build_pdf_report(period: str) -> BytesIO:
    if SimpleDocTemplate is None:
        raise RuntimeError("ReportLab não instalado. Rode: pip install reportlab")

    movs = transactions_for_period(period, order="asc")
    entradas = sum(t.amount for t in movs if t.kind == "entrada")
    saidas = sum(t.amount for t in movs if t.kind == "saida")
    saldo = entradas - saidas

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.3 * cm,
        bottomMargin=1.3 * cm,
        title="Relatorio CashFlow",
    )
    styles = getSampleStyleSheet()

    story = [
        Paragraph("CashFlow", styles["Title"]),
        Paragraph(f"Relatório financeiro - {period_label(period)}", styles["Heading2"]),
        Paragraph(f"Gerado em: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]),
        Spacer(1, 0.35 * cm),
    ]

    resumo = [
        ["Indicador", "Valor"],
        ["Total de entradas", fmt_brl(entradas)],
        ["Total de saídas", fmt_brl(saidas)],
        ["Saldo final", fmt_brl(saldo)],
        ["Quantidade de movimentações", str(len(movs))],
    ]
    table = Table(resumo, colWidths=[8 * cm, 7 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4b5cff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D5DD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [table, Spacer(1, 0.55 * cm), Paragraph("Histórico de movimentações", styles["Heading2"])]

    rows = [["Data", "Tipo", "Descrição", "Categoria", "Valor"]]
    for t in movs:
        rows.append([
            t.created_at.strftime("%d/%m/%Y"),
            "Entrada" if t.kind == "entrada" else "Saída",
            Paragraph((t.title or "")[:70], styles["Normal"]),
            t.category.name if t.category else "Geral",
            fmt_brl(t.amount),
        ])
    if len(rows) == 1:
        rows.append(["-", "-", "Nenhuma movimentação encontrada neste período.", "-", "-"])

    hist = Table(rows, colWidths=[2.5 * cm, 2.3 * cm, 6.2 * cm, 3 * cm, 3 * cm], repeatRows=1)
    hist.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#101828")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#EAECF0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story += [
        hist,
        Spacer(1, 0.45 * cm),
        Paragraph(
            "Observação: este documento foi gerado automaticamente a partir dos dados salvos no sistema.",
            styles["Italic"],
        ),
    ]
    doc.build(story)
    buffer.seek(0)
    return buffer
