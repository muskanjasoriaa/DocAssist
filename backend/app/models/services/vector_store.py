import os
import json
import math
from typing import List, Dict, Any
from app.config import settings
import google.generativeai as genai

# Setup Gemini API key if present
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

class LocalVectorStore:
    def __init__(self, db_path: str = settings.VECTOR_DB_PATH):
        self.db_path = db_path
        self.store = self._load_store()

    def _load_store(self) -> Dict[str, Any]:
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_store(self):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.store, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving vector store: {e}")

    def _get_embedding(self, text: str) -> List[float]:
        if settings.GEMINI_API_KEY:
            try:
                response = genai.embed_content(
                    model="models/text-embedding-004",
                    contents=text,
                    task_type="retrieval_document"
                )
                # Google Generative AI response format can vary, usually it's in ['embedding']
                if 'embedding' in response:
                    return response['embedding']
                elif isinstance(response, dict) and 'embedding' in response.get('embedding', {}):
                    return response['embedding']['values']
            except Exception as e:
                print(f"Error calling Gemini Embedding API: {e}")
                # Fallback to local embedding logic below

        # Deterministic mock embedding based on character frequencies
        # (This ensures the app works in Demo mode without crashing)
        mock_vector = [0.0] * 128
        for char in text:
            idx = ord(char) % 128
            mock_vector[idx] += 1.0
        
        # Normalize the vector
        norm = math.sqrt(sum(x * x for x in mock_vector))
        if norm > 0:
            mock_vector = [x / norm for x in mock_vector]
        return mock_vector

    def add_document(self, doc_id: int, chunks: List[str]):
        self.store = self._load_store()
        doc_key = str(doc_id)
        doc_data = []
        for idx, chunk in enumerate(chunks):
            vector = self._get_embedding(chunk)
            doc_data.append({
                "chunk_id": idx,
                "text": chunk,
                "vector": vector
            })
        self.store[doc_key] = doc_data
        self._save_store()

    def delete_document(self, doc_id: int):
        self.store = self._load_store()
        doc_key = str(doc_id)
        if doc_key in self.store:
            del self.store[doc_key]
            self._save_store()

    def search(self, doc_id: int, query: str, top_k: int = 3) -> List[str]:
        self.store = self._load_store()
        doc_key = str(doc_id)
        if doc_key not in self.store:
            return []

        query_vector = self._get_embedding(query)
        doc_data = self.store[doc_key]

        results = []
        for item in doc_data:
            # Cosine similarity: dot_product(A, B) / (norm(A) * norm(B))
            vec = item["vector"]
            dot_product = sum(a * b for a, b in zip(query_vector, vec))
            norm_q = math.sqrt(sum(a * a for a in query_vector))
            norm_v = math.sqrt(sum(b * b for b in vec))
            
            similarity = 0.0
            if norm_q > 0 and norm_v > 0:
                similarity = dot_product / (norm_q * norm_v)

            results.append((similarity, item["text"]))

        # Sort by similarity in descending order
        results.sort(key=lambda x: x[0], reverse=True)
        return [text for sim, text in results[:top_k]]
