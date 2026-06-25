import streamlit as st
import os
import math
import fitz  # PyMuPDF
import google.generativeai as genai
from typing import List

# 1. Page Configuration
st.set_page_config(page_title="Ask your PDF", page_icon="💬", layout="centered")

# Custom CSS to force a clean light theme matching the image
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    /* Text colors */
    h1, h2, h3, p, label, .stMarkdown {
        color: #1F2937 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Title styling */
    h1 {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* File uploader container */
    div[data-testid="stFileUploader"] {
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }
    
    /* Hide the default sidebar to match the layout in the image */
    [data-testid="sidebar-content"] {
        display: none;
    }
    
    /* Input box styling */
    .stTextInput input {
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        color: #1F2937 !important;
        border-radius: 6px !important;
    }
    
    /* Answer box spacing */
    .answer-box {
        margin-top: 1.5rem;
        font-size: 1.05rem;
        line-height: 1.6;
        color: #1F2937;
    }
</style>
""", unsafe_allow_html=True)

# 2. Setup Gemini API Key
api_key = ""
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
elif "gemini_api_key" in st.session_state:
    api_key = st.session_state["gemini_api_key"]

# Expandable API Key configuration at the top of the page
with st.expander("🔑 Configure Gemini API Key", expanded=not bool(api_key)):
    input_key = st.text_input("Enter your Gemini API Key:", type="password", value=api_key)
    if input_key:
        st.session_state["gemini_api_key"] = input_key
        api_key = input_key
        st.success("API Key saved!")

if api_key:
    genai.configure(api_key=api_key)

# 3. Vector Database Logic (in-memory session state)
class SessionVectorStore:
    def __init__(self):
        if "vectors" not in st.session_state:
            st.session_state["vectors"] = {}
        self.store = st.session_state["vectors"]

    def _get_embedding(self, text: str) -> List[float]:
        if api_key:
            try:
                response = genai.embed_content(
                    model="models/text-embedding-004",
                    contents=text,
                    task_type="retrieval_document"
                )
                if 'embedding' in response:
                    return response['embedding']
                elif isinstance(response, dict) and 'embedding' in response.get('embedding', {}):
                    return response['embedding']['values']
            except Exception:
                pass

        # Mock vector fallback for offline/demo mode
        mock_vector = [0.0] * 128
        for char in text:
            idx = ord(char) % 128
            mock_vector[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in mock_vector))
        if norm > 0:
            mock_vector = [x / norm for x in mock_vector]
        return mock_vector

    def add_document(self, doc_name: str, chunks: List[str]):
        doc_data = []
        for idx, chunk in enumerate(chunks):
            vector = self._get_embedding(chunk)
            doc_data.append({
                "text": chunk,
                "vector": vector
            })
        self.store[doc_name] = doc_data
        st.session_state["vectors"] = self.store

    def search(self, doc_name: str, query: str, top_k: int = 3) -> List[str]:
        if doc_name not in self.store:
            return []

        query_vector = self._get_embedding(query)
        doc_data = self.store[doc_name]

        results = []
        for item in doc_data:
            vec = item["vector"]
            dot_product = sum(a * b for a, b in zip(query_vector, vec))
            norm_q = math.sqrt(sum(a * a for a in query_vector))
            norm_v = math.sqrt(sum(b * b for b in vec))
            
            similarity = 0.0
            if norm_q > 0 and norm_v > 0:
                similarity = dot_product / (norm_q * norm_v)

            results.append((similarity, item["text"]))

        results.sort(key=lambda x: x[0], reverse=True)
        return [text for sim, text in results[:top_k]]

vector_db = SessionVectorStore()

# 4. PyMuPDF (fitz) text extractor (user's code)
def extract_chunks(uploaded_file, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    file_bytes = uploaded_file.read()
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    full_text = ""

    for page in doc:
        full_text += page.get_text()

    doc.close()

    # Split into chunks with overlap
    words = full_text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)

    return chunks

# 5. UI Elements matching the layout in the image
st.markdown("<h1>Ask your PDF 💬</h1>", unsafe_allow_html=True)

# Upload Section
uploaded_file = st.file_uploader("Upload your PDF", type="pdf", label_visibility="visible")

active_doc_name = None
if uploaded_file:
    active_doc_name = uploaded_file.name
    if active_doc_name not in vector_db.store:
        with st.spinner("Processing PDF..."):
            chunks = extract_chunks(uploaded_file)
            if chunks:
                vector_db.add_document(active_doc_name, chunks)
                st.success("PDF processed successfully!")
            else:
                st.error("No readable text found in this PDF.")

# Ask Question Section
user_query = st.text_input("Ask a question about your PDF:", placeholder="Enter your question here...")

if user_query:
    if not active_doc_name:
        st.warning("Please upload a PDF document first.")
    else:
        with st.spinner("Analyzing..."):
            chunks = vector_db.search(active_doc_name, user_query, top_k=3)
            
            if chunks:
                context = "\n---\n".join(chunks)
                
                if api_key:
                    model_names = ["gemini-1.5-flash", "gemini-pro", "gemini-2.5-flash"]
                    answer = ""
                    for model_name in model_names:
                        try:
                            model = genai.GenerativeModel(model_name)
                            prompt = (
                                "You are a helpful assistant. Answer the user's question based strictly on the provided document context below.\n"
                                "If the answer cannot be found in the context, say that the information is not present in the document. Do not make up facts.\n\n"
                                f"CONTEXT:\n{context}\n\n"
                                f"QUESTION: {user_query}\n\n"
                                "ANSWER:"
                            )
                            response = model.generate_content(prompt)
                            if response:
                                answer = response.text
                                break
                        except Exception:
                            pass
                    
                    if not answer:
                        answer = "⚠️ Could not connect to Gemini API. Please verify your API key."
                else:
                    # Demo Mode Fallback
                    answer = "⚠️ **DEMO MODE (No API Key configured)**\n\nHere are the top matching text chunks found in your document:\n\n"
                    for idx, chunk in enumerate(chunks):
                        clean_chunk = chunk.replace("\n", " ")
                        answer += f"**Match {idx + 1}:**\n> ... {clean_chunk[:300]} ...\n\n"
                    answer += "*Enter a Gemini API Key at the top of the page to generate full AI answers.*"
            else:
                answer = "No matching text could be found in the document."
            
            # Display Answer exactly as in the image layout
            st.markdown(f"<div class='answer-box'><strong>Answer:</strong> {answer}</div>", unsafe_allow_html=True)
