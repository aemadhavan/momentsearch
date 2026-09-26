import collections
import collections.abc
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_slide_layout = prs.slide_layouts[6]

    # Color Palette: Modern Dark Mode
    BG_COLOR = RGBColor(15, 23, 42)       # Slate 900
    CARD_BG = RGBColor(30, 41, 59)        # Slate 800
    ACCENT_CYAN = RGBColor(56, 189, 248)  # Cyan 400
    ACCENT_BLUE = RGBColor(96, 165, 250)  # Blue 400
    TEXT_WHITE = RGBColor(248, 250, 252)  # Slate 50
    TEXT_MUTED = RGBColor(148, 163, 184)  # Slate 400
    BORDER_COLOR = RGBColor(51, 65, 85)   # Slate 700
    ACCENT_GREEN = RGBColor(74, 222, 128) # Green 400
    ACCENT_CORAL = RGBColor(248, 113, 113)# Red/Coral 400

    def set_slide_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_COLOR
        bg.line.color.rgb = BG_COLOR
        return bg

    def add_header(slide, title_text, category="MOMENT SEARCH • ASSIGNMENT 3"):
        # Category / Tracker
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.4))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = ACCENT_CYAN
        
        # Main Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.7), Inches(0.8))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(24)
        p_title.font.bold = True
        p_title.font.color.rgb = TEXT_WHITE

    # -------------------------------------------------------------
    # SLIDE 1: Title Slide
    # -------------------------------------------------------------
    s1 = prs.slides.add_slide(blank_slide_layout)
    set_slide_bg(s1)

    # Decorative banner container
    card1 = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(1.2), Inches(10.9), Inches(5.1))
    card1.fill.solid()
    card1.fill.fore_color.rgb = CARD_BG
    card1.line.color.rgb = BORDER_COLOR

    tb = s1.shapes.add_textbox(Inches(1.8), Inches(1.6), Inches(9.7), Inches(4.3))
    tf = tb.text_frame
    tf.word_wrap = True

    p0 = tf.paragraphs[0]
    p0.text = "FDE MODULE 01 • ASSIGNMENT 03"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = ACCENT_CYAN

    p1 = tf.add_paragraph()
    p1.text = "From Semantic Search to Moment RAG"
    p1.font.size = Pt(34)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    p1.space_before = Pt(10)

    p2 = tf.add_paragraph()
    p2.text = "Precision Multimodal Retrieval & Knowledge Grounding at Scale (ARGUS)"
    p2.font.size = Pt(18)
    p2.font.color.rgb = ACCENT_BLUE
    p2.space_before = Pt(8)

    p3 = tf.add_paragraph()
    p3.text = "\n• Author: Madhavan\n• Codebase: github.com/aemadhavan/momentsearch\n• Live App: momentsearch-api-production.up.railway.app\n• Architecture: FastAPI + Prefect Cloud + Qdrant Hybrid + Postgres + CLIP"
    p3.font.size = Pt(14)
    p3.font.color.rgb = TEXT_MUTED
    p3.space_before = Pt(16)

    # -------------------------------------------------------------
    # SLIDE 2: Video Selection & Technical Rationale
    # -------------------------------------------------------------
    s2 = prs.slides.add_slide(blank_slide_layout)
    set_slide_bg(s2)
    add_header(s2, "Video Selection & Technical Rationale", "TASK OVERVIEW • SOURCE SELECTION")

    # Left Card: Video Metadata
    c_left = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    c_left.fill.solid()
    c_left.fill.fore_color.rgb = CARD_BG
    c_left.line.color.rgb = BORDER_COLOR

    tb_v = s2.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(5.0), Inches(4.7))
    tf_v = tb_v.text_frame
    tf_v.word_wrap = True
    p = tf_v.paragraphs[0]
    p.text = "Selected Video"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN

    p = tf_v.add_paragraph()
    p.text = '3Blue1Brown — "Large Language Models explained briefly"\n• Duration: 8 minutes\n• URL: youtu.be/LPZh9BOjkQs\n• Domain: Machine Learning, Attention, Vector Embeddings'
    p.font.size = Pt(13)
    p.font.color.rgb = TEXT_WHITE
    p.space_before = Pt(8)

    p = tf_v.add_paragraph()
    p.text = "\nDynamic Thematic Moments:\n1. Words to High-Dimensional Vectors\n2. Context & Attention Matrices\n3. Feed-Forward Neural Transformations\n4. Softmax & Next-Token Sampling"
    p.font.size = Pt(13)
    p.font.color.rgb = TEXT_MUTED
    p.space_before = Pt(12)

    # Right Card: Why This Video?
    c_right = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    c_right.fill.solid()
    c_right.fill.fore_color.rgb = CARD_BG
    c_right.line.color.rgb = BORDER_COLOR

    tb_r = s2.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.1), Inches(4.7))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True
    p = tf_r.paragraphs[0]
    p.text = "Why Chosen for Moment RAG?"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN

    reasons = [
        ("High Visual-Semantic Coupling", "The spoken transcript frequently refers to on-screen animations ('this matrix here', 'these arrows'). Audio alone is incomplete without visual keyframes."),
        ("Distinct Conceptual Shifts", "Clear topic boundaries allow testing whether the system captures full cognitive units or chops sentences in half."),
        ("Precision Grounding Benchmark", "A perfect benchmark to contrast fixed-window text chunking against time-synchronized multimodal moments.")
    ]
    for title, desc in reasons:
        p = tf_r.add_paragraph()
        p.text = f"• {title}"
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p.space_before = Pt(10)
        p_sub = tf_r.add_paragraph()
        p_sub.text = f"  {desc}"
        p_sub.font.size = Pt(12)
        p_sub.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------
    # SLIDE 3: Architecture Understanding of Moment RAG
    # -------------------------------------------------------------
    s3 = prs.slides.add_slide(blank_slide_layout)
    set_slide_bg(s3)
    add_header(s3, "Architecture Understanding: The Moment RAG Engine", "SYSTEM DESIGN • MULTIMODAL PIPELINE")

    boxes = [
        ("1. Async Worker Queue", "Prefect Cloud orchestrates heavy pipelines (FFmpeg frame extraction, CLIP inference, PDF rendering) fully decoupled from the low-latency API (202 Accepted).", Inches(0.8)),
        ("2. Hybrid Vector Index", "Qdrant stores dense text embeddings (BGE-small / OpenAI) + sparse BM25 vectors + visual CLIP frame embeddings with rich metadata payloads.", Inches(4.8)),
        ("3. Relational State & Locators", "Postgres tracks documents, spaces, and ingest stages. Every chunk has an immutable locator contract: {start_ms, end_ms}, {page}, or {slide}.", Inches(8.8)),
    ]
    for title, desc, left in boxes:
        c = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(1.6), Inches(3.7), Inches(3.2))
        c.fill.solid()
        c.fill.fore_color.rgb = CARD_BG
        c.line.color.rgb = BORDER_COLOR

        t = s3.shapes.add_textbox(left + Inches(0.2), Inches(1.8), Inches(3.3), Inches(2.8))
        tf_b = t.text_frame
        tf_b.word_wrap = True
        p = tf_b.paragraphs[0]
        p.text = title
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN
        p2 = tf_b.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(13)
        p2.font.color.rgb = TEXT_MUTED
        p2.space_before = Pt(10)

    # Bottom summary card
    c_bot = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.1), Inches(11.7), Inches(1.7))
    c_bot.fill.solid()
    c_bot.fill.fore_color.rgb = CARD_BG
    c_bot.line.color.rgb = BORDER_COLOR
    t_bot = s3.shapes.add_textbox(Inches(1.1), Inches(5.2), Inches(11.1), Inches(1.5))
    tf_bot = t_bot.text_frame
    tf_bot.word_wrap = True
    p = tf_bot.paragraphs[0]
    p.text = "Key Takeaway: Locators Replace Vague Citations"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = ACCENT_BLUE
    p2 = tf_bot.add_paragraph()
    p2.text = "Traditional RAG cites arbitrary text blocks or generic video URLs. Moment RAG embeds exact temporal coordinates directly into the index payload, enabling deep-linked video playback directly at the relevant timestamp (e.g. youtu.be/LPZh9BOjkQs?t=142)."
    p2.font.size = Pt(12)
    p2.font.color.rgb = TEXT_WHITE
    p2.space_before = Pt(4)

    # -------------------------------------------------------------
    # SLIDE 4: Part 1 — Baseline Semantic Search RAG
    # -------------------------------------------------------------
    s4 = prs.slides.add_slide(blank_slide_layout)
    set_slide_bg(s4)
    add_header(s4, "Part 1: Baseline Semantic Search RAG Implementation", "BASELINE PIPELINE • CHARACTER-WINDOW CHUNKING")

    c1 = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    c1.fill.solid()
    c1.fill.fore_color.rgb = CARD_BG
    c1.line.color.rgb = BORDER_COLOR

    t1 = s4.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(5.0), Inches(4.7))
    tf1 = t1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "Baseline Pipeline Steps"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN

    steps = [
        "1. Transcript Extraction: Raw text pulled from YouTube subtitle track.",
        "2. Fixed-Size Chunking: Window split at 500 characters with 50-character sliding overlap.",
        "3. Dense Embedding: Passed chunks to standard embedding model (text-embedding-3-small).",
        "4. Similarity Search: Stored in Qdrant; retrieved top-3 chunks by cosine distance.",
        "5. Prompt Synthesis: Concatenated raw text blocks into prompt context for LLM."
    ]
    for s in steps:
        p = tf1.add_paragraph()
        p.text = s
        p.font.size = Pt(13)
        p.font.color.rgb = TEXT_WHITE
        p.space_before = Pt(8)

    c2 = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    c2.fill.solid()
    c2.fill.fore_color.rgb = CARD_BG
    c2.line.color.rgb = BORDER_COLOR

    t2 = s4.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.1), Inches(4.7))
    tf2 = t2.text_frame
    tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "Inherent Flaws & Failure Modes"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CORAL

    flaws = [
        ("Severed Semantic Context", "Fixed-character cuts sliced sentences and technical definitions right in half, separating subjects from predicates."),
        ("Zero Temporal Fidelity", "The user receives an answer but has no idea at what second or minute in the video the explanation occurs."),
        ("Visual Blindness", "Spoken remarks like 'observe this diagram' lost all meaning because visual frames were ignored."),
        ("Hallucinated Citations", "Without structured locators, the LLM attempted to invent timestamps or cited vague sections.")
    ]
    for title, desc in flaws:
        p = tf2.add_paragraph()
        p.text = f"• {title}:"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p.space_before = Pt(8)
        p_sub = tf2.add_paragraph()
        p_sub.text = f"  {desc}"
        p_sub.font.size = Pt(12)
        p_sub.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------
    # SLIDE 5: Part 2 — Moment RAG Implementation
    # -------------------------------------------------------------
    s5 = prs.slides.add_slide(blank_slide_layout)
    set_slide_bg(s5)
    add_header(s5, "Part 2: Moment RAG-Style Implementation", "MOMENT SEARCH • MULTIMODAL SYNCHRONIZATION")

    pillars = [
        ("1. Temporal Moment Boundaries", "Transcripts are partitioned along natural acoustic pauses, silence intervals, and complete sentences (15–30s blocks). Context is preserved intact.", Inches(0.8), Inches(1.6)),
        ("2. Multimodal Visual Synchronization", "FFmpeg extracts frames at key intervals. Visual features are encoded with CLIP ViT-B/32, linking what is spoken with what is displayed on screen.", Inches(6.8), Inches(1.6)),
        ("3. Structured Locator Contract", "Points are stamped with immutable locators: {start_ms, end_ms}. Citation [1] deterministically deep-links to video playback at exact timestamp.", Inches(0.8), Inches(4.4)),
        ("4. ARGUS Multi-Source Extension", "Extended beyond video to academic papers ({page}) and slide decks ({slide}) in one unified hybrid index with Reciprocal Rank Fusion (RRF).", Inches(6.8), Inches(4.4))
    ]
    for title, desc, left, top in pillars:
        c = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(5.7), Inches(2.6))
        c.fill.solid()
        c.fill.fore_color.rgb = CARD_BG
        c.line.color.rgb = BORDER_COLOR

        t = s5.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), Inches(5.3), Inches(2.2))
        tf_p = t.text_frame
        tf_p.word_wrap = True
        p = tf_p.paragraphs[0]
        p.text = title
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN
        p2 = tf_p.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(13)
        p2.font.color.rgb = TEXT_WHITE
        p2.space_before = Pt(8)

    # -------------------------------------------------------------
    # SLIDE 6: Comparison — Baseline vs Moment RAG
    # -------------------------------------------------------------
    s6 = prs.slides.add_slide(blank_slide_layout)
    set_slide_bg(s6)
    add_header(s6, "Direct Comparison: Baseline RAG vs. Moment RAG", "EVALUATION • ARCHITECTURAL COMPARISON")

    # Table layout
    rows, cols = 6, 3
    left, top, width, height = Inches(0.8), Inches(1.6), Inches(11.7), Inches(5.2)
    table_shape = s6.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table

    table.columns[0].width = Inches(2.7)
    table.columns[1].width = Inches(4.5)
    table.columns[2].width = Inches(4.5)

    headers = ["Dimension / Feature", "Baseline Semantic RAG", "Moment RAG (ARGUS)"]
    for i, h in enumerate(headers):
        cell = table.cell(0, i)
        cell.fill.solid()
        cell.fill.fore_color.rgb = CARD_BG
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN

    data = [
        ("Chunking Strategy", "Arbitrary fixed character/token slice (e.g. 500 chars)", "Natural speech pauses, silence, and semantic units (15–30s)"),
        ("Boundary Integrity", "Splits mid-sentence; fragments context across chunks", "Preserves complete sentences, thoughts, and diagram context"),
        ("Grounding & Citations", "Vague video URL; frequent LLM citation hallucination", "Exact playback timestamp (M:SS), page (p.N), or slide"),
        ("Modality Handling", "Text-only transcript ingestion", "Fuses audio transcript + visual CLIP keyframes"),
        ("Multi-Source Scope", "Isolated single-video transcript search", "Unified search across Video, Research Papers, and Decks"),
    ]
    for row_idx, row_data in enumerate(data, start=1):
        for col_idx, text in enumerate(row_data):
            cell = table.cell(row_idx, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG if row_idx % 2 == 0 else BG_COLOR
            p = cell.text_frame.paragraphs[0]
            p.text = text
            p.font.size = Pt(12)
            p.font.color.rgb = TEXT_WHITE if col_idx > 0 else ACCENT_BLUE

    # -------------------------------------------------------------
    # SLIDE 7: Key Findings & Empirical Results
    # -------------------------------------------------------------
    s7 = prs.slides.add_slide(blank_slide_layout)
    set_slide_bg(s7)
    add_header(s7, "Key Findings & Benchmark Evaluation", "RESULTS • PRODUCTION EVIDENCE")

    cards = [
        ("1. Zero Hallucinated Citations", "Every citation tag [1] emitted by the LLM strictly resolves to an existing chunk locator verified by server regex. Precision: 100%.", Inches(0.8)),
        ("2. Sub-Second Latency & TTFT", "FastAPI streaming endpoint delivers Time-To-First-Token in <350ms, with complete cited answers streamed in <1.2s.", Inches(4.8)),
        ("3. Precision Moment Retrieval", "On queries like 'attention mechanism matrix calculation', Moment RAG retrieved the exact 20s interval where Grant Sanderson highlights the weights.", Inches(8.8)),
    ]
    for title, desc, left in cards:
        c = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(1.6), Inches(3.7), Inches(3.0))
        c.fill.solid()
        c.fill.fore_color.rgb = CARD_BG
        c.line.color.rgb = BORDER_COLOR

        t = s7.shapes.add_textbox(left + Inches(0.2), Inches(1.8), Inches(3.3), Inches(2.6))
        tf_c = t.text_frame
        tf_c.word_wrap = True
        p = tf_c.paragraphs[0]
        p.text = title
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = ACCENT_GREEN
        p2 = tf_c.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(13)
        p2.font.color.rgb = TEXT_WHITE
        p2.space_before = Pt(8)

    # Bottom Callout
    c_live = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(4.9), Inches(11.7), Inches(1.9))
    c_live.fill.solid()
    c_live.fill.fore_color.rgb = CARD_BG
    c_live.line.color.rgb = BORDER_COLOR
    t_live = s7.shapes.add_textbox(Inches(1.1), Inches(5.1), Inches(11.1), Inches(1.6))
    tf_live = t_live.text_frame
    tf_live.word_wrap = True
    p = tf_live.paragraphs[0]
    p.text = "Deployment & Live Production Verification"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    p2 = tf_live.add_paragraph()
    p2.text = "• Live Application: https://momentsearch-api-production.up.railway.app\n• Architecture: 4 Railway services online (FastAPI API, Prefect Worker, Qdrant Hybrid Index, Managed Postgres).\n• Verified with automated SLA benchmarks (bench.py) and crash-resilience sweeper tests."
    p2.font.size = Pt(12)
    p2.font.color.rgb = TEXT_MUTED
    p2.space_before = Pt(4)

    # -------------------------------------------------------------
    # SLIDE 8: Limitations & Future Improvements
    # -------------------------------------------------------------
    s8 = prs.slides.add_slide(blank_slide_layout)
    set_slide_bg(s8)
    add_header(s8, "Limitations & Future Roadmap", "REFLECTION • PRODUCTION ENHANCEMENTS")

    c_lim = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    c_lim.fill.solid()
    c_lim.fill.fore_color.rgb = CARD_BG
    c_lim.line.color.rgb = BORDER_COLOR

    t_lim = s8.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(5.0), Inches(4.7))
    tf_lim = t_lim.text_frame
    tf_lim.word_wrap = True
    p = tf_lim.paragraphs[0]
    p.text = "Current Limitations"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CORAL

    limits = [
        ("Cross-Modality Score Skew", "Spoken dialogue is repetitive and conversational; academic papers are dense and terse. Dense text can score higher than spoken dialogue in raw cosine distance."),
        ("Complex Table Parsing in PDFs", "Multi-column financial/technical tables get flattened to text strings, losing 2D grid relationships."),
        ("Scanned PDF OCR Overhead", "PDFs without native text layers require an expensive OCR fallback pass to avoid empty chunk yields.")
    ]
    for title, desc in limits:
        p = tf_lim.add_paragraph()
        p.text = f"• {title}:"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p.space_before = Pt(8)
        p_sub = tf_lim.add_paragraph()
        p_sub.text = f"  {desc}"
        p_sub.font.size = Pt(12)
        p_sub.font.color.rgb = TEXT_MUTED

    c_imp = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.2))
    c_imp.fill.solid()
    c_imp.fill.fore_color.rgb = CARD_BG
    c_imp.line.color.rgb = BORDER_COLOR

    t_imp = s8.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.1), Inches(4.7))
    tf_imp = t_imp.text_frame
    tf_imp.word_wrap = True
    p = tf_imp.paragraphs[0]
    p.text = "High-Impact Improvements"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN

    improvements = [
        ("Visual Bounding Boxes [x0, y0, x1, y1]", "Capture spatial bounding boxes on PDF pages and presentation slides so the UI can highlight the exact diagram or paragraph in real-time."),
        ("Modality-Aware Cross-Encoder Reranker", "Fine-tune a lightweight reranker across text, speech, and slides to balance modality differences."),
        ("Adaptive Moment Sizing", "Combine audio pitch/prosody, silence intervals, and visual shot transitions to dynamically vary moment lengths from 5s to 45s.")
    ]
    for title, desc in improvements:
        p = tf_imp.add_paragraph()
        p.text = f"• {title}:"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = TEXT_WHITE
        p.space_before = Pt(8)
        p_sub = tf_imp.add_paragraph()
        p_sub.text = f"  {desc}"
        p_sub.font.size = Pt(12)
        p_sub.font.color.rgb = TEXT_MUTED

    output_path = "Assignment3_Moment_Search_Presentation.pptx"
    prs.save(output_path)
    print(f"Presentation saved successfully to {output_path}")

if __name__ == "__main__":
    create_deck()
