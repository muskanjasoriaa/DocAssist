import streamlit as st
import os
import math
import fitz  # PyMuPDF
import google.generativeai as genai
from typing import List, Dict, Any

# 1. Page Configuration
st.set_page_config(page_title="DocAssist - Chat with PDF", page_icon="📄", layout="wide")

# Custom CSS for Premium Dark theme with Library Sidebar & Chat Window
st.markdown("""
<style>
    /* App background */
    .stApp {
        background-color: #0B0F19 !important;
        color: #F3F4F6 !important;
    }
    
    /* Sidebar styling */
    [data-testid="sidebar-content"] {
        background-color: #111827 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        padding-top: 20px !important;
    }
    
    /* Sidebar header */
    .sidebar-logo {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 24px;
    }
    
    .accent-text {
        color: #6366F1;
        text-shadow: 0 0 10px rgba(99, 102, 241, 0.35);
    }
    
    /* Text styling */
    h1, h2, h3, p, label, span, .stMarkdown {
        color: #F3F4F6 !important;
        font-family: 'Outfit', sans-serif;
    }
    
    /* Feature Welcome Box */
    .welcome-box {
        max-width: 700px;
        margin: 40px auto;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
    }
    
    .features-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin-top: 24px;
        width: 100%;
    }
    
    .feature-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 20px 14px;
        border-radius: 12px;
        text-align: center;
    }
    
    .feature-card h4 {
        margin-top: 8px;
        font-size: 14px;
        font-weight: 600;
    }
    
    .feature-card p {
        font-size: 11px;
        color: #9CA3AF !important;
        line-height: 1.4;
    }
    
    /* Chat bubbles */
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 12px;
    }
    
    /* Buttons */
    .stButton button {
        background-color: #4F46E5 !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
    }
    .stButton button:hover {
        background-color: #6366F1 !important;
    }
</style>
""", unsafe_allow_html=True)

# 2. Setup Gemini API Key
api_key = ""
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
elif "gemini_api_key" in st.session_state:
    api_key = st.session_state["gemini_api_key"]

# Sidebar configuration (Admin Dashboard)
with st.sidebar:
    st.markdown("<h2>📄 DocAssist <span class='accent-text'>AI</span></h2>", unsafe_allow_html=True)
    st.write("Smart RAG Document Assistant")
    st.write("---")
    
    # API Key Input
    if not api_key:
        input_key = st.text_input("Enter your Gemini API Key:", type="password")
        if input_key:
            st.session_state["gemini_api_key"] = input_key
            api_key = input_key
            st.rerun()
        st.info("💡 You can get a free key from [Google AI Studio](https://aistudio.google.com/)")
    else:
        st.success("✅ Gemini API Connected")
        
    st.write("---")

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

        # Mock vector fallback
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

# 5. Sidebar Document Upload & Selector (Admin Dashboard)
with st.sidebar:
    st.write("### Upload Document")
    uploaded_file = st.file_uploader("Upload a PDF file:", type="pdf", label_visibility="collapsed")
    
    if uploaded_file:
        doc_name = uploaded_file.name
        if doc_name not in vector_db.store:
            with st.spinner("Processing PDF..."):
                try:
                    chunks = extract_chunks(uploaded_file)
                    if chunks:
                        vector_db.add_document(doc_name, chunks)
                        st.success(f"Processed: {doc_name}")
                    else:
                        st.error("No text found in PDF.")
                except Exception as e:
                    st.error(f"Error: {e}")

    # Document list selection
    st.write("---")
    st.write("### My Library")
    doc_options = list(vector_db.store.keys())
    
    if doc_options:
        selected_doc = st.selectbox("Active Document:", doc_options)
        st.session_state["selected_doc"] = selected_doc
    else:
        st.session_state["selected_doc"] = None
        st.info("Upload a PDF above to begin.")

# 6. Main Chat View (User Dashboard)
selected_doc = st.session_state.get("selected_doc")

if selected_doc:
    st.markdown(f"## Chatting with: <span class='accent-text'>{selected_doc}</span>", unsafe_allow_html=True)
    st.write("---")
    
    # Initialize history
    history_key = f"chat_history_{selected_doc}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []
        
    # Render messages
    for msg in st.session_state[history_key]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    # Input field
    if user_query := st.chat_input("Ask a question about this document..."):
        with st.chat_message("user"):
            st.write(user_query)
        st.session_state[history_key].append({"role": "user", "content": user_query})
        
        with st.spinner("Analyzing document..."):
            chunks = vector_db.search(selected_doc, user_query, top_k=3)
            
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
                        answer = "⚠️ Could not connect to Gemini API. Please check your API key."
                else:
                    # Demo Mode
                    answer = "⚠️ **DEMO MODE (No API Key set)**\n\nHere are the top matches found in your PDF:\n\n"
                    for idx, chunk in enumerate(chunks):
                        clean_chunk = chunk.replace("\n", " ")
                        answer += f"**Match {idx + 1}:**\n> ... {clean_chunk[:300]} ...\n\n"
                    answer += "*Enter a Gemini API Key in the sidebar to enable full answers.*"
            else:
                answer = "No matching text could be found."
                
            with st.chat_message("assistant"):
                st.write(answer)
            st.session_state[history_key].append({"role": "assistant", "content": answer})

else:
    # Beautiful welcome page on first load
    st.markdown("""
    <div class="welcome-box">
        <h1 style="font-size: 38px;">Ask anything about your PDF</h1>
        <p style="color: #9CA3AF; font-size: 15px; max-width: 500px;">
            This RAG-based assistant splits, stores, and searches your document text using local semantic vectors and Gemini AI.
        </p>
        <div class="features-grid">
            <div class="feature-card">
                <h3 style="font-size: 24px;">🔍</h3>
                <h4>Semantic Search</h4>
                <p>Scans the PDF to locate sections matching your query.</p>
            </div>
            <div class="feature-card">
                <h3 style="font-size: 24px;">⚡</h3>
                <h4>Fast Responses</h4>
                <p>Uses Gemini 1.5 Flash to provide answers in seconds.</p>
            </div>
            <div class="feature-card">
                <h3 style="font-size: 24px;">🛡️</h3>
                <h4>Secure & Private</h4>
                <p>All embeddings and search operations run in memory.</p>
            </div>
        </div>
        <p style="margin-top: 40px; color: #6366F1; font-weight: 500;">
            ⬅️ Upload a PDF in the sidebar to begin!
        </p>
    </div>
    """, unsafe_allow_html=True)
