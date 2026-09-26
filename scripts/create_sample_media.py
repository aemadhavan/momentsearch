import fitz
from pathlib import Path

data_dir = Path("data/sample_media")
data_dir.mkdir(parents=True, exist_ok=True)

# 1. Paper PDF
pdf_path = data_dir / "sample_paper.pdf"
doc = fitz.open()

p1 = doc.new_page()
p1.insert_text((50, 72), "Title: Retrieval Augmented Generation for Enterprise Search\n\nAbstract: Retrieval augmented generation combines external knowledge retrieval with large language model generation.\nIntroduction: Traditional knowledge engines rely exclusively on parametric memory.", fontsize=12)

p2 = doc.new_page()
p2.insert_text((50, 72), "Section 2: Hybrid Retrieval with Dense and Sparse Signals\n\nWhat does the survey say about hybrid retrieval? The survey states that hybrid retrieval fuses dense vector similarity with sparse BM25 keyword matching. Dense vectors capture high-level conceptual semantics while sparse indices preserve exact keywords, serial numbers, and specialized technical acronyms.", fontsize=12)

p3 = doc.new_page()
p3.insert_text((50, 72), "Section 3: Empirical Benchmarks and Locators\n\nLocators ensure precise attribution: every claim links back to page numbers in papers, timestamps in videos, and slide numbers in decks.", fontsize=12)

doc.save(str(pdf_path))
doc.close()
print(f"Created {pdf_path}")

# 2. Deck PDF
deck_path = data_dir / "sample_deck.pdf"
deck = fitz.open()

s1 = deck.new_page(width=720, height=405)
s1.insert_text((60, 60), "ARGUS: Multimodal Knowledge Retrieval\nArchitecture Keynote", fontsize=20)

s2 = deck.new_page(width=720, height=405)
s2.insert_text((60, 60), "Slide 2: Unified Hybrid Indexing\n\nThis is the slide about one index for every source. Academic papers, slide decks, and video moments all land in a single hybrid Qdrant collection.", fontsize=18)

s3 = deck.new_page(width=720, height=405)
s3.insert_text((60, 60), "Slide 3: Work Queue Decoupling\n\nPrefect Cloud decouples heavy ingestion from search.", fontsize=18)

deck.save(str(deck_path))
deck.close()
print(f"Created {deck_path}")
