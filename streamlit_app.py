import streamlit as st
import os
import math
import json
import fitz  # PyMuPDF
import google.generativeai as genai
from typing import List, Dict, Any

# 1. Page Configuration & Title
st.set_page_config(page_title="DocAssist - Chat with PDF", page_icon="📄", layout="wide")

# Custom CSS for premium styling
st.markdown("""
<style>
    .main {
        background-color: #0B0F19;
        color: #F3F4F6;
    }
    .stApp {
        background-color: #0B0F19;
    }
    .stSidebar {
        background-color: #111827 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    h1, h2, h3 {
        color: #FFFFFF !important;
        font-family: 'Outfit', sans-serif;
    }
    .accent-text {
        color: #6366F1;
        text-shadow: 0 0 10px rgba(99, 102, 241, 0.35);
    }
    /* Chat message formatting */
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# 2. Setup Gemini API Key
api_key = ""
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
elif "gemini_api_key" in st.session_state:
    api_key = st.session_state["gemini_api_key"]

# Sidebar configuration
with st.sidebar:
    st.markdown("# 📄 DocAssist <span class='accent-text'>AI</span>", unsafe_allow_html=True)
    st.write("Smart RAG Document Assistant")
    st.write("---")
    
    # API Key Input if not in secrets
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

# Configure genai SDK if key is set
if api_key:
    genai.configure(api_key=api_key)

# 3. Local Vector Store logic
class LocalVectorStore:
    def __init__(self):
        # We store the vectors in Streamlit session state so they persist during the session
        if "vector_store" not in st.session_state:
            st.session_state["vector_store"] = {}
        self.store = st.session_state["vector_store"]

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
            except Exception as e:
                pass # Fallback to mock

        # Fallback Mock Embedding
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
                "chunk_id": idx,
                "text": chunk,
                "vector": vector
            })
        self.store[doc_name] = doc_data
        st.session_state["vector_store"] = self.store

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

vector_db = LocalVectorStore()

# 4. Integrated PyMuPDF (fitz) text extractor (user's code)
def extract_chunks(uploaded_file, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    # Read PyMuPDF document from file bytes
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

# 5. Document Upload Section (Sidebar)
with st.sidebar:
    st.write("### Upload Document")
    uploaded_file = st.file_uploader("Upload a PDF file:", type="pdf")
    
    if uploaded_file:
        doc_name = uploaded_file.name
        if doc_name not in vector_db.store:
            with st.spinner("Processing PDF and generating embeddings..."):
                try:
                    chunks = extract_chunks(uploaded_file)
                    if chunks:
                        vector_db.add_document(doc_name, chunks)
                        st.success(f"Processed: {doc_name}")
                    else:
                        st.error("No readable text found in this PDF.")
                except Exception as e:
                    st.error(f"Error processing PDF: {e}")

    # Library selector
    st.write("---")
    st.write("### Select Active Document")
    doc_options = list(vector_db.store.keys())
    
    if doc_options:
        selected_doc = st.selectbox("Select document to chat with:", doc_options)
        st.session_state["selected_doc"] = selected_doc
    else:
        st.session_state["selected_doc"] = None
        st.info("Upload a PDF to start.")

# 6. Chat Interface
selected_doc = st.session_state.get("selected_doc")

if selected_doc:
    st.markdown(f"## Chatting with: <span class='accent-text'>{selected_doc}</span>", unsafe_allow_html=True)
    
    # Initialize chat history
    history_key = f"chat_history_{selected_doc}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []
        
    # Render chat history
    for msg in st.session_state[history_key]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    # User Query Input
    if user_query := st.chat_input("Ask a question about this document..."):
        # Display user message
        with st.chat_message("user"):
            st.write(user_query)
        st.session_state[history_key].append({"role": "user", "content": user_query})
        
        # Call RAG with Gemini
        with st.spinner("Searching document & generating answer..."):
            # 1. Retrieve top matching chunks
            chunks = vector_db.search(selected_doc, user_query, top_k=3)
            
            if chunks:
                context = "\n---\n".join(chunks)
                
                # 2. Call Gemini
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
                        except Exception as e:
                            pass
                    
                    if not answer:
                        answer = "⚠️ Could not connect to Gemini API. Please check your API key."
                else:
                    # Demo fallback output
                    answer = "⚠️ **DEMO MODE (No API Key set)**\n\nHere are the top matches found in your PDF:\n\n"
                    for idx, chunk in enumerate(chunks):
                        clean_chunk = chunk.replace("\n", " ")
                        answer += f"**Match {idx + 1}:**\n> ... {clean_chunk[:300]} ...\n\n"
                    answer += "*Enter a Gemini API Key in the sidebar to enable full answers.*"
            else:
                answer = "Could not find any matching text in the document."
                
            # Display assistant message
            with st.chat_message("assistant"):
                st.write(answer)
            st.session_state[history_key].append({"role": "assistant", "content": answer})

else:
    # Welcome display when no document is active
    st.markdown("""
    <div style='text-align: center; margin-top: 100px;'>
        <h1 style='font-size: 40px;'>Welcome to <span class='accent-text'>DocAssist AI</span></h1>
        <p style='color: #9CA3AF; font-size: 18px;'>Upload a PDF in the sidebar and enter your Gemini API Key to start chatting with your documents.</p>
    </div>
    """, unsafe_allow_html=True)
