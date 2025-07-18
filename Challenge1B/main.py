import os
import glob
import json
import datetime
import pdfplumber
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

TOP_N_EXTRACT = 5
MIN_SECTION_CHAR = 60

def extract_sections(pdf_path):
    sections = []
    doc_first_heading = None
    heading_fontsize = None  # Will be set as the maximum fontsize found

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # (1) Scan all pages to determine the biggest font size -- assume that's headings
            max_fontsize = 0
            for page in pdf.pages:
                try:
                    words = page.extract_words(use_text_flow=True, extra_attrs=["size"])
                    for w in words:
                        sz = float(w['size'])
                        if sz > max_fontsize:
                            max_fontsize = sz
                except:
                    continue
            heading_fontsize = max_fontsize

            # (2) On each page, use that fontsize to find headings, split sections
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    # Extract all words with font size info
                    words = page.extract_words(use_text_flow=True, keep_blank_chars=False, extra_attrs=["size"])
                    # Group by lines and fontsize
                    lines = []
                    curr_line = ""
                    curr_size = None
                    last_bottom = None
                    for word in words:
                        if curr_size is None:
                            curr_size = word['size']
                            curr_line = word['text']
                            last_bottom = word['bottom']
                        elif abs(float(word['bottom']) - float(last_bottom)) < 2.5 and word['size']==curr_size:
                            # Same line, concatenate
                            curr_line += " " + word['text']
                            last_bottom = word['bottom']
                        else:
                            # New line block
                            lines.append((curr_line.strip(), curr_size))
                            curr_line = word['text']
                            curr_size = word['size']
                            last_bottom = word['bottom']
                    if curr_line:
                        lines.append((curr_line.strip(), curr_size))

                    # Now, split into sections by heading
                    curr_title = None
                    curr_content = []
                    for line_text, sz in lines:
                        if float(sz) >= heading_fontsize - 0.1:  # Allow for small float errors
                            # New heading
                            if curr_content and curr_title is not None and len("\n".join(curr_content)) >= MIN_SECTION_CHAR:
                                sections.append({
                                    "title": curr_title,
                                    "content": "\n".join(curr_content),
                                    "page": page_num
                                })
                            curr_title = line_text
                            if doc_first_heading is None:
                                doc_first_heading = curr_title
                            curr_content = []
                        else:
                            curr_content.append(line_text)
                    # Last content on page
                    if curr_content and curr_title is not None and len("\n".join(curr_content)) >= MIN_SECTION_CHAR:
                        sections.append({
                            "title": curr_title,
                            "content": "\n".join(curr_content),
                            "page": page_num
                        })
                except Exception as e:
                    print(f"    [WARN] pdfplumber error page {page_num} {pdf_path}: {e}")

        # Fallback: if no headings, use a generic document title or first page's first line
        if not sections:
            with pdfplumber.open(pdf_path) as pdf:
                text = (pdf.pages[0].extract_text() or "").strip().split('\n')
                doc_first_heading = text[0] if text else "Document Start"
                body = "\n".join(text[1:])
                sections.append({
                    "title": doc_first_heading, "content": body, "page": 1
                })

        # If some sections still lack a heading, assign doc_first_heading
        for s in sections:
            if not s["title"]:
                s["title"] = doc_first_heading if doc_first_heading else "Document Start"

    except Exception as e:
        print(f"  Could not parse {pdf_path}: {e}")
    return sections


def rank_sections(sections, query, vectorizer):
    texts = [s["title"] + "\n" + s["content"][:600] for s in sections]
    if not texts:
        return []
    tfidf_matrix = vectorizer.fit_transform(texts + [query])
    # Query is the last row
    query_vec = tfidf_matrix[-1]
    sections_vecs = tfidf_matrix[:-1]
    scores = cosine_similarity(query_vec, sections_vecs)[0]
    ranked = sorted(zip(scores, sections), key=lambda x: -x[0])
    return [(i+1, score, s) for i, (score, s) in enumerate(ranked)]

def analyze_subsection(section, query, vectorizer):
    paras = re.split(r'(\n{2,}|\.\s)', section["content"])
    paras = [p.strip() for p in paras if len(p.strip()) > 40]
    if not paras:
        return section["content"].strip()[:350]
    tfidf_matrix = vectorizer.fit_transform(paras + [query])
    query_vec = tfidf_matrix[-1]
    paras_vecs = tfidf_matrix[:-1]
    scores = cosine_similarity(query_vec, paras_vecs)[0]
    best_idx = int(np.argmax(scores))
    return paras[best_idx][:350]

def process_collection(folder):
    # print(f'Processing "{folder}"')
    input_path = os.path.join(folder, "challenge1b_input.json")
    if not os.path.exists(input_path):
        print(f"  - challenge1b_input.json not found, skipping.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    documents_json = input_data.get("documents", [])
    doc_map = {doc["filename"]: doc.get("title", "") for doc in documents_json}
    persona = input_data.get("persona", {}).get("role", "")
    job = input_data.get("job_to_be_done", {}).get("task", "")
    pdf_dir = os.path.join(folder, 'PDFs')
    pdf_files = [os.path.join(pdf_dir, filename) for filename in doc_map.keys() if os.path.isfile(os.path.join(pdf_dir, filename))]
    if not pdf_files:
        print(f"  - No valid PDFs found to analyze.")
        return

    query = f"{persona.strip()} {job.strip()}"
    vectorizer = TfidfVectorizer()

    all_sections = []
    for pdf in pdf_files:
        doc_sections = extract_sections(pdf)
        for sec in doc_sections:
            sec['document'] = os.path.basename(pdf)
        all_sections.extend(doc_sections)

    ranked_sections = rank_sections(all_sections, query, vectorizer)

    import datetime

    metadata = {
        "input_documents": [os.path.basename(x) for x in pdf_files],
        "persona": persona,
        "job_to_be_done": job,
        "processing_timestamp": datetime.datetime.now().isoformat()
    }
    extracted_sections = []
    sub_section_analysis = []
    for imp_rank, score, sec in ranked_sections[:TOP_N_EXTRACT]:
        extracted_sections.append({
            "document": sec["document"],
            "section_title": sec["title"],
            "importance_rank": imp_rank,
            "page_number": sec["page"]
        })
        ref_text = analyze_subsection(sec, query, vectorizer)
        sub_section_analysis.append({
            "document": sec["document"],
            "refined_text": ref_text,
            "page_number": sec["page"]
        })

    out_dict = {
        "metadata": metadata,
        "extracted_sections": extracted_sections,
        "subsection_analysis": sub_section_analysis
    }
    out_path = os.path.join(folder, "challenge1b_output.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_dict, f, indent=2,ensure_ascii=False)
    print(f"  - Results written to challenge1b_output.json")

if __name__ == "__main__":
    print("Start Processing")
    base = os.getcwd()
    folders = [f for f in glob.glob(os.path.join(base, "Collection*")) if os.path.isdir(f)]
    if not folders:
        print("No 'Collection' folders found.")
    for fold in sorted(folders):
        process_collection(fold)
    print("Completed Processing")
