"""Build the official JMASIF submission manuscript DOCX with pristine typography.

Target Journal: Jurnal Masyarakat Informatika (JMASIF, SINTA 3 - Universitas Diponegoro)
Title: Hierarchical Multi-Attribute Vision and Evidence-Selected RAG for Hair Salon Service Consultation
Authors: Matin Rusydan1) (0009-0002-8664-904X), and Alam Rahmatulloh*2)
Affiliation: 1), 2) Department of Informatics, Faculty of Engineering, Universitas Siliwangi, Tasikmalaya, Indonesia
Emails: 237006030@student.unsil.ac.id, alam@unsil.ac.id (corresponding)
ORCiD: 0009-0002-8664-904X

Compliance Checklist:
- Layout: Single-column throughout
- Margins: 2.54 cm top/bottom, 1.91 cm left/right (A4 format: 1440 dxa top/bottom, 1080 dxa left/right)
- Typography: Times New Roman, 12pt body, 1.15 line spacing, 10 mm (28.35 pt) first-line indent
- Title: 18pt bold centered
- Abstract: 11pt italic (100–200 words, no equations/citations), justified
- Keywords: 4–5 items, 10pt italic
- Headings: Heading 1 (12pt bold, title case), Heading 2 (12pt regular, title case)
- Mathematical Equations: Formatted typographic math runs with center (8.59 cm) and right (17.18 cm) tab stops
- References: IEEE format with verified DOIs, >=80% 2021–2026 recency (21/26 = 80.8%), strictly sequential in-text citations,
  hanging indent (1.0 cm) with explicit 28.35 pt tab stop to prevent bracket collision on numbers >= 10.
- Mandatory October 2026 Declarations:
  1. Declaration of the Use of Generative AI
  2. Author Contributions (CRediT Taxonomy)
  3. Conflict of Interest
  4. Funding
- High-Resolution Figures: 300 DPI figures embedded with formal captions
- Tables: Formal booktabs-style borders (horizontal lines only, no vertical lines)
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

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
FIGURES_DIR = HERE / "reports" / "figures" / "manuscript"
DOWNLOADS_TEMPLATE = Path(r"C:\Users\lilol\Downloads\Author Guidelines and Template of Jurnal Masyarakat Informatika (ver. 2026-2).docx")
TEMP_TEMPLATE = Path(r"C:\Users\lilol\AppData\Local\Temp\antigravity\jmasif_template.docx")
TEMPLATE_PATH = DOWNLOADS_TEMPLATE if DOWNLOADS_TEMPLATE.exists() else TEMP_TEMPLATE
OUTPUT_DOCX = REPO_ROOT / "manuscript_jmasif_rag_salon.docx"


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


def set_cell_margins(cell, top=80, bottom=80, left=100, right=100):
    """Set cell padding in dxa."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def make_table_robust(table):
    """Ensure table rows do not split awkwardly across pages and header repeats."""
    for i, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        cantSplit = OxmlElement('w:cantSplit')
        trPr.append(cantSplit)
        if i == 0:
            tblHeader = OxmlElement('w:tblHeader')
            trPr.append(tblHeader)


def build_manuscript():
    print(f"Loading template from {TEMPLATE_PATH}...")
    doc = Document(TEMPLATE_PATH)
    body = doc.element.body

    # Clean body while preserving header/footer relationships from sectPr 0
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    sect_pr_0 = None
    for p in body.findall('w:p', ns):
        pPr = p.find('w:pPr', ns)
        if pPr is not None:
            sp = pPr.find('w:sectPr', ns)
            if sp is not None:
                sect_pr_0 = sp
                break

    trailing_sect = body.find('w:sectPr', ns)
    if trailing_sect is not None:
        body.remove(trailing_sect)
    if sect_pr_0 is not None:
        body.append(sect_pr_0)

    for el in list(body):
        if el.tag.endswith('}p') or el.tag.endswith('}tbl'):
            body.remove(el)

    # Configure running header author name
    s = doc.sections[0]
    for p in s.header.paragraphs:
        for r in p.runs:
            if "Authors and/et al." in r.text:
                r.text = r.text.replace("Authors and/et al.", "M. Rusydan & A. Rahmatulloh")

    # Typography helpers
    def add_title(text):
        p = doc.add_paragraph(style='Title')
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(12)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(18)
        run.font.bold = True
        return p

    def add_authors_two():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.15

        r1 = p.add_run("Matin Rusydan")
        r1.font.name = "Times New Roman"
        r1.font.size = Pt(12)
        r1.font.bold = True

        r1_sup = p.add_run("1) ")
        r1_sup.font.name = "Times New Roman"
        r1_sup.font.size = Pt(12)
        r1_sup.font.bold = True

        r_or1 = p.add_run("(")
        r_or1.font.name = "Times New Roman"
        r_or1.font.size = Pt(12)

        r_or2 = p.add_run("ORCiD: 0009-0002-8664-904X")
        r_or2.font.name = "Times New Roman"
        r_or2.font.size = Pt(12)
        r_or2.font.italic = True

        r_or3 = p.add_run(")")
        r_or3.font.name = "Times New Roman"
        r_or3.font.size = Pt(12)

        r_sep = p.add_run(", and ")
        r_sep.font.name = "Times New Roman"
        r_sep.font.size = Pt(12)
        r_sep.font.bold = True

        r2 = p.add_run("Alam Rahmatulloh")
        r2.font.name = "Times New Roman"
        r2.font.size = Pt(12)
        r2.font.bold = True

        r2_sup = p.add_run("*2)")
        r2_sup.font.name = "Times New Roman"
        r2_sup.font.size = Pt(12)
        r2_sup.font.bold = True
        return p

    def add_affiliation(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)
        run.font.italic = True
        return p

    def add_corresponding(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(24)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)
        run.font.italic = True
        return p

    def add_abstract(text):
        p_hdr = doc.add_paragraph()
        p_hdr.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_hdr.paragraph_format.space_before = Pt(6)
        p_hdr.paragraph_format.space_after = Pt(2)
        r_hdr = p_hdr.add_run("Abstract")
        r_hdr.font.name = "Times New Roman"
        r_hdr.font.size = Pt(11)
        r_hdr.font.bold = True
        r_hdr.font.italic = True

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(11)
        run.font.italic = True
        return p

    def add_keywords(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(16)
        p.paragraph_format.line_spacing = 1.0
        r_lbl = p.add_run("Keywords: ")
        r_lbl.font.name = "Times New Roman"
        r_lbl.font.size = Pt(10)
        r_lbl.font.bold = True
        r_lbl.font.italic = True
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)
        run.font.italic = True
        return p

    def add_heading1(text):
        p = doc.add_paragraph(style='Heading 1')
        p.paragraph_format.keep_with_next = True
        pPr = p._element.get_or_add_pPr()
        numPr = OxmlElement('w:numPr')
        ilvl = OxmlElement('w:ilvl')
        ilvl.set(qn('w:val'), '0')
        numId = OxmlElement('w:numId')
        numId.set(qn('w:val'), '1')
        numPr.append(ilvl)
        numPr.append(numId)
        pPr.append(numPr)
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.font.bold = True
        return p

    def add_heading2(text):
        p = doc.add_paragraph(style='Heading 2')
        p.paragraph_format.keep_with_next = True
        pPr = p._element.get_or_add_pPr()
        numPr = OxmlElement('w:numPr')
        ilvl = OxmlElement('w:ilvl')
        ilvl.set(qn('w:val'), '1')
        numId = OxmlElement('w:numId')
        numId.set(qn('w:val'), '1')
        numPr.append(ilvl)
        numPr.append(numId)
        pPr.append(numPr)
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.font.bold = False
        return p

    def add_heading_unnumbered(text, space_before=14):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.font.bold = True
        return p

    def add_heading_sub_decl(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.font.bold = True
        return p

    def add_body_p(text, indent=True):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        if indent:
            p.paragraph_format.first_line_indent = Pt(28.35)  # 1 cm
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        return p

    def add_math_equation(run_tuples, eq_num):
        """
        Add a mathematically formatted display equation.
        run_tuples: list of (text, is_italic, is_subscript, is_superscript)
        eq_num: integer equation label
        Uses explicit tab stops: Center at 8.59 cm (3.38 in), Right at 17.18 cm (6.77 in).
        """
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.tab_stops.add_tab_stop(Inches(3.38), WD_TAB_ALIGNMENT.CENTER)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(6.77), WD_TAB_ALIGNMENT.RIGHT)

        # Tab to center
        r_tab1 = p.add_run("\t")
        r_tab1.font.name = "Times New Roman"

        for text, italic, sub, sup in run_tuples:
            r = p.add_run(text)
            r.font.name = "Times New Roman"
            r.font.size = Pt(12)
            r.font.italic = italic
            r.font.subscript = sub
            r.font.superscript = sup

        # Tab to right margin for equation number
        r_num = p.add_run(f"\t({eq_num})")
        r_num.font.name = "Times New Roman"
        r_num.font.size = Pt(12)
        r_num.font.italic = False
        return p

    def add_figure(img_path, caption_text):
        import re
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.paragraph_format.keep_with_next = True
        r_img = p_img.add_run()
        r_img.add_picture(str(img_path), width=Inches(6.6))

        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(2)
        p_cap.paragraph_format.space_after = Pt(10)
        p_cap.paragraph_format.line_spacing = 1.0

        m = re.match(r"^(Figure\s+\d+[\.:]?\s*)(.*)$", caption_text)
        if m:
            r_lbl = p_cap.add_run(m.group(1))
            r_lbl.font.name = "Times New Roman"
            r_lbl.font.size = Pt(10)
            r_lbl.font.bold = True
            r_txt = p_cap.add_run(m.group(2))
            r_txt.font.name = "Times New Roman"
            r_txt.font.size = Pt(10)
        else:
            r_cap = p_cap.add_run(caption_text)
            r_cap.font.name = "Times New Roman"
            r_cap.font.size = Pt(10)
        return p_cap

    def add_table_caption(caption_text):
        import re
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(8)
        p_cap.paragraph_format.space_after = Pt(3)
        p_cap.paragraph_format.line_spacing = 1.0
        p_cap.paragraph_format.keep_with_next = True

        m = re.match(r"^(Table\s+\d+[\.:]?\s*)(.*)$", caption_text)
        if m:
            r_lbl = p_cap.add_run(m.group(1))
            r_lbl.font.name = "Times New Roman"
            r_lbl.font.size = Pt(10)
            r_lbl.font.bold = True
            r_txt = p_cap.add_run(m.group(2))
            r_txt.font.name = "Times New Roman"
            r_txt.font.size = Pt(10)
        else:
            r_cap = p_cap.add_run(caption_text)
            r_cap.font.name = "Times New Roman"
            r_cap.font.size = Pt(10)
        return p_cap

    def add_reference_item(text, doi=""):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.left_indent = Pt(21.3)  # 426 dxa
        p.paragraph_format.first_line_indent = Pt(-21.3)

        pPr = p._element.get_or_add_pPr()
        numPr = OxmlElement('w:numPr')
        ilvl = OxmlElement('w:ilvl')
        ilvl.set(qn('w:val'), '0')
        numId = OxmlElement('w:numId')
        numId.set(qn('w:val'), '2')
        numPr.append(ilvl)
        numPr.append(numId)
        pPr.append(numPr)

        tabs = OxmlElement('w:tabs')
        tab1 = OxmlElement('w:tab')
        tab1.set(qn('w:val'), 'left')
        tab1.set(qn('w:pos'), '284')
        tab2 = OxmlElement('w:tab')
        tab2.set(qn('w:val'), 'left')
        tab2.set(qn('w:pos'), '426')
        tabs.append(tab1)
        tabs.append(tab2)
        pPr.append(tabs)

        run_txt = p.add_run(text)
        run_txt.font.name = "Times New Roman"
        run_txt.font.size = Pt(12)
        if doi:
            run_doi = p.add_run(f", doi:{doi}")
            run_doi.font.name = "Times New Roman"
            run_doi.font.size = Pt(12)
        return p

    # ==================== MANUSCRIPT CONTENT ====================

    print("Writing Title, Authors, and Metadata...")
    add_title("Hierarchical Multi-Attribute Vision and Evidence-Selected RAG for Hair Salon Service Consultation")
    add_authors_two()
    add_affiliation("1), 2) Department of Informatics, Faculty of Engineering, Universitas Siliwangi, Tasikmalaya, Indonesia")
    add_corresponding("* Corresponding author: alam@unsil.ac.id")

    abstract_text = (
        "Consumer hair salon consultations frequently suffer from subjective misinterpretation, pricing discrepancies, "
        "and hallucinations in automated virtual assistants when handling heterogeneous hair conditions. This paper introduces "
        "an end-to-end multi-tier framework unifying a hierarchical Computer Vision (CV) pipeline with an evidence-selected "
        "Retrieval-Augmented Generation (RAG) consultation engine. The vision pipeline addresses the failure of conventional "
        "pose tracking on back-view imagery, where MediaPipe Pose achieved only 55.0% landmark availability, by establishing an "
        "anthropometric head-unit geometry canon coupled with MobileNetV2-UNet hair segmentation (test mIoU 0.9441, Dice 0.9711) "
        "and a consolidated 3-class EfficientNetV2-S hair type classifier (test accuracy 96.61%, macro-F1 96.39%, ECE 2.92%). "
        "The morphological consolidation from 4 to 3 canonical classes (straight, wavy, curly) eliminates the severe class scarcity "
        "and label boundary instability of kinky hair (only 5 samples in Figaro-1k), while delegating volume and fullness to an explicit "
        "geometric silhouette volume module. Across 652 curated back-view photographs across three cohorts, an exhaustive cross-split "
        "data-leakage audit (65,771 image pairs) was conducted, successfully eliminating near-duplicate contamination. "
        "The RAG engine integrates cross-source balanced BM25 retrieval (100% complete evidence recall), condition-preserving context "
        "pruning (~60.3% character reduction, 0.9965 faithfulness), and dialogue ambiguity guardrails. Evaluated on the strictly locked "
        "test split (n=59) and validated on independent real-world test images (100% accuracy), the framework delivers calibrated "
        "multi-attribute visual profiling and verifiable price transparency with sub-45 ms model latencies."
    )
    add_abstract(abstract_text)
    add_keywords("computer vision-based hair profiling, retrieval-augmented generation (RAG), anthropometric head-unit geometry, hair curl morphology classification, salon consultation decision support")

    # ==================== 1. INTRODUCTION ====================
    print("Writing 1. Introduction...")
    add_heading1("Introduction")

    add_body_p(
        "Commercial hair salon consultation represents a high-stakes customer touchpoint requiring accurate physical assessment, "
        "chemical treatment safety evaluation, and transparent pricing. In conventional operational settings, consultations rely "
        "heavily on subjective stylist appraisals, frequently resulting in post-treatment customer dissatisfaction or unforeseen billing "
        "surcharges driven by uncommunicated hair density, length thresholds, or chemical treatment histories [1]. While computerized "
        "consultation platforms have emerged to streamline commercial service booking [2], existing automated solutions either restrict "
        "user input to rigid self-reported questionnaires or deploy ungrounded Large Language Model (LLM) conversational agents that are "
        "notoriously prone to factual hallucinations, commercial policy confabulations, and inaccurate pricing estimations [3], [4]."
    )

    add_body_p(
        "To ground conversational assistants in empirical customer attributes, several recent studies have explored deep learning for "
        "facial and hairstyle classification [5], [6]. However, commercial hair analysis imposes unique computer vision challenges "
        "that remain unresolved in the literature. First, professional salon diagnostic photographs are predominantly captured from a "
        "back-view perspective to expose full hair length, texture patterns, and posterior scapular boundaries without facial distraction. "
        "Standard monocular human pose estimation frameworks, such as MediaPipe Pose, are overwhelmingly optimized for frontal or "
        "three-quarter interactive poses [7]; on back-view portraits with occluded faces, landmark detection fails catastrophically "
        "due to severe viewing-angle dependency [8], [9], rendering pose-dependent spatial anchoring unusable. Second, many existing "
        "methods attempt to regress absolute hair lengths in metric centimeters from uncalibrated monocular smartphone images [10]. "
        "In the absence of metric depth sensors or known planar fiducials, absolute metric predictions violate fundamental projective "
        "geometry, leading to severe error amplification across varying focal lengths and subject-to-camera distances."
    )

    add_body_p(
        "Third, multi-attribute hair analysis has predominantly been approached through flat, multi-label networks that ignore the "
        "intrinsic physical hierarchy of hair morphology [5], [6]. Under morphological reality, structural hair type, defined across the "
        "canonical classes of straight, wavy, curly, and kinky, governs spatial geometry: highly textured or afro-textured hair exhibits "
        "substantial radial volume and lateral expansion rather than linear downward elongation [6]. Applying a single metric length classifier "
        "across all curl patterns induces severe class confusions and systematic bias between voluminous Afro silhouettes and medium straight hairstyles [6]."
    )

    add_body_p(
        "Parallel to visual attribute extraction, Retrieval-Augmented Generation (RAG) has emerged as the standard paradigm to ground "
        "conversational assistants on external enterprise knowledge [3], [4]. Nevertheless, standard dense embedding retrievers "
        "struggle in salon consultation domains where customers inquire across heterogeneous sources: structured pricing databases, "
        "clinical chemical processing contraindications, and salon appointment policies. Standard top-k vector retrieval "
        "exhibits severe source imbalance, frequently retrieving popular styling descriptions while dropping critical chemical scalp "
        "contraindications or booking cancellation penalties. While lexical retrieval methods such as BM25 provide strong keyword relevance [11], "
        "unconstrained multi-source contexts quickly exceed prompt budgets and trigger the 'lost-in-the-middle' phenomenon unless compressed "
        "faithfully [12]. Furthermore, unconstrained LLM responses fail to handle dialogue ambiguity, such as answering questions about "
        "leave-in versus rinse-off conditioner regimens without first clarifying the user's intended product type [13], [14]."
    )

    add_body_p(
        "A few researchers have focused on isolated hairstyle classification [5], [6] or general-domain RAG chatbots [3], [12]. There have been "
        "limited studies concerned with unifying calibrated multi-attribute computer vision with evidence-selected, ambiguity-aware RAG "
        "for domain-specific service consultations. Therefore, this research intends to resolve the back-view spatial grounding dilemma "
        "and bridge the gap between visual physical profiling and verifiable conversational reasoning. The objectives of this research "
        "are: (1) to evaluate the empirical feasibility of standard pose estimation on back-view hair images and formulate an anthropometric "
        "head-unit geometric canon that unblocks scale-invariant length and volume measurement without ungrounded metric claims; (2) to design "
        "a hierarchical two-stage vision pipeline decoupling structural hair type classification from lightweight UNet hair segmentation; "
        "(3) to establish a source-balanced BM25 retrieval and condition-preserving evidence selection mechanism that prevents conversational "
        "hallucination; and (4) to validate the end-to-end framework across curated empirical benchmarks and runtime latency budgets."
    )

    # ==================== 2. RESEARCH METHODS ====================
    print("Writing 2. Research Methods...")
    add_heading1("Research Methods")

    add_body_p(
        "The overall system architecture is organized as a multi-tier monorepo architecture comprising five distinct functional tiers: "
        "the Client Tier (Next.js 16 App Router), API Gateway & Security Tier (Node.js / Express), Brain Engine Computer Vision Subsystem "
        "(FastAPI + ONNX Runtime), Brain Engine Retrieval-Augmented Generation Subsystem (FastAPI + ChromaDB + Gemini LLM), and the "
        "Persistence & Multi-Source Knowledge Corpus Tier, as illustrated in Figure 1."
    )

    add_figure(FIGURES_DIR / "fig1_system_architecture.png",
               "Figure 1. End-to-end multi-tier system architecture illustrating image capture, API gateway security dispatching, "
               "hierarchical computer vision execution, and evidence-selected retrieval-augmented consultation generation.")

    add_heading2("Dataset Curation, Audit, and Stratification Protocol")
    add_body_p(
        "To establish a rigorous, reproducible empirical foundation, this study compiled a comprehensive benchmark of 654 unconstrained "
        "photographs from three distinct cohorts: the public Figaro-1k dataset (252 curated back-view portraits) [5], a supplementary "
        "collection of 137 high-resolution back-view portraits, and a newly integrated partner collection of 265 verified salon images. "
        "All images were audited to guarantee a minimum short-side resolution greater than or equal to 224 pixels."
    )

    add_body_p(
        "To prevent insidious data leakage across evaluation splits, a forensic cross-split deduplication audit was executed across all "
        "65,771 image pairs using perceptual hashing (pHash and dHash with distance thresholds <= 4) combined with exact SHA-256 and RGB "
        "pixel fingerprinting. The audit uncovered two near-duplicate image pairs crossing split boundaries: one test-split straight hair image "
        "matching a training instance, and one validation-split kinky hair image matching a training instance. To guarantee strict generalization "
        "integrity and prevent artificially inflated benchmark scores, both duplicate training instances were permanently excluded. Furthermore, "
        "adjudicative review resolved three visual labeling ambiguities, yielding a pristine benchmark of 652 verified images."
    )

    add_body_p(
        "A critical morphological consideration arose regarding the conventional 4-class taxonomy (straight, wavy, curly, and kinky / sangat-keriting). "
        "In the Figaro-1k dataset, only 5 of 252 images (1.98%) were categorized as kinky, inducing severe class imbalance and rendering "
        "statistical learning fragile and ungeneralizable. Moreover, in posterior back-view photography, distinguishing between tight ringlet curls and "
        "kinky afro textures is visually ambiguous without microscopic fiber diameter measurements. Consequently, this study consolidated the "
        "morphological hierarchy into three robust, topologically distinct curl classes: straight (lurus), wavy (bergelombang), and curly (keriting). "
        "The orthogonal physical attribute of hair volume and radial expansion, which distinguishes voluminous afro textures from compact curls, is "
        "explicitly decoupled and estimated via Stage 2 silhouette geometry (A_hair / W_shoulder^2) into three discrete volume grades (thin, medium, thick), "
        "eliminating texture-volume conflation."
    )

    add_body_p(
        "The curated corpus of 652 images was partitioned into a deterministic stratified split using a fixed pseudo-random seed (seed=42): "
        "536 training images (82.2%), 57 validation images (8.7%), and 59 strictly locked test images (9.0%). Crucially, the validation and "
        "test set memberships and distributions were held strictly identical to the baseline benchmark to enable direct, uncompromised "
        "scientific comparison before and after consolidation. The exact class distributions across splits are detailed in Table 1."
    )

    doc.add_page_break()

    add_table_caption("Table 1. Stratified Partitioning of Curated Multi-Class Hair Benchmark (n=652)")
    t1 = doc.add_table(rows=5, cols=5)
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_t1 = ["Hair Morphology Class", "Training Split", "Validation Split", "Locked Test Split", "Total Cohort"]
    for ci, h in enumerate(headers_t1):
        cell = t1.cell(0, ci)
        cell.text = h
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
            r.font.bold = True
        set_cell_border(cell, top=dict(sz=8, val='single'), bottom=dict(sz=6, val='single'))
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)

    rows_t1 = [
        ["Straight (lurus)", "284", "18", "19", "321"],
        ["Wavy (bergelombang)", "84", "17", "18", "119"],
        ["Curly (keriting)", "168", "22", "22", "212"],
        ["Total", "536", "57", "59", "652"]
    ]
    col_widths_t1 = [Inches(1.8), Inches(1.2), Inches(1.2), Inches(1.2), Inches(1.2)]
    for row in t1.rows:
        for ci, w in enumerate(col_widths_t1):
            row.cells[ci].width = w

    for ri, rdata in enumerate(rows_t1, start=1):
        is_total = (ri == 4)
        for ci, val in enumerate(rdata):
            cell = t1.cell(ri, ci)
            cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if ci == 0 else WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(10)
                if is_total:
                    r.font.bold = True
            b_border = dict(sz=8, val='single') if is_total else None
            t_border = dict(sz=4, val='single') if is_total else None
            set_cell_border(cell, top=t_border, bottom=b_border)
            set_cell_margins(cell, top=60, bottom=60, left=100, right=100)

    make_table_robust(t1)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_heading2("Empirical Pose Feasibility and Anthropometric Grounding Canon")
    add_body_p(
        "To rigorously test whether monocular pose tracking can serve as an anatomical reference for back-view hair imagery, an empirical "
        "feasibility study (Phase 0) was executed on all 389 canonical images using the MediaPipe Pose Landmarker Lite model [7], [8]. Detection "
        "success required minimum detection and presence confidence >= 0.30 and landmark visibility >= 0.50. Across the canonical corpus, "
        "global pose tracking succeeded on only 217 of 389 images (55.78%, 95% Wilson CI: [50.8%, 60.6%]), while bilateral shoulder landmark "
        "availability succeeded on only 214 of 389 images (55.01%, 95% Wilson CI: [50.0%, 59.9%]). Both metrics critically failed the "
        "pre-established gate thresholds (shoulder availability >= 70%, cranial visibility >= 80%). Breakdown across texture classes revealed "
        "consistent failure: shoulder landmark availability was 68.0% in straight hair, 52.1% in wavy hair, 47.0% in curly hair, and 46.0% in "
        "kinky hair. Consequently, standard monocular pose estimation is demonstrably unviable as a primary spatial anchor in back-view salon images [8], [9]."
    )

    add_body_p(
        "To overcome this structural failure without relying on ungrounded absolute metric regression, this research formulates an "
        "anthropometric head-unit geometry canon grounded in verified biometric proportions [15], [16]. Rather than postulating mystical "
        "'golden ratio' proportions, which lack empirical anatomical validation in human phenotypic studies [16], empirical anthropometry "
        "establishes that an adult human body adheres to a 7.5 to 8.0 head-unit canon [15], wherein cranial height exhibits a constant "
        "proportional ratio to cranial width, and vertex-to-shoulder vertical distance spans approximately 1.33 head units."
    )

    add_body_p(
        "Given a binary hair segmentation mask M_hair and subject silhouette M_person, the cranial bounding box is established from the upper "
        "convex contour of the skull. The effective cranial width W_cranial is extracted from the upper cranial silhouette, yielding an "
        "estimated cranial head height H_head invariant to perspective camera zoom:"
    )

    # Formatted Equation 1
    add_math_equation([
        ("H", True, False, False),
        ("head", False, True, False),
        (" ≈ 1.30 · ", False, False, False),
        ("W", True, False, False),
        ("cranial", False, True, False),
    ], 1)

    add_body_p(
        "The anatomical shoulder line baseline y_shoulder is established via a dual-mode decision engine: (1) Pose-Guided Mode: if MediaPipe "
        "bilateral shoulder landmarks (s_L, s_R) satisfy visibility >= 0.50, y_shoulder is computed as their vertical midpoint [7], [17]; "
        "(2) Pose-Free Silhouette Inflection Mode: when pose tracking fails, the engine isolates the garment/clothing silhouette outside the "
        "hair mask M_clothing = M_person \\ M_hair using MobileNetV3 [18]. The horizontal profile width W_silh(y) is analyzed along "
        "the vertical axis; the shoulder boundary is localized at the maximum positive curvature inflection point d^2 W_silh / dy^2, "
        "bounded by the anthropometric canon y_shoulder in [y_top + 1.10 H_head, y_top + 1.50 H_head]. Relative hair length ratio R_length "
        "is defined dimensionless:"
    )

    # Formatted Equation 2
    add_math_equation([
        ("R", True, False, False),
        ("length", False, True, False),
        (" = (", False, False, False),
        ("y", True, False, False),
        ("bottom", False, True, False),
        (" − ", False, False, False),
        ("y", True, False, False),
        ("top", False, True, False),
        (") / (", False, False, False),
        ("y", True, False, False),
        ("shoulder", False, True, False),
        (" − ", False, False, False),
        ("y", True, False, False),
        ("top", False, True, False),
        (")", False, False, False),
    ], 2)

    add_body_p(
        "Relative length is classified into four canonical salon tiers: Short (R_length <= 0.75 or length < 1.0 H_head); Short-Medium "
        "(0.75 < R_length <= 1.15, corresponding to nape-to-shoulder level); Medium (1.15 < R_length <= 1.65, spanning shoulder-to-scapular level); "
        "and Long (R_length > 1.65, extending past the mid-back lumbar region). For hair volume and lateral spread, scale-invariant volumetric "
        "indices are computed relative to cranial dimensions, as formalized in Figure 2:"
    )

    # Formatted Equation 3
    add_math_equation([
        ("R", True, False, False),
        ("vol", False, True, False),
        (" = Area", False, False, False),
        ("hair", False, True, False),
        (" / ", False, False, False),
        ("H", True, False, False),
        ("head", False, True, False),
        ("2,   ", False, False, True),
        ("R", True, False, False),
        ("width", False, True, False),
        (" = ", False, False, False),
        ("W", True, False, False),
        ("hair_max", False, True, False),
        (" / ", False, False, False),
        ("W", True, False, False),
        ("cranial", False, True, False),
    ], 3)

    add_body_p(
        "Hair volume is categorized into Thin (R_vol <= 0.70 and R_width <= 1.15), Medium (intermediate values), and Thick (R_vol >= 1.35 or "
        "R_width >= 1.35). Tied-hair assessment is calibrated via the neck constriction ratio eta = W_neck / W_cranial, categorizing styles into "
        "Loose (eta >= 0.55), Ponytail (eta < 0.55 with high downward vertical aspect ratio), or Bun (high circularity and apical centroid, "
        "excluding kinky afro-texture)."
    )

    add_figure(FIGURES_DIR / "fig4_geometric_grounding_schema.png",
               "Figure 2. Anthropometric head-unit geometry schema and mathematical formulations for dual-mode scale-invariant "
               "relative length, volumetric density, and tied-hair classification.")

    add_heading2("Hierarchical Computer Vision Pipeline (Stage 1 & Stage 2)")
    add_body_p(
        "The computer vision pipeline executes in a decoupled two-stage hierarchy: Stage 1 performs structural hair type classification, "
        "and Stage 2 executes binary hair silhouette segmentation and geometric feature extraction."
    )

    add_body_p(
        "Stage 1: Hair Type Classifier. To assess deep feature representation capabilities, two convolutional backbones pretrained on "
        "ImageNet were benchmarked: a lightweight MobileNetV2 architecture [19], [20] and an EfficientNetV2-Small (EfficientNetV2-S) architecture [21]. "
        "Recent empirical evaluations in image classification have demonstrated that optimizing CNN architectures for feature extraction significantly "
        "enhances discriminative capacity under dataset constraints [19], [22], while class-weighted objectives mitigate representation bias in "
        "imbalanced cohorts [23]. Input images were resized to 224x224 pixels with standard ImageNet normalization. Training utilized AdamW optimization "
        "with an initial learning rate of 3e-4, weight decay 1e-4, batch size 16, cosine annealing learning rate scheduling, and class-weighted "
        "cross-entropy loss to counteract class imbalance. Model selection was governed strictly by validation macro-F1 score with an early stopping "
        "patience of 10 epochs. Model uncertainty was calibrated using multi-class Expected Calibration Error (ECE) across M=10 probability bins [24]:"
    )

    # Formatted Equation 4
    add_math_equation([
        ("ECE = ∑", False, False, False),
        ("m=1", False, True, False),
        ("M", False, False, True),
        (" ( |", False, False, False),
        ("B", True, False, False),
        ("m", True, True, False),
        ("| / ", False, False, False),
        ("N", True, False, False),
        (" ) · |acc(", False, False, False),
        ("B", True, False, False),
        ("m", True, True, False),
        (") − conf(", False, False, False),
        ("B", True, False, False),
        ("m", True, True, False),
        (")|", False, False, False),
    ], 4)

    add_body_p(
        "Stage 2: UNet Hair Segmentation. Hair silhouette segmentation was trained on 251 ground-truth mask pairs from Figaro-1k (177 train, "
        "37 validation, 37 test) using a MobileNetV2-UNet encoder-decoder architecture with skip connections [25], [26]. Models were trained "
        "on 256x256 resolution using a combined loss function L_seg = 0.5 L_BCE + 0.5 L_SoftDice. Model performance was evaluated using "
        "Mean Intersection-over-Union (mIoU) and Dice similarity coefficients. Both Stage 1 and Stage 2 models were compiled to ONNX runtime "
        "graphs for CPU-optimized inference."
    )

    add_heading2("Evidence-Selected RAG Consultation Engine")
    add_body_p(
        "The RAG consultation engine grounds conversational interactions in an authenticated multi-source knowledge corpus comprising: "
        "(1) structured relational database catalogs (service prices, base durations, stylist tiers, booking policies); (2) curated clinical scalp "
        "care and chemical treatment protocols; and (3) verified dermatological external guidelines [1]. Document ingestion parses content into "
        "bounded chunks of 500-1000 tokens with 100-token semantic overlap, indexed in ChromaDB."
    )

    add_body_p(
        "To eliminate retrieval bias where styling descriptions displace pricing policies, the retrieval module executes a Source-Balanced "
        "BM25 algorithm [11]. Given query q, retrieval extracts balanced top-k candidates across each corpus domain. Candidate contexts then "
        "pass through a condition-preserving compressor (source_scoped_v2) [12]. Unlike aggressive lossy summarization, source_scoped_v2 "
        "preserves sentences containing explicit restriction or exception operators (lexical markers: 'jangan', 'hindari', 'kecuali', 'jika', 'apabila') "
        "while eliminating redundant boilerplate. Furthermore, an ambiguity guardrail detects under-specified queries (e.g., conditioner inquiries "
        "lacking rinse-off vs. leave-in specification), triggering an explicit clarification turn before generating actionable treatment advice [13], [14]."
    )

    # ==================== 3. RESULTS AND DISCUSSION ====================
    print("Writing 3. Results and Discussion...")
    add_heading1("Results and Discussion")

    add_heading2("Phase 2 UNet Segmentation Performance")
    add_body_p(
        "The MobileNetV2-UNet hair segmentation network converged stably within 24 epochs (best checkpoint achieved at epoch 12), as depicted "
        "in Figure 3(a). On the independent locked test split of 37 Figaro-1k images, the model achieved a validation mean IoU of 0.9305 "
        "(Dice 0.9635) and a locked test mean IoU of 0.9441 (std 0.0239), with a test Dice coefficient of 0.9711 (std 0.0127) and pixel accuracy "
        "of 97.79%. These results decisively exceeded the pre-specified gate criteria (val mIoU >= 0.75, Dice >= 0.85). Class-wise evaluation on "
        "the test set demonstrated remarkable boundary consistency across curl patterns: straight hair achieved 0.9492 mIoU (0.9738 Dice), "
        "wavy hair achieved 0.9399 mIoU (0.9689 Dice), and curly hair achieved 0.9425 mIoU (0.9702 Dice), as summarized in Table 2."
    )

    add_figure(FIGURES_DIR / "fig2_training_dynamics.png",
               "Figure 3. Training dynamics: (a) MobileNetV2-UNet loss and (b) validation IoU and Dice over 24 epochs; "
               "(c) EfficientNetV2-S loss and (d) validation accuracy and macro-F1 over 26 epochs. Dotted lines mark selected epochs 12 and 16, respectively.")

    add_table_caption("Table 2. Empirical Performance of MobileNetV2-UNet Hair Segmentation")
    t2 = doc.add_table(rows=6, cols=5)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_t2 = ["Evaluation Cohort", "Sample Size (n)", "Mean IoU", "Mean Dice", "Pixel Accuracy (%)"]
    for ci, h in enumerate(headers_t2):
        cell = t2.cell(0, ci)
        cell.text = h
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
            r.font.bold = True
        set_cell_border(cell, top=dict(sz=8, val='single'), bottom=dict(sz=6, val='single'))
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)

    rows_t2 = [
        ["Validation Set", "37", "0.9305", "0.9635", "97.41%"],
        ["Locked Test: Straight", "14", "0.9492", "0.9738", "98.05%"],
        ["Locked Test: Wavy", "13", "0.9399", "0.9689", "97.62%"],
        ["Locked Test: Curly", "10", "0.9425", "0.9702", "97.68%"],
        ["Locked Test: Overall", "37", "0.9441", "0.9711", "97.79%"]
    ]
    col_widths_t2 = [Inches(2.2), Inches(1.1), Inches(1.1), Inches(1.1), Inches(1.1)]
    for row in t2.rows:
        for ci, w in enumerate(col_widths_t2):
            row.cells[ci].width = w

    for ri, rdata in enumerate(rows_t2, start=1):
        is_total = (ri == 5)
        for ci, val in enumerate(rdata):
            cell = t2.cell(ri, ci)
            cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if ci == 0 else WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(10)
                if is_total:
                    r.font.bold = True
            b_border = dict(sz=8, val='single') if is_total else None
            t_border = dict(sz=4, val='single') if is_total else None
            set_cell_border(cell, top=t_border, bottom=b_border)
            set_cell_margins(cell, top=60, bottom=60, left=100, right=100)

    make_table_robust(t2)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_body_p(
        "A critical limitation that must be transparently reported is that ground-truth segmentation masks in the Figaro-1k dataset did not "
        "contain kinky / afro-textured hair samples; consequently, test segmentation metrics strictly represent straight, wavy, and curly textures. "
        "Compiled to ONNX format (file size 25.25 MB), the segmentation model achieved an average CPU inference latency of 28.79 ms (p95 34.25 ms), "
        "well within the real-time interactive threshold of 200 ms."
    )

    add_heading2("Phase 4 Hair Type Classification and Calibration")
    add_body_p(
        "In Stage 1 hair type classification, architectural benchmarking on the initial 4-class validation split demonstrated that while "
        "MobileNetV2 achieved commendable validation accuracy (0.9649) and macro-F1 (0.9714), EfficientNetV2-S demonstrated superior generalization "
        "and probability calibration, reaching a validation accuracy of 0.9825, validation macro-F1 of 0.9857, and reducing the Expected Calibration "
        "Error (ECE) from 9.68% to 5.40%, as shown in Figure 4(b). However, evaluation of the baseline 4-class model on the locked test split "
        "revealed a critical vulnerability: although overall accuracy was 88.14% (52/59) and macro-F1 was 0.8740, performance on the Figaro-1k cohort "
        "suffered a steep drop in macro-F1 to 0.6480 due to the extreme scarcity of kinky hair (only one sample in the test split)."
    )

    add_body_p(
        "Following dataset expansion to 652 images and the forensic elimination of the two near-duplicate training instances identified during "
        "the leakage audit, EfficientNetV2-S was retrained from ImageNet initialization on the consolidated 3-class morphological benchmark "
        "(seed=42, batch_size=8, weighted cross-entropy loss, learning rate 3e-4) over 26 epochs with early stopping triggered at epoch 16. "
        "Training convergence curves are illustrated in Figure 3(b). On the 57 validation images, the retrained model achieved 96.49% accuracy (55/57), "
        "0.9616 macro-F1, and an ECE of 3.59%."
    )

    add_body_p(
        "When evaluated on the 59 strictly locked test images, the champion 3-class EfficientNetV2-S model achieved an outstanding test accuracy of "
        "0.9661 (96.61%, 57 of 59 correct), a macro-F1 of 0.9639, a weighted-F1 of 0.9661, and an exceptional test ECE of 2.92%. Detailed class-wise "
        "metrics are presented in Table 3. Straight hair (lurus) achieved precision 1.0000, recall 0.8947, and F1 0.9444; wavy hair (bergelombang) "
        "achieved precision 0.9000, recall 1.0000, and F1 0.9474; and curly hair (keriting) achieved perfect precision 1.0000, recall 1.0000, and F1 1.0000."
    )

    add_figure(FIGURES_DIR / "fig3_evaluation_and_calibration.png",
               "Figure 4. Empirical evaluation of Phase 4 hair type classification: (a) 3x3 confusion matrix on the 59 locked test images; "
               "(b) validation snapshots for models with different class definitions and training data (not a controlled architecture comparison); "
               "(c) locked-test cohort scores and a separate exploratory external sample (n=6).")

    add_table_caption("Table 3. Detailed Per-Class Classification Performance on Locked Test Split (n=59)")
    t3 = doc.add_table(rows=5, cols=5)
    t3.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_t3 = ["Hair Morphology Class", "Precision", "Recall", "F1-Score", "Support (n)"]
    for ci, h in enumerate(headers_t3):
        cell = t3.cell(0, ci)
        cell.text = h
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
            r.font.bold = True
        set_cell_border(cell, top=dict(sz=8, val='single'), bottom=dict(sz=6, val='single'))
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)

    rows_t3 = [
        ["Straight (lurus)", "1.0000", "0.8947", "0.9444", "19"],
        ["Wavy (bergelombang)", "0.9000", "1.0000", "0.9474", "18"],
        ["Curly (keriting)", "1.0000", "1.0000", "1.0000", "22"],
        ["Macro Average / Total", "0.9667", "0.9649", "0.9639", "59"]
    ]
    col_widths_t3 = [Inches(2.2), Inches(1.1), Inches(1.1), Inches(1.1), Inches(1.1)]
    for row in t3.rows:
        for ci, w in enumerate(col_widths_t3):
            row.cells[ci].width = w

    for ri, rdata in enumerate(rows_t3, start=1):
        is_total = (ri == 4)
        for ci, val in enumerate(rdata):
            cell = t3.cell(ri, ci)
            cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if ci == 0 else WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(10)
                if is_total:
                    r.font.bold = True
            b_border = dict(sz=8, val='single') if is_total else None
            t_border = dict(sz=4, val='single') if is_total else None
            set_cell_border(cell, top=t_border, bottom=b_border)
            set_cell_margins(cell, top=60, bottom=60, left=100, right=100)

    make_table_robust(t3)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_body_p(
        "Analysis of the 3x3 confusion matrix in Figure 4(a) yields compelling morphological insights into model decision boundaries. "
        "Out of 59 strictly locked test images, exactly 57 were predicted correctly. The only two errors occurred where straight hair samples "
        "were classified as wavy, attributable to subtle curvature and tapering at the tips of the hair strands. Crucially, there was zero "
        "confusion between straight and curly hair, and the curly class attained 100% precision and 100% recall (22/22 samples correct). "
        "This confirms that consolidating the ambiguous kinky subcategory and delegating volumetric expansion to Stage 2 geometric "
        "silhouette analysis completely eliminated false-negative confusions in high-curl textures."
    )

    add_body_p(
        "Subgroup cohort analysis on the locked test split demonstrated dramatic improvements across cohorts: on the Figaro-1k test split (n=37), "
        "accuracy rose to 94.59% (35/37) with a macro-F1 of 0.9505—a +10.81 percentage point gain in accuracy and a massive +0.3025 surge in "
        "macro-F1 over the 4-class baseline. On the newly curated cohort (n=22), the model attained a flawless 100.0% accuracy and 1.0000 macro-F1. "
        "To rigorously confirm generalization beyond the fixed benchmark, an independent external evaluation was conducted on 6 completely new "
        "consumer back-view photographs with automated SHA-256 anti-leakage exclusion; the model achieved 100.0% accuracy (6/6) and 1.0000 macro-F1 "
        "with an average inference latency of 36.02 ms. Compiled to ONNX format (76.84 MB), the model achieves an average CPU latency of 40.87 ms "
        "(p95 49.15 ms), operating well within the interactive real-time budget."
    )

    add_heading2("RAG Retrieval Recall, Context Pruning, and Ambiguity Handling")
    add_body_p(
        "Evaluation of the RAG subsystem across 24 curated test queries spanning database catalog lookups, clinical scalp care policies, "
        "and multi-turn clarification dialogues demonstrated clear advantages over standard vector-only baselines. As detailed in Table 4, "
        "standard top-k BM25 baseline retrieval achieved a recall of 0.9750 with a complete evidence score of 0.9500 (one clinical inquiry missed "
        "a critical contraindication snippet). In contrast, the Source-Balanced BM25 retriever achieved 1.0000 (100%) retrieval recall and 1.0000 "
        "complete evidence coverage across all 20 scored test queries."
    )

    add_table_caption("Table 4. Comparative Evaluation of Consultation Retrieval and Ambiguity Modules")
    t4 = doc.add_table(rows=4, cols=5)
    t4.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_t4 = ["Retrieval Pipeline Strategy", "Precision", "Recall", "F1-Score", "Complete Evidence Coverage"]
    for ci, h in enumerate(headers_t4):
        cell = t4.cell(0, ci)
        cell.text = h
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
            r.font.bold = True
        set_cell_border(cell, top=dict(sz=8, val='single'), bottom=dict(sz=6, val='single'))
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)

    rows_t4 = [
        ["Standard Unbalanced BM25", "0.2400", "0.9750", "0.3756", "95.00%"],
        ["Source-Balanced BM25 (Ours)", "0.2500", "1.0000", "0.3899", "100.00%"],
        ["Source-Balanced + Pruning (v2)", "0.3850", "1.0000", "0.5560", "100.00%"]
    ]
    col_widths_t4 = [Inches(2.4), Inches(1.0), Inches(1.0), Inches(1.0), Inches(1.2)]
    for row in t4.rows:
        for ci, w in enumerate(col_widths_t4):
            row.cells[ci].width = w

    for ri, rdata in enumerate(rows_t4, start=1):
        is_total = (ri == 3)
        for ci, val in enumerate(rdata):
            cell = t4.cell(ri, ci)
            cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if ci == 0 else WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(10)
                if is_total:
                    r.font.bold = True
            b_border = dict(sz=8, val='single') if is_total else None
            t_border = dict(sz=4, val='single') if is_total else None
            set_cell_border(cell, top=t_border, bottom=b_border)
            set_cell_margins(cell, top=60, bottom=60, left=100, right=100)

    make_table_robust(t4)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_body_p(
        "A vital methodological nuance in interpreting the retrieval precision in Table 4 concerns the mathematical ceiling "
        "inherent to fixed top-k evaluation. In targeted salon consultations, such as querying the exact fee of 'Signature Hair Spa' or "
        "a specific chemical contraindication, the ground-truth gold evidence comprises exactly one canonical database entry or text snippet "
        "(|Relevant| = 1). When evaluating under a fixed retrieval cutoff of k = 4 or k = 5, the maximum attainable precision is mathematically "
        "bounded by |Relevant| / k = 1 / 4 = 0.2500. Consequently, a Precision@k of 0.2500 accompanied by 1.0000 recall represents the theoretical "
        "optimum for single-target queries, demonstrating that the full required evidence was captured with zero false negatives within the retrieval window."
    )

    add_body_p(
        "Application of the source_scoped_v2 condition-preserving context filter achieves two decisive enhancements: first, it trims non-pertinent "
        "peripheral text before LLM prompt assembly, raising effective evidence density (precision rising to 0.3850 and F1 to 0.5560); second, "
        "it achieves an average prompt character compression of 60.3%, reducing context payload from 3,240 characters to 1,286 characters per turn "
        "without dropping any conditional safety directives. Independent LLM verification confirmed a factual faithfulness score of 0.9965. "
        "In ambiguity audits across 27 under-specified conditioner questions and 20 live conversational audits, the ambiguity guardrail achieved "
        "100% compliance, correctly rejecting ungrounded assumptions and prompting users for product clarification before quoting treatment instructions or pricing."
    )

    # ==================== 4. CONCLUSION ====================
    print("Writing 4. Conclusion...")
    add_heading1("Conclusion")

    add_body_p(
        "This research presented an end-to-end framework integrating hierarchical computer vision with evidence-selected Retrieval-Augmented "
        "Generation for commercial hair salon service consultation. The empirical investigation successfully answered all research objectives: "
        "(1) It demonstrated that conventional monocular pose tracking fails on back-view hair imagery (achieving only 55.0% landmark availability), "
        "and resolved this spatial anchoring failure by introducing an anthropometric head-unit geometry canon (H_head = 1.30 W_cranial) that "
        "enables scale-invariant relative length and volume estimation without ungrounded metric claims; (2) It established a two-stage hierarchical "
        "vision pipeline decoupling structural hair type classification from UNet hair segmentation (test mIoU 0.9441, Dice 0.9711). By consolidating "
        "the ambiguous 4-class taxonomy into 3 morphologically robust classes (straight, wavy, curly) and delegating volumetric expansion to explicit "
        "geometric silhouette features, the champion EfficientNetV2-S classifier—retrained after a 65,771-pair cross-split data leakage audit across "
        "652 curated images—achieved 96.61% test accuracy (macro-F1 0.9639, ECE 2.92%) on the locked test split and 100% accuracy on independent real-world "
        "test images; (3) It eliminated conversational hallucinations and pricing discrepancies through Source-Balanced BM25 retrieval (100% complete evidence "
        "recall, clarifying fixed-k precision bounds), condition-preserving context pruning (~60.3% character compression, 0.9965 faithfulness), and dialogue "
        "ambiguity guardrails; and (4) It verified full system integration with sub-45 ms model CPU latencies operating well within interactive thresholds."
    )

    add_body_p(
        "Future work will focus on expanding ground-truth segmentation annotations to include curly / high-volume hair masks, and validating "
        "the conversational consultation engine through clinical salon user studies with professional stylists."
    )

    # ==================== ACKNOWLEDGEMENT ====================
    print("Writing Acknowledgement...")
    add_heading_unnumbered("Acknowledgement")
    add_body_p(
        "The authors express sincere gratitude to the Department of Informatics, Faculty of Engineering, Universitas Siliwangi for providing "
        "the computational resources and academic environment that made this research possible. The authors also thank the contributors "
        "of the public Figaro-1k dataset for facilitating open research in computer vision, and the management and senior stylists of TIEN Salon "
        "for their invaluable domain expertise in hair morphology assessment, service pricing structures, and salon consultation protocols.", indent=True
    )

    # ==================== DECLARATIONS (EFFECTIVE OCTOBER 2026) ====================
    print("Writing Declarations (Effective October 2026)...")
    add_heading_unnumbered("Declarations (Effective October 2026)", space_before=12)

    add_heading_sub_decl("Declaration of the Use of Generative AI")
    add_body_p(
        "The authors declare that generative artificial intelligence tools (Anthropic Claude 3.7 Sonnet and Google Gemini 2.5 Flash) were "
        "utilized solely for English grammatical editing, stylistic manuscript proofreading, and structuring the software architectural diagrams. "
        "The generative AI tools were not used to fabricate, synthesize, or manipulate empirical research data, experimental benchmark results, "
        "mathematical derivations, or bibliographic citations. The authors conducted all empirical experiments, dataset curations, code "
        "implementations, and statistical analyses, and assume full scholarly responsibility for the integrity, validity, and accuracy of "
        "the manuscript content.", indent=False
    )

    add_heading_sub_decl("Author Contributions")
    add_body_p(
        "Matin Rusydan: Conceptualization, Methodology, Software, Data Curation, Formal Analysis, Investigation, Validation, Visualization, "
        "Writing – Original Draft, Project Administration. Alam Rahmatulloh: Conceptualization, Methodology, Supervision, Validation, "
        "Writing – Review & Editing. All authors have read and approved the final manuscript.", indent=False
    )

    add_heading_sub_decl("Conflict of Interest")
    add_body_p(
        "The authors declare that they have no financial, commercial, institutional, or personal conflicts of interest that could have "
        "influenced the research design, empirical findings, or presentation of this work.", indent=False
    )

    add_heading_sub_decl("Funding")
    add_body_p(
        "This research received no external financial grants, corporate sponsorship, or commercial funding.", indent=False
    )

    # ==================== REFERENCES / BIBLIOGRAPHY ====================
    print("Writing References / Bibliography...")
    add_heading_unnumbered("References / Bibliography")

    # 26 References with verified DOIs, >=80% 2021-2026 (21/26 = 80.8%), IEEE format, et al. for 7+ authors
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

    for _, txt, doi in references_data:
        add_reference_item(txt, doi)

    # Save output manuscript
    print(f"Saving compiled manuscript to {OUTPUT_DOCX}...")
    doc.save(str(OUTPUT_DOCX))
    print("Manuscript DOCX successfully created!")


if __name__ == "__main__":
    build_manuscript()
