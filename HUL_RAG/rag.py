import pandas as pd
import os
import re
from sentence_transformers import SentenceTransformer
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ---------- helpers ----------

def row_to_text(row):
    parts = []
    for col, val in row.items():
        if pd.isna(val):
            continue
        parts.append(f"{col}: {val}")
    return " | ".join(parts)

def extract_course_code(text):
    match = re.search(r'HUL\d{3}', text)
    return match.group(0) if match else "UNKNOWN"

# ---------- load excel files ----------

documents = []

for file in os.listdir(DATA_DIR):
    if not file.endswith(".xlsx"):
        continue

    path = os.path.join(DATA_DIR, file)
    df = pd.read_excel(path)

    for _, row in df.iterrows():
        text = row_to_text(row)
        code = extract_course_code(text)

        documents.append({
            "course_code": code,
            "text": text
        })

print(f"✅ Loaded {len(documents)} feedback entries")

# ---------- embeddings ----------

embedder = SentenceTransformer("all-MiniLM-L6-v2")
texts = [doc["text"] for doc in documents]
embeddings = embedder.encode(texts)

print(f"✅ Embeddings created: {embeddings.shape}")

# ---------- retrieval ----------

def retrieve(query, k=5):
    query_emb = embedder.encode([query])[0]
    scores = np.dot(embeddings, query_emb)
    top_idx = np.argsort(scores)[-k:][::-1]
    return [documents[i] for i in top_idx]

# ---------- interactive loop ----------

while True:
    query = input("\nAsk about HULs (or type 'exit'): ")
    if query.lower() == "exit":
        break

    results = retrieve(query, k=5)

    print("\n🔍 Top matches:\n")
    for r in results:
        print(f"[{r['course_code']}] {r['text']}\n")
