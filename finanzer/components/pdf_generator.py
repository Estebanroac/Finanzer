"""
Finanzer - Generador de reportes PDF.
Crea informes ejecutivos profesionales con análisis financiero.
"""

import io
from datetime import datetime
from typing import Optional
from functools import partial

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer

from finanzer.utils.formatters import fmt as fmt_base


def generate_simple_pdf(
    symbol: str, 
    company_name: str, 
    ratios: dict, 
    alerts: dict, 
    score: int,
    dcf_calculator=None  # Función DCF opcional para evitar dependencia circular
) -> bytes:
    """
    PDF moderno estilo informe ejecutivo - diseño limpio y profesional.
    
    Args:
        symbol: Ticker del activo
        company_name: Nombre de la empresa
        ratios: Dict con métricas financieras
        alerts: Dict con alertas y señales
        score: Score total
        dcf_calculator: Función opcional para calcular DCF
    
    Returns:
        bytes del PDF generado
    """
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        topMargin=0.4*inch, 
        bottomMargin=0.4*inch,
        leftMargin=0.5*inch, 
        rightMargin=0.5*inch
    )
    
    story = []
    pw = 7.5*inch
    
    # Colores
    PRIMARY = '#059669'      # Verde esmeralda
    DARK = '#1e293b'         # Slate oscuro
    MUTED = '#64748b'        # Gris
    LIGHT_BG = '#f8fafc'     # Fondo claro
    SUCCESS = '#22c55e'
    WARNING = '#f59e0b'  
    DANGER = '#ef4444'
    
    # Wrapper de fmt con "—" para PDFs (en vez de "N/A")
    def fmt(val, tipo="x"):
        # Mapeo de tipos: "x" -> "number", "%" -> "percent", "$" -> "currency"
        tipo_map = {"x": "number", "%": "percent", "$": "currency"}
        return fmt_base(val, tipo_map.get(tipo, tipo), na_text="—")
    
    sv2 = alerts.get("score_v2", {})
    ts = sv2.get("score", score)
    lv = sv2.get("level", "N/A")
    cs = sv2.get("category_scores", {})
    
    # ══════════════════════════════════════════════════════════════
    # HEADER PRINCIPAL
    # ══════════════════════════════════════════════════════════════
    header_left = f"{symbol}"
    header_right = company_name[:35]
    
    header = Table([
        [header_left, "", header_right]
    ], colWidths=[1.5*inch, pw-4*inch, 2.5*inch])
    header.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,0), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,0), 'Helvetica'),
        ('FONTSIZE', (0,0), (0,0), 24),
        ('FONTSIZE', (2,0), (2,0), 11),
        ('TEXTCOLOR', (0,0), (0,0), colors.HexColor(PRIMARY)),
        ('TEXTCOLOR', (2,0), (2,0), colors.HexColor(MUTED)),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (2,0), (2,0), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(header)
    
    # Línea separadora verde
    line = Table([[""]], colWidths=[pw])
    line.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,0), 3, colors.HexColor(PRIMARY)),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(line)
    
    # ══════════════════════════════════════════════════════════════
    # RESUMEN EJECUTIVO - Score y Recomendación
    # ══════════════════════════════════════════════════════════════
    
    # Determinar colores según score
    if ts >= 70: 
        score_color = SUCCESS
        score_text = "FAVORABLE"
    elif ts >= 50: 
        score_color = WARNING
        score_text = "NEUTRAL"
    else: 
        score_color = DANGER
        score_text = "PRECAUCIÓN"
    
    sig = alerts.get("signal", "—")
    gr = "Growth" if sv2.get("is_growth_company", False) else "Value"
    price = ratios.get("price")
    
    exec_data = [
        ["SCORE", "EVALUACIÓN", "SEÑAL", "TIPO", "PRECIO"],
        [f"{ts}/100", lv, sig, gr, fmt(price, "$")]
    ]
    exec_table = Table(exec_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    exec_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica'),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('FONTSIZE', (0,1), (-1,1), 14),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor(MUTED)),
        ('TEXTCOLOR', (0,1), (0,1), colors.HexColor(score_color)),
        ('TEXTCOLOR', (1,1), (-1,1), colors.HexColor(DARK)),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(LIGHT_BG)),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(exec_table)
    story.append(Spacer(1, 12))
    
    # ══════════════════════════════════════════════════════════════
    # DESGLOSE DEL SCORE POR CATEGORÍA
    # ══════════════════════════════════════════════════════════════
    
    def score_bar_text(val, max_val=20):
        pct = (val / max_val) * 100 if max_val > 0 else 0
        return f"{val:.0f}/{max_val}"
    
    cat_data = [
        ["Categoría", "Puntuación", ""],
        ["Valoración", score_bar_text(cs.get('valoracion', 0)), "Métricas P/E, P/B, EV/EBITDA, etc."],
        ["Rentabilidad", score_bar_text(cs.get('rentabilidad', 0)), "ROE, ROA, márgenes operativos"],
        ["Solidez", score_bar_text(cs.get('solidez', 0)), "Liquidez, deuda, cobertura"],
        ["Calidad", score_bar_text(cs.get('calidad', 0)), "Consistencia, flujos de caja"],
        ["Crecimiento", score_bar_text(cs.get('crecimiento', 0)), "Tendencias de ingresos y EPS"],
    ]
    cat_table = Table(cat_data, colWidths=[1.8*inch, 1.2*inch, 4.5*inch])
    cat_styles = [
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('FONTSIZE', (0,1), (0,-1), 10),
        ('FONTSIZE', (1,1), (1,-1), 11),
        ('FONTSIZE', (2,1), (2,-1), 8),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor(MUTED)),
        ('TEXTCOLOR', (0,1), (0,-1), colors.HexColor(DARK)),
        ('TEXTCOLOR', (1,1), (1,-1), colors.HexColor(PRIMARY)),
        ('TEXTCOLOR', (2,1), (2,-1), colors.HexColor(MUTED)),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('ALIGN', (2,0), (2,-1), 'LEFT'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor(LIGHT_BG)),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]
    cat_table.setStyle(TableStyle(cat_styles))
    story.append(cat_table)
    story.append(Spacer(1, 15))
    
    # ══════════════════════════════════════════════════════════════
    # MÉTRICAS CLAVE - 3 columnas
    # ══════════════════════════════════════════════════════════════
    
    section_title = Table([["MÉTRICAS FINANCIERAS"]], colWidths=[pw])
    section_title.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor(PRIMARY)),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor(PRIMARY)),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(section_title)
    
    # Tres columnas de métricas
    col_width = pw / 3
    
    def metric_block(title, metrics):
        """Crea un bloque de métricas"""
        rows = [[title, ""]]
        for name, value in metrics:
            rows.append([name, value])
        t = Table(rows, colWidths=[1.5*inch, 1*inch])
        styles = [
            ('FONTNAME', (0,0), (0,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (0,0), 9),
            ('TEXTCOLOR', (0,0), (0,0), colors.HexColor(DARK)),
            ('FONTNAME', (0,1), (0,-1), 'Helvetica'),
            ('FONTNAME', (1,1), (1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('TEXTCOLOR', (0,1), (0,-1), colors.HexColor(MUTED)),
            ('TEXTCOLOR', (1,1), (1,-1), colors.HexColor(DARK)),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]
        t.setStyle(TableStyle(styles))
        return t
    
    # Columna 1: Valoración
    val_metrics = [
        ("P/E", fmt(ratios.get("pe"))),
        ("Forward P/E", fmt(ratios.get("forward_pe"))),
        ("P/B", fmt(ratios.get("pb"))),
        ("EV/EBITDA", fmt(ratios.get("ev_ebitda"))),
        ("PEG", fmt(ratios.get("peg"))),
        ("FCF Yield", fmt(ratios.get("fcf_yield"), "%")),
    ]
    
    # Columna 2: Rentabilidad
    rent_metrics = [
        ("ROE", fmt(ratios.get("roe"), "%")),
        ("ROA", fmt(ratios.get("roa"), "%")),
        ("ROIC", fmt(ratios.get("roic"), "%")),
        ("Margen Bruto", fmt(ratios.get("gross_margin"), "%")),
        ("Margen Op.", fmt(ratios.get("operating_margin"), "%")),
        ("Margen Neto", fmt(ratios.get("net_margin"), "%")),
    ]
    
    # Columna 3: Solidez
    sol_metrics = [
        ("Current Ratio", fmt(ratios.get("current_ratio"))),
        ("Quick Ratio", fmt(ratios.get("quick_ratio"))),
        ("D/E", fmt(ratios.get("debt_to_equity"))),
        ("Net D/EBITDA", fmt(ratios.get("net_debt_to_ebitda"))),
        ("Int. Coverage", fmt(ratios.get("interest_coverage"))),
        ("Beta", fmt(ratios.get("beta"))),
    ]
    
    metrics_row = Table([
        [metric_block("Valoración", val_metrics), 
         metric_block("Rentabilidad", rent_metrics),
         metric_block("Solidez", sol_metrics)]
    ], colWidths=[col_width, col_width, col_width])
    metrics_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(metrics_row)
    story.append(Spacer(1, 12))
    
    # ══════════════════════════════════════════════════════════════
    # VALOR INTRÍNSECO
    # ══════════════════════════════════════════════════════════════
    
    section_title2 = Table([["VALOR INTRÍNSECO"]], colWidths=[pw])
    section_title2.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor(PRIMARY)),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor(PRIMARY)),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(section_title2)
    
    # Cálculos de valor intrínseco
    eps = ratios.get("eps")
    bvps = ratios.get("book_value_per_share")
    graham = (22.5 * eps * bvps) ** 0.5 if eps and bvps and eps > 0 and bvps > 0 else None
    fcf = ratios.get("fcf")
    shares = ratios.get("shares_outstanding")
    
    dcf_value = None
    if dcf_calculator and fcf and shares and fcf > 0 and shares > 0:
        try:
            growth_val = ratios.get("revenue_cagr_3y", 0.05) or 0.05
            growth_val = min(max(growth_val, 0.02), 0.35)
            dcf_pdf = dcf_calculator(fcf=fcf, shares_outstanding=shares, revenue_growth_3y=growth_val)
            dcf_value = dcf_pdf.get("fair_value_per_share")
        except (TypeError, ValueError, ZeroDivisionError, KeyError): 
            pass
    
    # Calcular upside/downside
    def calc_diff(fair, current):
        if fair and current and current > 0:
            diff = ((fair - current) / current) * 100
            return f"{diff:+.0f}%"
        return "—"
    
    zs = alerts.get('altman_z_score', {})
    fs = alerts.get('piotroski_f_score', {})
    zv = zs.get('value') if isinstance(zs, dict) else None
    zl = zs.get('level', '') if isinstance(zs, dict) else ''
    fv = fs.get('value') if isinstance(fs, dict) else None
    
    intrinsic_data = [
        ["Método", "Valor Justo", "vs Precio", "Interpretación"],
        ["Graham Number", fmt(graham, "$"), calc_diff(graham, price), "Fórmula clásica de valor"],
        ["DCF Multi-Stage", fmt(dcf_value, "$"), calc_diff(dcf_value, price), "Flujos descontados a 10 años"],
        ["Altman Z-Score", f"{zv:.2f}" if zv else "—", "", "Segura" if zl == 'SAFE' else "Gris" if zl == 'GREY' else "Riesgo" if zl else "—"],
        ["Piotroski F-Score", f"{fv}/9" if fv is not None else "—", "", "8-9: Fuerte | 0-3: Débil"],
    ]
    
    intrinsic_table = Table(intrinsic_data, colWidths=[1.8*inch, 1.5*inch, 1.2*inch, 3*inch])
    intrinsic_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor(MUTED)),
        ('TEXTCOLOR', (0,1), (0,-1), colors.HexColor(DARK)),
        ('TEXTCOLOR', (1,1), (1,-1), colors.HexColor(PRIMARY)),
        ('TEXTCOLOR', (3,1), (3,-1), colors.HexColor(MUTED)),
        ('ALIGN', (1,0), (2,-1), 'CENTER'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor(LIGHT_BG)),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(intrinsic_table)
    story.append(Spacer(1, 12))
    
    # ══════════════════════════════════════════════════════════════
    # SEÑALES DETECTADAS
    # ══════════════════════════════════════════════════════════════
    
    section_title3 = Table([["SEÑALES Y ALERTAS"]], colWidths=[pw])
    section_title3.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor(PRIMARY)),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor(PRIMARY)),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(section_title3)
    
    # Recopilar señales
    danger_list = []
    warning_list = []
    success_list = []
    
    # Valoración
    val = alerts.get("valuation", {})
    for reason in val.get("overvalued_reasons", []):
        danger_list.append(("Valoración", reason))
    for reason in val.get("undervalued_reasons", []):
        success_list.append(("Valoración", reason))
    
    # Deuda/Apalancamiento
    lev = alerts.get("leverage", {})
    for reason in lev.get("warning_reasons", []):
        danger_list.append(("Deuda", reason))
    for reason in lev.get("positive_reasons", []):
        success_list.append(("Deuda", reason))
    
    # Rentabilidad
    prof = alerts.get("profitability", {})
    for reason in prof.get("warning_reasons", []):
        warning_list.append(("Rentabilidad", reason))
    for reason in prof.get("positive_reasons", []):
        success_list.append(("Rentabilidad", reason))
    
    # Liquidez
    liq = alerts.get("liquidity", {})
    for reason in liq.get("warning_reasons", []):
        warning_list.append(("Liquidez", reason))
    for reason in liq.get("positive_reasons", []):
        success_list.append(("Liquidez", reason))
    
    # Flujo de Caja
    cf = alerts.get("cash_flow", {})
    for reason in cf.get("warning_reasons", []):
        danger_list.append(("Flujo de Caja", reason))
    for reason in cf.get("positive_reasons", []):
        success_list.append(("Flujo de Caja", reason))
    
    # Crecimiento
    growth = alerts.get("growth", {})
    for reason in growth.get("warning_reasons", []):
        warning_list.append(("Crecimiento", reason))
    for reason in growth.get("positive_reasons", []):
        success_list.append(("Crecimiento", reason))
    
    # Volatilidad
    vol = alerts.get("volatility", {})
    for reason in vol.get("warning_reasons", []):
        warning_list.append(("Volatilidad", reason))
    for reason in vol.get("positive_reasons", []):
        success_list.append(("Volatilidad", reason))
    
    # Extraer alertas de score_v2 categories
    score_v2 = alerts.get("score_v2", {})
    categories = score_v2.get("categories", [])
    for cat in categories:
        adjustments = cat.get("adjustments", [])
        for adj in adjustments:
            if adj.get("adjustment", 0) < -2:
                danger_list.append((cat.get("category", ""), f"{adj.get('metric', '')}: {adj.get('reason', '')}"))
            elif adj.get("adjustment", 0) < 0:
                warning_list.append((cat.get("category", ""), f"{adj.get('metric', '')}: {adj.get('reason', '')}"))
            elif adj.get("adjustment", 0) > 2:
                success_list.append((cat.get("category", ""), f"{adj.get('metric', '')}: {adj.get('reason', '')}"))
    
    # Eliminar duplicados
    def unique_alerts(alerts_list):
        seen = set()
        result = []
        for cat, reason in alerts_list:
            key = (cat, reason[:50])
            if key not in seen:
                seen.add(key)
                result.append((cat, reason))
        return result
    
    danger_list = unique_alerts(danger_list)
    warning_list = unique_alerts(warning_list)
    success_list = unique_alerts(success_list)
    
    # Crear tabla de señales
    signal_rows = []
    for c, r in danger_list: 
        signal_rows.append(["●", f"{r[:70]}", "Riesgo"])
    for c, r in warning_list: 
        signal_rows.append(["●", f"{r[:70]}", "Atención"])
    for c, r in success_list: 
        signal_rows.append(["●", f"{r[:70]}", "Fortaleza"])
    
    if not signal_rows:
        signal_rows.append(["●", "Sin señales significativas detectadas", "Info"])
    
    sig_table = Table(signal_rows, colWidths=[0.3*inch, 5.7*inch, 1.5*inch])
    sig_styles = [
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#f1f5f9')),
    ]
    
    for i, row in enumerate(signal_rows):
        if row[2] == "Riesgo":
            sig_styles.append(('TEXTCOLOR', (0,i), (0,i), colors.HexColor(DANGER)))
            sig_styles.append(('TEXTCOLOR', (2,i), (2,i), colors.HexColor(DANGER)))
        elif row[2] == "Atención":
            sig_styles.append(('TEXTCOLOR', (0,i), (0,i), colors.HexColor(WARNING)))
            sig_styles.append(('TEXTCOLOR', (2,i), (2,i), colors.HexColor(WARNING)))
        else:
            sig_styles.append(('TEXTCOLOR', (0,i), (0,i), colors.HexColor(SUCCESS)))
            sig_styles.append(('TEXTCOLOR', (2,i), (2,i), colors.HexColor(SUCCESS)))
    
    sig_table.setStyle(TableStyle(sig_styles))
    story.append(sig_table)
    story.append(Spacer(1, 20))
    
    # ══════════════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════════════
    
    footer_line = Table([[""]], colWidths=[pw])
    footer_line.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,0), 1, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(footer_line)
    
    footer = Table([
        ["Finanzer", datetime.now().strftime('%d/%m/%Y %H:%M'), "Este documento no constituye asesoría financiera"]
    ], colWidths=[1.5*inch, 2*inch, 4*inch])
    footer.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,0), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (-1,0), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('TEXTCOLOR', (0,0), (0,0), colors.HexColor(PRIMARY)),
        ('TEXTCOLOR', (1,0), (-1,0), colors.HexColor(MUTED)),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('ALIGN', (2,0), (2,0), 'RIGHT'),
    ]))
    story.append(footer)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
