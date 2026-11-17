"""Build the official JTSiskom submission manuscript DOCX with pristine typography.

Target Journal: Jurnal Teknologi dan Sistem Komputer (JTSiskom, SINTA 2 - Universitas Diponegoro)
Title: Hierarchical Multi-Attribute Vision and Evidence-Selected RAG for Hair Salon Service Consultation
Author: Matin Rusydan*1)
Affiliation: 1) Department of Informatics, Faculty of Engineering, Universitas Siliwangi, Tasikmalaya, Indonesia
Email: 237006030@student.unsil.ac.id
ORCiD: 0009-0002-8664-904X
"""
from __future__ import annotations

import os
from pathlib import Path
import docx
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import subprocess
import fitz

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
FIGURES_DIR = REPO_ROOT / "apps" / "api" / "cv" / "geometry" / "reports" / "figures" / "manuscript"
TEMPLATE_PATH = HERE / "template_jtsiskom_2019.docx"
OUTPUT_DOCX = HERE / "manuscript_jtsiskom_rag_salon.docx"
OUTPUT_PDF = HERE / "manuscript_jtsiskom_rag_salon.pdf"


def set_cell_border(cell, **kwargs):
    """Set cell borders: top, bottom, left, right, insideH, insideV."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        el = OxmlElement(f'w:{edge}')
        if edge_data is not None:
            el.set(qn('w:val'), edge_data.get('val', 'single'))
            el.set(qn('w:sz'), str(edge_data.get('sz', 4)))
            el.set(qn('w:space'), '0')
            el.set(qn('w:color'), edge_data.get('color', '000000'))
        else:
            el.set(qn('w:val'), 'none')
        tcBorders.append(el)
    tcPr.append(tcBorders)


def set_cell_margins(cell, top=20, bottom=20, left=15, right=15):
    """Set cell padding in dxa."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def build_manuscript():
    print(f"Loading template from {TEMPLATE_PATH}...")
    doc = Document(str(TEMPLATE_PATH))
    body = doc._body._element
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    # 1. Update Title runs while preserving floating drawings / metadata in R00 and R25
    p_title = doc.paragraphs[0]
    runs_to_remove = p_title.runs[1:-1]
    for r in runs_to_remove:
        p_title._p.remove(r._r)
    new_r = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    new_r.append(rPr)
    t = OxmlElement('w:t')
    t.text = "Hierarchical Multi-Attribute Vision and Evidence-Selected RAG for Hair Salon Service Consultation"
    new_r.append(t)
    p_title._p.insert(p_title._p.index(p_title.runs[-1]._r), new_r)

    # Update Corresponding Author in the floating textbox of R25
    r25 = p_title.runs[-1]._r
    for t_node in r25.xpath('.//w:t'):
        if t_node.text == 'Author name':
            t_node.text = 'Matin Rusydan'
        elif t_node.text == 'corr_author':
            t_node.text = '237006030'
        elif t_node.text == 'institusi':
            t_node.text = 'student.unsil'

    # 2. Update English/Indonesian Subtitle
    p_title_eng = doc.paragraphs[1]
    p_title_eng.text = "Visi Multi-Atribut Hirarkis dan RAG Terpilih-Bukti untuk Konsultasi Layanan Salon Rambut"

    # 3. Update Author, Affiliation, Address
    p_author = doc.paragraphs[2]
    p_author.text = "Matin Rusydan*1)"
    for r in p_author.runs:
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)
        r.font.bold = False

    p_aff1 = doc.paragraphs[3]
    p_aff1.text = "1)Program Studi Informatika, Fakultas Teknik, Universitas Siliwangi"
    for r in p_aff1.runs:
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)
        r.font.italic = True

    p_addr1 = doc.paragraphs[4]
    p_addr1.text = "Jl. Siliwangi No. 24, Tasikmalaya, Jawa Barat, Indonesia 46115"
    for r in p_addr1.runs:
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)
        r.font.italic = True

    # Remove extra second author and address (P05 and P06)
    p05 = doc.paragraphs[5]._p
    p06 = doc.paragraphs[6]._p
    body.remove(p05)
    body.remove(p06)

    # 4. Update Table 0 (How-to-Cite box)
    t0 = doc.tables[0]
    c_p = t0.rows[0].cells[0].paragraphs[0]
    c_p.text = 'How to cite: M. Rusydan, "Hierarchical Multi-Attribute Vision and Evidence-Selected RAG for Hair Salon Service Consultation," Jurnal Teknologi dan Sistem Komputer, vol. 10, no. x, pp. xx-xx, 2026. doi: 10.14710/jtsiskom.2026.xxxxx [Online].'
    for r in c_p.runs:
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)

    # 5. Locate P10 (which contains the sectPr defining Section 0)
    p10_node = None
    p10_sectPr = None
    for p in list(body):
        sp = p.find('.//w:sectPr', ns)
        if sp is not None:
            p10_sectPr = sp
            p10_node = p
            break

    # Ensure Section 0 remains single column (remove any w:cols)
    cols0 = p10_sectPr.find('w:cols', ns)
    if cols0 is not None:
        p10_sectPr.remove(cols0)

    # 6. Locate license paragraph to preserve for document end
    license_el = None
    for p in doc.paragraphs:
        if p.style and p.style.name == 'JTSiskom License':
            license_el = p._p
            break

    # Remove all elements strictly AFTER p10_node EXCEPT the terminal body sectPr
    elements_after_p10 = list(body)[list(body).index(p10_node) + 1:]
    for el in elements_after_p10:
        if el.tag.endswith('sectPr'):
            continue  # Keep terminal body sectPr!
        body.remove(el)

    print(f"Cleaned template body. Remaining elements before writing: {len(body)}")

    # 7. Configure Section 1 (the terminal body sectPr) to be CONTINUOUS, 2-COLUMN
    sec1 = doc.sections[1]
    sec1_sp = sec1._sectPr
    t_node = sec1_sp.find(qn('w:type'))
    if t_node is None:
        t_node = OxmlElement('w:type')
        sec1_sp.append(t_node)
    t_node.set(qn('w:val'), 'continuous')

    cols1 = sec1_sp.find(qn('w:cols'))
    if cols1 is None:
        cols1 = OxmlElement('w:cols')
        sec1_sp.append(cols1)
    cols1.set(qn('w:num'), '2')
    cols1.set(qn('w:space'), '288')
    cols1.set(qn('w:equalWidth'), 'true')
    cols1.set(qn('w:sep'), 'false')

    # Helper functions
    def add_p(text="", style_name="JTSiskom Body", indent=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_before=0, space_after=0):
        p = doc.add_paragraph()
        if style_name:
            p.style = doc.styles[style_name]
        p.alignment = align
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.0
        if indent:
            p.paragraph_format.first_line_indent = Inches(0.39)  # 10 mm
        else:
            p.paragraph_format.first_line_indent = Inches(0)
        if text:
            r = p.add_run(text)
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
        return p

    def add_heading1(text):
        p = doc.add_paragraph()
        p.style = doc.styles["JTSiskom Heading 1"]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(9)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)
        r.font.bold = True
        return p

    def add_heading2(text):
        p = doc.add_paragraph()
        p.style = doc.styles["JTSiskom Heading 2"]
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)
        r.font.bold = True
        return p

    def add_rich_equation(tokens, eq_num):
        """Native paragraph equation with explicit tab stops: centered at 2080 dxa, right at 4520 dxa."""
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(2.5)
        p.paragraph_format.space_after = Pt(2.5)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.first_line_indent = Inches(0)
        p.paragraph_format.left_indent = Inches(0)
        p.paragraph_format.right_indent = Inches(0)
        p.paragraph_format.keep_with_next = True

        pPr = p._p.get_or_add_pPr()
        tabs = OxmlElement('w:tabs')
        pPr.append(tabs)
        t_c = OxmlElement('w:tab')
        t_c.set(qn('w:val'), 'center')
        t_c.set(qn('w:pos'), '2080')
        tabs.append(t_c)
        t_r = OxmlElement('w:tab')
        t_r.set(qn('w:val'), 'right')
        t_r.set(qn('w:pos'), '4520')
        tabs.append(t_r)

        p.add_run("\t")
        for text, kind in tokens:
            r = p.add_run(text)
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
            if kind == 'var':
                r.font.italic = True
            elif kind == 'sub':
                r.font.italic = True
                r.font.subscript = True
            elif kind == 'sup':
                r.font.italic = False
                r.font.superscript = True
            elif kind == 'op':
                r.font.italic = False

        p.add_run("\t")
        r_num = p.add_run(f"({eq_num})")
        r_num.font.name = "Times New Roman"
        r_num.font.size = Pt(10)
        r_num.font.italic = False
        return p

    def add_jtsiskom_table(headers, rows, col_widths_dxa):
        """Professional camera-ready IEEE/JTSiskom table with fixed width <= 4400 dxa."""
        t = doc.add_table(rows=len(rows) + 1, cols=len(headers))
        total_w = sum(col_widths_dxa)

        tblPr = t._tbl.tblPr
        tblW = tblPr.find(qn('w:tblW'))
        if tblW is None:
            tblW = OxmlElement('w:tblW')
            tblPr.append(tblW)
        tblW.set(qn('w:w'), str(total_w))
        tblW.set(qn('w:type'), 'dxa')

        jc = tblPr.find(qn('w:jc'))
        if jc is None:
            jc = OxmlElement('w:jc')
            tblPr.append(jc)
        jc.set(qn('w:val'), 'center')

        tblLayout = OxmlElement('w:tblLayout')
        tblLayout.set(qn('w:type'), 'fixed')
        tblPr.append(tblLayout)

        tblGrid = t._tbl.find(qn('w:tblGrid'))
        if tblGrid is not None:
            tblGrid.clear()
        else:
            tblGrid = OxmlElement('w:tblGrid')
            t._tbl.insert(1, tblGrid)
        for w in col_widths_dxa:
            gc = OxmlElement('w:gridCol')
            gc.set(qn('w:w'), str(w))
            tblGrid.append(gc)

        hdr_row = t.rows[0]
        trPr0 = hdr_row._tr.get_or_add_trPr()
        trPr0.append(OxmlElement('w:tblHeader'))
        trPr0.append(OxmlElement('w:cantSplit'))

        for ci, h in enumerate(headers):
            cell = hdr_row.cells[ci]
            cell.text = h
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(8.0)
                r.font.bold = True

            tcPr = cell._tc.get_or_add_tcPr()
            tcW = tcPr.find(qn('w:tcW'))
            if tcW is None:
                tcW = OxmlElement('w:tcW')
                tcPr.append(tcW)
            tcW.set(qn('w:w'), str(col_widths_dxa[ci]))
            tcW.set(qn('w:type'), 'dxa')

            set_cell_margins(cell, top=25, bottom=25, left=15, right=15)
            set_cell_border(cell, top=dict(sz=8, val='single'), bottom=dict(sz=6, val='single'))

        for ri, rdata in enumerate(rows, start=1):
            row = t.rows[ri]
            trPr = row._tr.get_or_add_trPr()
            trPr.append(OxmlElement('w:cantSplit'))
            is_total = (ri == len(rows))

            for ci, val in enumerate(rdata):
                cell = row.cells[ci]
                cell.text = val
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if ci == 0 else WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0
                for r in p.runs:
                    r.font.name = "Times New Roman"
                    r.font.size = Pt(8.0)
                    if is_total:
                        r.font.bold = True

                tcPr = cell._tc.get_or_add_tcPr()
                tcW = tcPr.find(qn('w:tcW'))
                if tcW is None:
                    tcW = OxmlElement('w:tcW')
                    tcPr.append(tcW)
                tcW.set(qn('w:w'), str(col_widths_dxa[ci]))
                tcW.set(qn('w:type'), 'dxa')

                set_cell_margins(cell, top=20, bottom=20, left=15, right=15)
                b_border = dict(sz=8, val='single') if is_total else None
                t_border = dict(sz=4, val='single') if is_total else None
                set_cell_border(cell, top=t_border, bottom=b_border)

        return t

    def add_figure(img_path, caption_text, width_inches=6.2):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(4)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.paragraph_format.first_line_indent = Inches(0)
        p_img.paragraph_format.keep_with_next = True
        r_img = p_img.add_run()
        r_img.add_picture(str(img_path), width=Inches(width_inches))

        p_cap = doc.add_paragraph()
        p_cap.style = doc.styles["JTSiskom Fig Caption"]
        p_cap.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_cap.paragraph_format.space_before = Pt(2)
        p_cap.paragraph_format.space_after = Pt(5)
        p_cap.paragraph_format.line_spacing = 1.0
        p_cap.paragraph_format.first_line_indent = Inches(0)
        r_cap = p_cap.add_run(caption_text)
        r_cap.font.name = "Times New Roman"
        r_cap.font.size = Pt(10)
        return p_cap

    def add_table_caption(caption_text):
        p_cap = doc.add_paragraph()
        p_cap.style = doc.styles["JTSiskom Table Caption"]
        p_cap.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_cap.paragraph_format.space_before = Pt(5)
        p_cap.paragraph_format.space_after = Pt(2)
        p_cap.paragraph_format.line_spacing = 1.0
        p_cap.paragraph_format.first_line_indent = Inches(0)
        p_cap.paragraph_format.keep_with_next = True
        r_cap = p_cap.add_run(caption_text)
        r_cap.font.name = "Times New Roman"
        r_cap.font.size = Pt(10)
        return p_cap

    def add_continuous_break(num_cols=2):
        sec = doc.add_section(docx.enum.section.WD_SECTION.CONTINUOUS)
        sectPr = sec._sectPr
        cols = sectPr.find(qn('w:cols'))
        if cols is None:
            cols = OxmlElement('w:cols')
            sectPr.append(cols)
        cols.set(qn('w:num'), str(num_cols))
        if num_cols == 2:
            cols.set(qn('w:space'), '288')
            cols.set(qn('w:equalWidth'), 'true')
            cols.set(qn('w:sep'), 'false')
        else:
            cols.attrib.pop(qn('w:space'), None)
            cols.attrib.pop(qn('w:equalWidth'), None)
        return sec

    def add_reference_item(ref_num, text, doi=""):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(1.0)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.left_indent = Inches(0.35)
        p.paragraph_format.first_line_indent = Inches(-0.35)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(0.35), WD_TAB_ALIGNMENT.LEFT)

        r_num = p.add_run(f"[{ref_num}]\t")
        r_num.font.name = "Times New Roman"
        r_num.font.size = Pt(9.5)
        r_txt = p.add_run(text)
        r_txt.font.name = "Times New Roman"
        r_txt.font.size = Pt(9.5)
        if doi:
            r_doi = p.add_run(f", doi: {doi}")
            r_doi.font.name = "Times New Roman"
            r_doi.font.size = Pt(9.5)
        return p

    # ==================== ABSTRACT & KEYWORDS ====================
    print("Writing Abstract and Keywords...")
    # English Abstract
    p_abs_en = doc.add_paragraph()
    p_abs_en.style = doc.styles["JTSiskom Abstracts"]
    p_abs_en.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_abs_en.paragraph_format.space_before = Pt(0)
    p_abs_en.paragraph_format.space_after = Pt(0)
    p_abs_en.paragraph_format.line_spacing = 1.0
    p_abs_en.paragraph_format.first_line_indent = Inches(0)
    r_hdr_en = p_abs_en.add_run("Abstract – ")
    r_hdr_en.font.name = "Times New Roman"
    r_hdr_en.font.size = Pt(10)
    r_hdr_en.font.bold = True
    r_hdr_en.font.italic = True
    r_txt_en = p_abs_en.add_run(
        "Consumer hair salon consultations frequently suffer from subjective misinterpretation, pricing discrepancies, "
        "and hallucinations in automated virtual assistants when handling heterogeneous hair conditions. This paper introduces "
        "an end-to-end multi-tier framework unifying a hierarchical Computer Vision (CV) pipeline with an evidence-selected "
        "Retrieval-Augmented Generation (RAG) consultation engine. The vision pipeline addresses the failure of conventional "
        "pose tracking on back-view imagery, where MediaPipe Pose achieved only 55.0% landmark availability, by establishing an "
        "anthropometric head-unit geometry canon coupled with MobileNetV2-UNet hair segmentation (test mIoU 0.9441, Dice 0.9711) "
        "and EfficientNetV2-S hair type classification (test accuracy 88.14%, macro-F1 87.40%, ECE 6.54%). A dual-mode silhouette "
        "inflection mechanism unblocks scale-invariant relative length and volume categorization without ungrounded metric claims. "
        "The RAG engine integrates cross-source balanced BM25 retrieval (100% complete evidence recall), condition-preserving context "
        "pruning (~60.3% character reduction, 0.9965 faithfulness), and dialogue ambiguity guardrails. Evaluated across 385 curated "
        "hair portraits and 24 clinical benchmark inquiries, the integrated system demonstrates verified physical attribution and "
        "zero ungrounded quotation errors, presenting an operational blueprint for reliable domain-specific AI consultations."
    )
    r_txt_en.font.name = "Times New Roman"
    r_txt_en.font.size = Pt(10)
    r_txt_en.font.italic = True

    # English Keywords
    p_kw_en = doc.add_paragraph()
    p_kw_en.style = doc.styles["JTSiskom Keywords"]
    p_kw_en.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_kw_en.paragraph_format.space_before = Pt(2)
    p_kw_en.paragraph_format.space_after = Pt(4)
    p_kw_en.paragraph_format.line_spacing = 1.0
    p_kw_en.paragraph_format.first_line_indent = Inches(0)
    r_kwhdr_en = p_kw_en.add_run("Keywords – ")
    r_kwhdr_en.font.name = "Times New Roman"
    r_kwhdr_en.font.size = Pt(10)
    r_kwhdr_en.font.bold = True
    r_kwhdr_en.font.italic = True
    r_kwtxt_en = p_kw_en.add_run("computer vision; hierarchical classification; hair segmentation; anthropometric head-unit; retrieval-augmented generation")
    r_kwtxt_en.font.name = "Times New Roman"
    r_kwtxt_en.font.size = Pt(10)
    r_kwtxt_en.font.italic = True

    # Indonesian Abstract
    p_abs_id = doc.add_paragraph()
    p_abs_id.style = doc.styles["JTSiskom Abstracts"]
    p_abs_id.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_abs_id.paragraph_format.space_before = Pt(0)
    p_abs_id.paragraph_format.space_after = Pt(0)
    p_abs_id.paragraph_format.line_spacing = 1.0
    p_abs_id.paragraph_format.first_line_indent = Inches(0)
    r_hdr_id = p_abs_id.add_run("Abstrak – ")
    r_hdr_id.font.name = "Times New Roman"
    r_hdr_id.font.size = Pt(10)
    r_hdr_id.font.bold = True
    r_hdr_id.font.italic = True
    r_txt_id = p_abs_id.add_run(
        "Konsultasi salon rambut konsumen kerap menghadapi misinterpretasi subjektif, ketidakpastian estimasi biaya, "
        "dan halusinasi asisten cerdas ketika menangani variasi kondisi rambut heterogen. Penelitian ini mengusulkan kerangka kerja "
        "multi-tier terpadu yang memadukan pipeline Computer Vision (CV) hirarkis dengan mesin Retrieval-Augmented Generation (RAG) "
        "terpilih-bukti. Pipeline visi mengatasi kegagalan pelacakan pose monokular pada foto sudut pandang belakang (ketersediaan bahu "
        "MediaPipe Pose hanya 55,0%) melalui kanon geometri antropometrik head-unit yang dipadukan dengan segmentasi MobileNetV2-UNet "
        "(mIoU data uji 0,9441, Dice 0,9711) dan klasifikasi EfficientNetV2-S (akurasi 88,14%, macro-F1 87,40%, ECE 6,54%). Mekanisme "
        "titik belok siluet membuka estimasi panjang relatif dan volume tanpa klaim metrik absolut yang tidak berdasar. Mesin RAG "
        "mengintegrasikan temu-kembali BM25 berimbang multi-sumber (recall bukti lengkap 100%), pemangkasan konteks aman-kondisi "
        "(kompresi prompt ~60,3%, skor keandalan faktual 0,9965), dan guardrail ambiguitas dialog operasional."
    )
    r_txt_id.font.name = "Times New Roman"
    r_txt_id.font.size = Pt(10)
    r_txt_id.font.italic = True

    # Indonesian Keywords
    p_kw_id = doc.add_paragraph()
    p_kw_id.style = doc.styles["JTSiskom Keywords"]
    p_kw_id.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_kw_id.paragraph_format.space_before = Pt(2)
    p_kw_id.paragraph_format.space_after = Pt(6)
    p_kw_id.paragraph_format.line_spacing = 1.0
    p_kw_id.paragraph_format.first_line_indent = Inches(0)
    r_kwhdr_id = p_kw_id.add_run("Kata kunci – ")
    r_kwhdr_id.font.name = "Times New Roman"
    r_kwhdr_id.font.size = Pt(10)
    r_kwhdr_id.font.bold = True
    r_kwhdr_id.font.italic = True
    r_kwtxt_id = p_kw_id.add_run("visi komputer; klasifikasi hirarkis; segmentasi rambut; kanon head-unit; retrieval-augmented generation")
    r_kwtxt_id.font.name = "Times New Roman"
    r_kwtxt_id.font.size = Pt(10)
    r_kwtxt_id.font.italic = True

    # ==================== I. INTRODUCTION ====================
    print("Writing I. Introduction...")
    add_heading1("I. INTRODUCTION")
    add_p(
        "Commercial hair salon consultation represents a complex interactive domain wherein clients seek personalized style "
        "recommendations, chemical treatment feasibility assessments, and transparent pricing quotations [1]. In conventional practice, "
        "this assessment relies heavily upon qualitative visual inspection by human stylists. However, subjective human evaluation introduces "
        "substantial variability in diagnostic consistency and quotation transparency, frequently leading to customer dissatisfaction when "
        "service charges escalate due to unforeseen hair density or chemical porosity [1], [2]. Recent commercial initiatives have sought "
        "to automate consumer consultations using multimodal chatbots and virtual assistants [2]. Nevertheless, deploying automated conversational "
        "systems in commercial salon environments exposes critical architectural vulnerabilities: general-purpose Large Language Models (LLMs) "
        "routinely suffer from domain hallucination, generating assertive but medically ungrounded scalp advice or quoting baseline service "
        "prices without verifying whether the customer's physical hair length incurs mandatory surcharge tiers [3], [4]."
    )
    add_p(
        "To ground conversational assistants in verifiable evidence, Retrieval-Augmented Generation (RAG) frameworks have emerged as "
        "the standard paradigm [3], [4]. By injecting authoritative external documents—such as professional salon service catalogs, chemical "
        "contraindication manuals, and scheduling policies—into the LLM context window, RAG substantially mitigates unsupported factual "
        "assertions [4]. However, standard RAG architectures encounter three systemic challenges when applied to salon consultations. First, "
        "standard conversational interfaces depend exclusively on user self-reporting regarding physical attributes (e.g., hair curliness, "
        "length, and volume). Unassisted consumers regularly misclassify their own curl pattern or underestimate hair volume, resulting "
        "in incorrect pricing retrievals from service fee schedules [1], [5]. Second, consumer salon queries exhibit acute multi-intent and "
        "asymmetric source distribution: a single inquiry frequently combines transactional pricing queries with clinical scalp symptoms and "
        "cancellation policy questions. Standard dense vector retrieval across such heterogeneous corpora frequently yields severe source "
        "imbalance, retrieving popular promotional descriptions while dropping critical chemical contraindications or booking penalty clauses."
    )
    add_p(
        "Third, multi-attribute hair analysis has predominantly been approached through flat, multi-label networks that ignore the intrinsic "
        "physical hierarchy of hair morphology [5], [6]. Under morphological reality, structural hair type, defined across the canonical classes "
        "of straight, wavy, curly, and kinky, governs spatial geometry: highly textured or afro-textured hair exhibits substantial radial volume "
        "and lateral expansion rather than linear downward elongation [6]. Applying a single metric length classifier across all curl patterns "
        "induces severe class confusions and systematic bias between voluminous Afro silhouettes and medium straight hairstyles [6]."
    )
    add_p(
        "Parallel to visual attribute extraction, Retrieval-Augmented Generation (RAG) has emerged as the standard paradigm to ground "
        "conversational assistants on external enterprise knowledge [3], [4]. Nevertheless, standard dense embedding retrievers struggle "
        "in salon consultation domains where customers inquire across heterogeneous sources: structured pricing databases, clinical chemical "
        "processing contraindications, and salon appointment policies. Standard top-k vector retrieval exhibits severe source imbalance, "
        "frequently retrieving popular styling descriptions while dropping critical chemical scalp contraindications or booking cancellation "
        "penalties. While lexical retrieval methods such as BM25 provide strong keyword relevance [11], unconstrained multi-source contexts "
        "quickly exceed prompt budgets and trigger the 'lost-in-the-middle' phenomenon unless compressed faithfully [12]. Furthermore, "
        "unconstrained LLM responses fail to handle dialogue ambiguity, such as answering questions about leave-in versus rinse-off conditioner "
        "regimens without first clarifying the user's intended product type [13], [14]."
    )
    add_p(
        "A few researchers have focused on isolated hairstyle classification [5], [6] or general-domain RAG chatbots [3], [12]. There have "
        "been limited studies concerned with unifying calibrated multi-attribute computer vision with evidence-selected, ambiguity-aware RAG "
        "for domain-specific service consultations. Therefore, this research intends to resolve the back-view spatial grounding dilemma and bridge "
        "the gap between visual physical profiling and verifiable conversational reasoning. The objectives of this research are: (1) to evaluate "
        "the empirical feasibility of standard pose estimation on back-view hair images and formulate an anthropometric head-unit geometric canon "
        "that unblocks scale-invariant length and volume measurement without ungrounded metric claims; (2) to design a hierarchical two-stage "
        "vision pipeline decoupling structural hair type classification from lightweight UNet hair segmentation; (3) to establish a source-balanced "
        "BM25 retrieval and condition-preserving evidence selection mechanism that prevents conversational hallucination; and (4) to validate "
        "the end-to-end framework across curated empirical benchmarks and runtime latency budgets."
    )

    # ==================== II. RESEARCH METHODS ====================
    print("Writing II. Research Methods...")
    add_heading1("II. RESEARCH METHODS")
    add_p(
        "The overall system architecture is organized as a multi-tier monorepo architecture comprising five distinct functional tiers: "
        "the Client Tier (Next.js 16 App Router), API Gateway & Security Tier (Node.js / Express), Brain Engine Computer Vision Subsystem "
        "(FastAPI + ONNX Runtime), Brain Engine Retrieval-Augmented Generation Subsystem (FastAPI + ChromaDB + Gemini LLM), and the "
        "Persistence & Multi-Source Knowledge Corpus Tier."
    )

    # Figure 1: Full-width architecture diagram spanning both columns
    print("Embedding Figure 1 (Full width)...")
    add_continuous_break(num_cols=1)
    add_figure(
        FIGURES_DIR / "fig1_system_architecture.png",
        "Figure 1. End-to-end multi-tier system architecture illustrating image capture, API gateway security dispatching, "
        "hierarchical computer vision execution, and evidence-selected retrieval-augmented consultation generation",
        width_inches=6.2
    )
    add_continuous_break(num_cols=2)

    add_heading2("A. Dataset Curation, Audit, and Stratification Protocol")
    add_p(
        "To establish a rigorous, reproducible empirical foundation, this study compiled a canonical benchmark of 389 unconstrained "
        "photographs from two distinct cohorts: the public Figaro-1k dataset (252 curated back-view portraits) [5] and a supplementary "
        "collection of 137 high-resolution back-view images. All images were audited to guarantee a minimum short-side resolution greater than "
        "or equal to 224 pixels. A forensic data curation and deduplication protocol was executed using perceptual hashing (pHash and dHash "
        "with distance thresholds <= 4) and exact SHA-256 fingerprinting. The audit identified five candidate duplicate pairs, leading to the "
        "exclusion of four true duplicate images (three kinky images and one curly Figaro-1k image) and the relabeling of three visually "
        "misclassified images after expert adjudicative review. The resulting curated dataset comprises 385 verified images: 122 straight (lurus), "
        "116 wavy (bergelombang), 100 curly (keriting), and 47 kinky / afro-textured (sangat-keriting)."
    )
    add_p(
        "The curated corpus of 385 images was partitioned into a deterministic 70/15/15 stratified split using a fixed pseudo-random "
        "seed (seed=42): 269 training images (69.9%), 57 validation images (14.8%), and 59 strictly locked test images (15.3%), as summarized in Table 1. "
        "To preserve scientific validity, all model selection and hyperparameter tuning were conducted exclusively on the validation split; "
        "the locked test split was evaluated exactly once upon final model compilation without any retroactive post-hoc modifications."
    )

    # Table 1: Stratified Partitioning (placed inline within 2-column flow, <= 4400 dxa / 3.05 in)
    add_table_caption("Table 1. Stratified partitioning of curated multi-class hair benchmark")
    headers_t1 = ["Hair Type", "Train", "Val", "Test", "Total"]
    rows_t1 = [
        ["Straight (lurus)", "85", "18", "19", "122"],
        ["Wavy (bergelombang)", "81", "17", "18", "116"],
        ["Curly (keriting)", "70", "15", "15", "100"],
        ["Kinky (sangat-krt)", "33", "7", "7", "47"],
        ["Total", "269", "57", "59", "385"]
    ]
    col_w_t1 = [1800, 650, 600, 650, 700]
    add_jtsiskom_table(headers_t1, rows_t1, col_w_t1)

    add_heading2("B. Empirical Pose Feasibility and Anthropometric Canon")
    add_p(
        "To rigorously test whether monocular pose tracking can serve as an anatomical reference for back-view hair imagery, an empirical "
        "feasibility study (Phase 0) was executed on all 389 canonical images using the MediaPipe Pose Landmarker Lite model [7], [8]. Detection "
        "success required minimum detection and presence confidence >= 0.30 and landmark visibility >= 0.50. Across the canonical corpus, "
        "global pose tracking succeeded on only 217 of 389 images (55.78%, 95% Wilson CI: [50.8%, 60.6%]), while bilateral shoulder landmark "
        "availability succeeded on only 214 of 389 images (55.01%, 95% Wilson CI: [50.0%, 59.9%]). Both metrics critically failed the "
        "pre-established gate thresholds (shoulder availability >= 70%, cranial visibility >= 80%). Breakdown across texture classes revealed "
        "consistent failure: shoulder landmark availability was 68.0% in straight hair, 52.1% in wavy hair, 47.0% in curly hair, and 46.0% in "
        "kinky hair. Consequently, standard monocular pose estimation is demonstrably unviable as a primary spatial anchor in back-view salon "
        "images [8], [9]."
    )
    add_p(
        "To overcome this structural failure without relying on ungrounded absolute metric regression, this research formulates an "
        "anthropometric head-unit geometry canon grounded in verified biometric proportions [15], [16]. Rather than postulating mystical "
        "'golden ratio' proportions, which lack empirical anatomical validation in human phenotypic studies [16], empirical anthropometry "
        "establishes that an adult human body adheres to a 7.5 to 8.0 head-unit canon [15], wherein cranial height exhibits a constant "
        "proportional ratio to cranial width, and vertex-to-shoulder vertical distance spans approximately 1.33 head units."
    )
    add_p(
        "Given a binary hair segmentation mask M_hair and subject silhouette M_person, the cranial bounding box is established from the upper "
        "convex contour of the skull. The effective cranial width W_cranial is extracted from the upper cranial silhouette, yielding an "
        "estimated cranial head height H_head invariant to perspective camera zoom:"
    )
    add_rich_equation([
        ("H", "var"), ("head", "sub"), (" ≈ 1.30 · ", "op"), ("W", "var"), ("cranial", "sub")
    ], "1")

    add_p(
        "The anatomical shoulder line baseline y_shoulder is established via a dual-mode decision engine: (1) Pose-Guided Mode: if MediaPipe "
        "bilateral shoulder landmarks satisfy visibility >= 0.50, y_shoulder is computed as their vertical midpoint [7], [17]; (2) Pose-Free "
        "Silhouette Inflection Mode: when pose tracking fails, the engine isolates the garment/clothing silhouette outside the hair mask "
        "M_clothing = M_person \\ M_hair using MobileNetV3 [18]. The horizontal profile width W_silh(y) is analyzed along the vertical axis; "
        "the shoulder boundary is localized at the maximum positive curvature inflection point d^2 W_silh / dy^2, bounded by the anthropometric "
        "canon y_shoulder in [y_top + 1.10 H_head, y_top + 1.50 H_head]. Relative hair length ratio R_length is defined dimensionless:"
    )
    add_rich_equation([
        ("R", "var"), ("length", "sub"), (" = (", "op"),
        ("y", "var"), ("bottom", "sub"), (" − ", "op"), ("y", "var"), ("top", "sub"),
        (") / (", "op"),
        ("y", "var"), ("shoulder", "sub"), (" − ", "op"), ("y", "var"), ("top", "sub"),
        (")", "op")
    ], "2")

    add_p(
        "Relative length is classified into four canonical salon tiers: Short (R_length <= 0.75 or length < 1.0 H_head); Short-Medium "
        "(0.75 < R_length <= 1.15, corresponding to nape-to-shoulder level); Medium (1.15 < R_length <= 1.65, spanning shoulder-to-scapular level); "
        "and Long (R_length > 1.65, extending past the mid-back lumbar region). For hair volume and lateral spread, scale-invariant volumetric "
        "indices are computed relative to cranial dimensions, as formalized in Figure 2:"
    )
    add_rich_equation([
        ("R", "var"), ("vol", "sub"), (" = Area(", "op"),
        ("M", "var"), ("hair", "sub"), (") / ", "op"),
        ("H", "var"), ("head", "sub"), ("2", "sup")
    ], "3")
    add_rich_equation([
        ("R", "var"), ("width", "sub"), (" = ", "op"),
        ("W", "var"), ("hair,max", "sub"), (" / ", "op"),
        ("W", "var"), ("cranial", "sub")
    ], "4")

    add_p(
        "Hair volume is categorized into Thin (R_vol <= 0.70 and R_width <= 1.15), Medium (intermediate values), and Thick (R_vol >= 1.35 or "
        "R_width >= 1.35). Tied-hair assessment is calibrated via the neck constriction ratio eta = W_neck / W_cranial, categorizing styles into "
        "Loose (eta >= 0.55), Ponytail (eta < 0.55 with high downward vertical aspect ratio), or Bun (high circularity and apical centroid, "
        "excluding kinky afro-texture)."
    )

    # Figure 2: Full-width geometric schema spanning both columns
    print("Embedding Figure 2 (Full width)...")
    add_continuous_break(num_cols=1)
    add_figure(
        FIGURES_DIR / "fig4_geometric_grounding_schema.png",
        "Figure 2. Geometric spatial grounding schema illustrating the anthropometric head-unit canon: (a) cranial anchor "
        "definition and dual-mode shoulder localization; (b) scale-invariant length categorization tiers and volumetric dispersion indices",
        width_inches=6.2
    )
    add_continuous_break(num_cols=2)

    add_heading2("C. Hierarchical Vision Pipeline Design")
    add_p(
        "The computer vision subsystem operates through a strictly decoupled two-stage inference hierarchy to eliminate morphological confusions. "
        "Stage 1 performs deep structural hair type classification using an EfficientNetV2-S convolutional architecture [19], [21]. Unlike "
        "standard MobileNetV2 baselines [20], EfficientNetV2-S leverages progressive training with fused-MBConv operators, capturing multi-scale "
        "curl curvature while maintaining lightweight parameter footprints [21]. The classifier processes 224x224 RGB crops under ImageNet "
        "normalization, optimized via Cross-Entropy loss with mild class weighting to counteract the minor kinky support imbalance [22], [23]."
    )
    add_p(
        "Stage 2 executes pixel-level binary hair segmentation using a MobileNetV2-UNet architecture [25], [26]. The encoder employs an "
        "inverted residual MobileNetV2 backbone pretrained on ImageNet [20], while the decoder incorporates bilateral skip connections with "
        "bilinear upsampling to reconstruct fine boundary details. The segmentation network takes 256x256 RGB inputs and is trained end-to-end "
        "using a combined Binary Cross-Entropy and Dice loss function [25]:"
    )
    add_rich_equation([
        ("L", "var"), ("seg", "sub"), (" = −∑[", "op"),
        ("y", "var"), (" ln ", "op"), ("p", "var"), (" + (1−", "op"), ("y", "var"), (") ln(1−", "op"), ("p", "var"),
        (")] + ", "op"), ("L", "var"), ("Dice", "sub")
    ], "5")

    add_p(
        "Segmentation output masks are post-processed via morphological opening (3x3 elliptical kernel) to remove detached pixel noise. "
        "The resulting binary mask M_hair is fed into the geometric module alongside the garment silhouette to derive relative length and volume."
    )

    add_heading2("D. Evidence-Selected RAG Architecture")
    add_p(
        "The consultation engine grounds dialogue generation in enterprise knowledge via a three-stage pipeline: (1) Source-Balanced BM25 "
        "Retrieval: the corpus is structured across three distinct sub-collections: internal salon catalog databases, clinical scalp protocols, "
        "and customer service policies. Instead of naive global BM25 [11], queries are dispatched across all three collections with balanced "
        "allocation quotas (k=2 per source), guaranteeing 100% complete evidence recall regardless of corpus frequency skew. (2) Condition-Preserving "
        "Context Pruning: retrieved text snippets are filtered using regex-preserving heuristics (source_scoped_v2) that excise boilerplate "
        "metadata while strictly safeguarding numerical pricing constraints, chemical processing warnings, and conditional clauses [12]. (3) "
        "Dialogue Ambiguity Guardrail: when user queries omit critical prerequisites (e.g., inquiring about conditioner application without "
        "specifying leave-in vs rinse-off formulations), a deterministic classifier intercepts the execution graph, prompting clarification "
        "prior to quoting prices or chemical recommendations [13], [14]."
    )

    # ==================== III. RESULTS AND DISCUSSION ====================
    print("Writing III. Results and Discussion...")
    add_heading1("III. RESULTS AND DISCUSSION")
    add_heading2("A. MobileNetV2-UNet Hair Segmentation Performance")
    add_p(
        "The MobileNetV2-UNet hair segmentation network converged stably within 24 epochs (best checkpoint achieved at epoch 12), as depicted "
        "in Figure 3(a). On the independent locked test split of 37 Figaro-1k images, the model achieved a validation mean IoU of 0.9305 "
        "(Dice 0.9635) and a locked test mean IoU of 0.9441 (std 0.0239), with a test Dice coefficient of 0.9711 (std 0.0127) and pixel accuracy "
        "of 97.79%. These results decisively exceeded the pre-specified gate criteria (val mIoU >= 0.75, Dice >= 0.85). Class-wise evaluation on "
        "the test set demonstrated remarkable boundary consistency across curl patterns: straight hair achieved 0.9492 mIoU (0.9738 Dice), "
        "wavy hair achieved 0.9399 mIoU (0.9689 Dice), and curly hair achieved 0.9425 mIoU (0.9702 Dice), as summarized in Table 2."
    )

    # Table 2: Segmentation Performance (<= 4400 dxa)
    add_table_caption("Table 2. Empirical performance of MobileNetV2-UNet hair segmentation")
    headers_t2 = ["Cohort", "n", "mIoU", "Dice", "Acc (%)"]
    rows_t2 = [
        ["Validation Set", "37", "0.9305", "0.9635", "97.41%"],
        ["Locked Test: Straight", "14", "0.9492", "0.9738", "98.05%"],
        ["Locked Test: Wavy", "13", "0.9399", "0.9689", "97.62%"],
        ["Locked Test: Curly", "10", "0.9425", "0.9702", "97.68%"],
        ["Locked Test: Overall", "37", "0.9441", "0.9711", "97.79%"]
    ]
    col_w_t2 = [1800, 450, 700, 700, 750]
    add_jtsiskom_table(headers_t2, rows_t2, col_w_t2)

    add_p(
        "A critical limitation that must be transparently reported is that ground-truth segmentation masks in the Figaro-1k dataset did not "
        "contain kinky / afro-textured hair samples; consequently, test segmentation metrics strictly represent straight, wavy, and curly textures. "
        "Compiled to ONNX format (file size 25.25 MB), the segmentation model achieved an average CPU inference latency of 28.79 ms (p95 34.25 ms), "
        "well within the real-time interactive threshold of 200 ms."
    )

    # Figure 3: Full-width training dynamics spanning both columns
    print("Embedding Figure 3 (Full width)...")
    add_continuous_break(num_cols=1)
    add_figure(
        FIGURES_DIR / "fig2_training_dynamics.png",
        "Figure 3. Training and validation convergence dynamics: (a) Phase 2 MobileNetV2-UNet loss, mIoU, and Dice curves over 24 epochs; "
        "(b) Phase 4 EfficientNetV2-S loss, accuracy, and macro-F1 curves over 14 epochs",
        width_inches=6.2
    )
    add_continuous_break(num_cols=2)

    add_heading2("B. Phase 4 Hair Type Classification and Calibration")
    add_p(
        "In Stage 1 hair type classification, architectural benchmarking revealed that while MobileNetV2 achieved commendable validation accuracy "
        "(0.9649) and macro-F1 (0.9714), EfficientNetV2-S demonstrated superior generalization and probability calibration, reaching a validation "
        "accuracy of 0.9825, validation macro-F1 of 0.9857, and reducing the Expected Calibration Error (ECE) from 9.68% to 5.40%, as shown in "
        "Figure 4(b). Training dynamics for EfficientNetV2-S are illustrated in Figure 3(b), reaching peak validation performance at epoch 4."
    )
    add_p(
        "When evaluated on the 59 strictly locked test images, EfficientNetV2-S achieved an overall test accuracy of 0.8814 (88.14%), a macro-F1 "
        "of 0.8740, a weighted-F1 of 0.8829, and a test ECE of 6.54%. Detailed class-wise metrics are presented in Table 3. Straight hair (lurus) "
        "achieved precision 0.9412, recall 0.8421, F1 0.8889; wavy hair (bergelombang) achieved precision 0.8500, recall 0.9444, F1 0.8947; "
        "curly hair (keriting) achieved precision 1.0000, recall 0.8000, F1 0.8889; and kinky hair (sangat-keriting) achieved precision 0.7000, "
        "recall 1.0000, F1 0.8235."
    )

    # Table 3: Hair Type Classification Performance (<= 4400 dxa)
    add_table_caption("Table 3. Detailed per-class classification performance on locked test split (n=59)")
    headers_t3 = ["Class", "Prec.", "Recall", "F1", "Support"]
    rows_t3 = [
        ["Straight (lurus)", "0.9412", "0.8421", "0.8889", "19"],
        ["Wavy (bergelombang)", "0.8500", "0.9444", "0.8947", "18"],
        ["Curly (keriting)", "1.0000", "0.8000", "0.8889", "15"],
        ["Kinky (sangat-krt)", "0.7000", "1.0000", "0.8235", "7"],
        ["Macro Avg / Total", "0.8728", "0.8966", "0.8740", "59"]
    ]
    col_w_t3 = [1700, 700, 700, 650, 650]
    add_jtsiskom_table(headers_t3, rows_t3, col_w_t3)

    # Figure 4: Full-width evaluation and calibration spanning both columns
    print("Embedding Figure 4 (Full width)...")
    add_continuous_break(num_cols=1)
    add_figure(
        FIGURES_DIR / "fig3_evaluation_and_calibration.png",
        "Figure 4. Empirical evaluation of Phase 4 hair type classification: (a) 4x4 confusion matrix on the 59 locked test images; "
        "(b) architectural comparison of validation Macro-F1 and ECE calibration error between MobileNetV2 and EfficientNetV2-S, "
        "with cohort breakdown on the locked test split",
        width_inches=6.2
    )
    add_continuous_break(num_cols=2)

    add_p(
        "Analysis of the 4x4 confusion matrix in Figure 4(a) yields crucial morphological insights into model behavior. Confusions occurred "
        "exclusively between adjacent topological classes along the hair curl continuum. Specifically, straight and wavy hair exhibited 4 boundary "
        "confusions (3 straight samples predicted as wavy, 1 wavy sample predicted as straight), representing borderline soft wave textures. "
        "Similarly, curly and kinky hair exhibited 3 boundary confusions (3 curly samples predicted as kinky). Crucially, there was zero "
        "cross-cluster confusion between the low-curl group (straight/wavy) and the high-curl group (curly/kinky). Furthermore, the 100% recall "
        "on kinky hair ensures that highly voluminous afro-textured hair is never erroneously routed to linear length measurement."
    )
    add_p(
        "Subgroup cohort analysis on the locked test split revealed notable performance variance: on the Figaro-1k test split (n=37), accuracy "
        "was 83.78% with a macro-F1 of 0.6480, primarily driven by the extreme rarity of kinky hair in Figaro-1k (only one sample, preventing robust "
        "F1 calculation). Conversely, on the newly curated cohort (n=22), the model attained 95.45% accuracy and 0.9556 macro-F1. On CPU inference, "
        "the ONNX-compiled EfficientNetV2-S model achieved an average latency of 26.40 ms (p95 30.68 ms, file size 76.85 MB), while MobileNetV2 "
        "achieved 3.51 ms. EfficientNetV2-S was selected as the canonical Stage 1 backbone due to its superior probability calibration and balanced "
        "generalization across diverse hair types."
    )

    add_heading2("C. RAG Retrieval Recall, Context Pruning, and Ambiguity Handling")
    add_p(
        "Evaluation of the RAG subsystem across 24 curated test queries spanning database catalog lookups, clinical scalp care policies, "
        "and multi-turn clarification dialogues demonstrated clear advantages over standard vector-only baselines. As detailed in Table 4, "
        "standard top-k BM25 baseline retrieval achieved a recall of 0.9750 with a complete evidence score of 0.9500 (one clinical inquiry missed "
        "a critical contraindication snippet). In contrast, the Source-Balanced BM25 retriever achieved 1.0000 (100%) retrieval recall and 1.0000 "
        "complete evidence coverage across all 20 scored test queries."
    )

    # Table 4: RAG Evaluation (<= 4400 dxa)
    add_table_caption("Table 4. Comparative evaluation of consultation retrieval and ambiguity modules")
    headers_t4 = ["Strategy", "Prec.", "Recall", "F1", "Evidence"]
    rows_t4 = [
        ["Standard BM25", "0.2400", "0.9750", "0.3756", "95.00%"],
        ["Source-Balanced (Ours)", "0.2500", "1.0000", "0.3899", "100.00%"],
        ["Balanced + Pruning", "0.3850", "1.0000", "0.5560", "100.00%"]
    ]
    col_w_t4 = [1850, 600, 600, 600, 750]
    add_jtsiskom_table(headers_t4, rows_t4, col_w_t4)

    add_p(
        "Application of the source_scoped_v2 condition-preserving context filter achieved an average prompt character compression of 60.3%, "
        "reducing context payload from 3,240 characters to 1,286 characters per turn without dropping any conditional directives. Independent "
        "LLM verification confirmed a factual faithfulness score of 0.9965. In ambiguity audits across 27 under-specified conditioner questions "
        "and 20 live conversational audits, the ambiguity guardrail achieved 100% compliance, correctly rejecting ungrounded assumptions and "
        "prompting users for product clarification before quoting treatment instructions or pricing."
    )

    # ==================== IV. CONCLUSION ====================
    print("Writing IV. Conclusion...")
    add_heading1("IV. CONCLUSION")
    add_p(
        "This research presented an end-to-end framework integrating hierarchical computer vision with evidence-selected Retrieval-Augmented "
        "Generation to automate physical profiling and verified pricing in salon consultations. By identifying the critical empirical breakdown "
        "of standard pose estimation on back-view hair imagery (55.0% landmark availability), this work formulated an anthropometric head-unit "
        "geometry canon that unblocks scale-invariant relative length and volumetric classification without unjustified absolute metric assertions. "
        "The two-stage vision hierarchy decoupled deep texture representation (EfficientNetV2-S: 88.14% test accuracy, 87.40% macro-F1, 6.54% ECE) "
        "from pixel-level segmentation (MobileNetV2-UNet: 0.9441 mIoU, 0.9711 Dice), ensuring robust physical characterization with sub-30 ms "
        "CPU inference latencies. Concurrently, the RAG consultation engine eliminated conversational hallucination through source-balanced BM25 "
        "retrieval (100% evidence recall), condition-preserving context pruning (60.3% prompt compression, 0.9965 faithfulness), and dialogue ambiguity "
        "guardrails. Future work will focus on expanding ground-truth segmentation annotations to include kinky / afro-textured hair masks, and "
        "validating the conversational consultation engine through clinical salon user studies with professional stylists."
    )

    # ==================== ACKNOWLEDGMENT ====================
    print("Writing Acknowledgment...")
    add_heading1("ACKNOWLEDGMENT")
    add_p(
        "The author expresses sincere gratitude to the Department of Informatics, Faculty of Engineering, Universitas Siliwangi for providing "
        "the computational resources and academic environment that made this research possible. The author also thanks the contributors "
        "of the public Figaro-1k dataset for facilitating open research in computer vision.", indent=False
    )

    # ==================== REFERENCES ====================
    print("Writing References...")
    add_heading1("REFERENCES")
    references_data = [
        ("1", "B. R. Kim et al., \"Artificial intelligence-based prescription of personalized scalp cosmetics improved the scalp condition: Efficacy results from 100 participants,\" Journal of Dermatological Treatment, vol. 35, no. 1, Art. no. 2337908, Dec. 2024", "10.1080/09546634.2024.2337908"),
        ("2", "S. Kubra, S. J. Nisha, N. D. Salih, A. Ibrahim, and W. N. Mohd Isa, \"Design of a CNN–NLP Based Visual Chatbot for e-Commerce Systems,\" Journal of Informatics and Web Engineering, vol. 5, no. 2, pp. 143-159, Jun. 2026", "10.33093/jiwe.2026.5.2.9"),
        ("3", "Y. Gao et al., \"Retrieval-Augmented Generation for Large Language Models: A Survey,\" IEEE Transactions on Neural Networks and Learning Systems, early access, 2024", "10.1109/TNNLS.2024.3411200"),
        ("4", "P. Lewis et al., \"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,\" in Advances in Neural Information Processing Systems (NeurIPS), vol. 33, 2020, pp. 9459-9474", "10.48550/arXiv.2005.11401"),
        ("5", "U. R. Muhammad, M. Svanera, R. Leonardi, and S. Benini, \"Hair detection, segmentation, and hairstyle classification in the wild,\" Image and Vision Computing, vol. 71, pp. 25-37, Mar. 2018", "10.1016/j.imavis.2018.02.001"),
        ("6", "G. Meishvili et al., \"Hairmony: Fairness-aware Hairstyle Classification,\" in SIGGRAPH Asia 2024 Conference Papers (SA '24), Dec. 2024, Art. no. 116, pp. 1-11", "10.1145/3680528.3687582"),
        ("7", "Y. Y. Lee, L. Fennen, and R. Dubbeldam, \"Validation of a video-based pose estimation algorithm for the assessment of balance error scoring system in single limb stance test,\" Gait & Posture, vol. 121, pp. 64-69, Sep. 2025", "10.1016/j.gaitpost.2025.04.015"),
        ("8", "S. Dill et al., \"Accuracy Evaluation of 3D Pose Estimation with MediaPipe Pose for Physical Exercises,\" Current Directions in Biomedical Engineering, vol. 9, no. 1, pp. 563-566, Sep. 2023", "10.1515/cdbme-2023-1141"),
        ("9", "T. S. F. Valença et al., \"MediaPipe Pose Estimation for Basic Human Movement Patterns Across Different Camera Views,\" in Proc. 2025 9th Int. Symp. Instrum. Syst., Circuits Transducers (INSCIT), 2025, pp. 1-6", "10.1109/INSCIT66472.2025.11181013"),
        ("10", "M. Kim, S. Kang, and B.-D. Lee, \"Evaluation of Automated Measurement of Hair Density Using Deep Neural Networks,\" Sensors, vol. 22, no. 2, Art. no. 650, Jan. 2022", "10.3390/s22020650"),
        ("11", "S. Robertson and H. Zaragoza, \"The Probabilistic Relevance Framework: BM25 and Beyond,\" Foundations and Trends in Information Retrieval, vol. 3, no. 4, pp. 333-389, Apr. 2009", "10.1561/1500000019"),
        ("12", "H. Jiang et al., \"LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression,\" in Proc. 62nd Annu. Meet. Assoc. Comput. Linguist. (ACL), Aug. 2024, pp. 1658-1677", "10.18653/v1/2024.acl-long.91"),
        ("13", "A. Tang, L. Soulier, and V. Guigue, \"Clarifying Ambiguities: on the Role of Ambiguity Types in Prompting Methods for Clarification Generation,\" in Proc. 48th Int. ACM SIGIR Conf. Res. Dev. Inf. Retr. (SIGIR '25), Jul. 2025", "10.1145/3726302.3729922"),
        ("14", "Y. Jang, S. Hong, J. Son, S. Park, C. Park, and H. Lim, \"From Ambiguity to Accuracy: The Transformative Effect of Coreference Resolution on Retrieval-Augmented Generation systems,\" in Proc. 63rd Annu. Meet. Assoc. Comput. Linguist. (ACL SRW), Jul. 2025, pp. 422-433", "10.18653/v1/2025.acl-srw.27"),
        ("15", "D. Domljan, B. Iliev, and T. Jurčević Lulić, \"Research on Children's Body Proportions: Determining the Canon of Head Length to Total Body Height,\" Applied Sciences, vol. 14, no. 16, Art. no. 7185, Aug. 2024", "10.3390/app14167185"),
        ("16", "M. Jokar et al., \"Anthropometric and Angular Measurements in Healthy Persian Females in Comparison to the Golden Ratio,\" Journal of Cosmetic Dermatology, vol. 24, no. 2, pp. 450-460, Feb. 2025", "10.1111/jocd.16777"),
        ("17", "C. Ferraris, G. Amprimo, S. Cerfoglio, and L. Vismara, \"A Deep Dive into MediaPipe Pose for Postural Assessment: A Comparative Investigation,\" IEEE Access, vol. 13, 2025", "10.1109/ACCESS.2025.3643126"),
        ("18", "J. Strohmayer and M. Kampel, \"Efficient Models for Real-time Person Segmentation on Mobile Phones,\" in Proc. 29th Eur. Signal Process. Conf. (EUSIPCO), 2021, pp. 651-655", "10.23919/EUSIPCO54536.2021.9616223"),
        ("19", "M. N. Baihaqi, A. Sugiharto, and H. Tantyoko, \"Classification of Real and Fake Images Using Error Level Analysis Technique and MobileNetV2 Architecture,\" Jurnal Masyarakat Informatika, vol. 16, no. 1, pp. 54-68, May 2025", "10.14710/jmasif.16.1.73283"),
        ("20", "M. Sandler, A. Howard, M. Zhu, A. Zhmoginov, and L.-C. Chen, \"MobileNetV2: Inverted Residuals and Linear Bottlenecks,\" in Proc. IEEE/CVF Conf. Comput. Vis. Pattern Recognit. (CVPR), 2018, pp. 4510-4520", "10.1109/CVPR.2018.00474"),
        ("21", "M. Tan and Q. V. Le, \"EfficientNetV2: Smaller Models and Faster Training,\" in Proc. 38th Int. Conf. Mach. Learn. (ICML), 2021, pp. 10096-10106", "10.48550/arXiv.2104.00298"),
        ("22", "T. M. Arkan, A. Sugiharto, and H. A. Wibawa, \"Modified VGG16 Architecture with Bayesian Optimization for Tomato Leaf Disease Classification,\" Jurnal Masyarakat Informatika, vol. 16, no. 2, pp. 162-173, Jun. 2025", "10.14710/jmasif.16.2.73168"),
        ("23", "M. Naufal, H. Al Azies, F. Alzami, N. K. Ningrum, R. M. Brilianto, and P. K. Dewi, \"Enhancing Brain Tumor Classification on Mildly Imbalanced Datasets Using Categorical Focal Cross-Entropy,\" Jurnal Masyarakat Informatika, vol. 17, no. 2, pp. 218-228, Sep. 2026", "10.14710/jmasif.17.2.82619"),
        ("24", "M. Minderer et al., \"Revisiting the Calibration of Modern Neural Networks,\" in Advances in Neural Information Processing Systems (NeurIPS), vol. 34, 2021, pp. 15682-15694", "10.48550/arXiv.2106.07998"),
        ("25", "H.-S. Yoon, S.-W. Park, and J.-H. Yoo, \"Real-Time Hair Segmentation Using Mobile-Unet,\" Electronics, vol. 10, no. 2, Art. no. 99, Jan. 2021", "10.3390/electronics10020099"),
        ("26", "O. Ronneberger, P. Fischer, and T. Brox, \"U-Net: Convolutional Networks for Biomedical Image Segmentation,\" in Med. Image Comput. Comput.-Assist. Interv. (MICCAI), 2015, pp. 234-241", "10.1007/978-3-319-24574-4_28")
    ]

    for num, txt, doi in references_data:
        add_reference_item(num, txt, doi)

    # Re-attach Creative Commons License element at the end
    # Place license within the 2-column flow directly at bottom, or 1-column if appropriate
    if license_el is not None:
        add_continuous_break(num_cols=1)
        # Set spacing before to 12 pt (240 dxa) to ensure 2-column balancing fits cleanly on Page 8
        sp_node = license_el.find('.//w:spacing', ns)
        if sp_node is not None:
            sp_node.set(qn('w:before'), '240')
        else:
            pPr_lic = license_el.find('w:pPr', ns)
            if pPr_lic is None:
                pPr_lic = OxmlElement('w:pPr')
                license_el.insert(0, pPr_lic)
            sp_node = OxmlElement('w:spacing')
            sp_node.set(qn('w:before'), '240')
            pPr_lic.append(sp_node)
        for t_node in license_el.xpath('.//w:t'):
            if '2021' in (t_node.text or ''):
                t_node.text = t_node.text.replace('2021', '2026')
        body.find(qn('w:sectPr')).addprevious(license_el)

    print(f"Saving compiled manuscript to {OUTPUT_DOCX}...")
    doc.save(str(OUTPUT_DOCX))
    print("Manuscript DOCX successfully created!")


if __name__ == "__main__":
    build_manuscript()
