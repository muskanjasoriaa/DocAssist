from app.config import settings
from app.models.services.vector_store import LocalVectorStore
import google.generativeai as genai

class RAGService:
    def __init__(self):
        self.vector_store = LocalVectorStore()

    def generate_answer(self, doc_id: int, query: str) -> str:
        # 1. Retrieve the top relevant chunks for this document
        chunks = self.vector_store.search(doc_id=doc_id, query=query, top_k=3)
        
        if not chunks:
            return "No text could be extracted or found in this document. Please check the PDF file."

        # 2. Build the context string
        context = "\n---\n".join(chunks)

        # 3. Call the Gemini API if configured
        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                
                # List of model names to try in order of preference
                model_names = ["gemini-1.5-flash", "gemini-pro", "gemini-2.5-flash"]
                response = None
                last_error = None
                
                prompt = (
                    "You are a helpful assistant. Answer the user's question based strictly on the provided document context below.\n"
                    "If the answer cannot be found in the context, say that the information is not present in the document. Do not make up facts.\n\n"
                    f"CONTEXT:\n{context}\n\n"
                    f"QUESTION: {query}\n\n"
                    "ANSWER:"
                )
                
                for model_name in model_names:
                    try:
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(prompt)
                        if response:
                            return response.text
                    except Exception as e:
                        print(f"Failed to use model {model_name}: {e}")
                        last_error = e
                
                if last_error:
                    raise last_error
            except Exception as e:
                print(f"Error calling Gemini Chat API: {e}")
                return f"Error executing RAG chat: {e}"

        # 4. Fallback/Demo Response
        demo_response = (
            "⚠️ **DEMO MODE (No GEMINI_API_KEY set)**\n\n"
            f"Here are the top matches found in your PDF matching your query *\"{query}\"*:\n\n"
        )
        for idx, chunk in enumerate(chunks):
            # Limit chunk length for display
            clean_chunk = chunk.replace("\n", " ")
            demo_response += f"**Match {idx + 1}:**\n> ... {clean_chunk[:300]} ...\n\n"
        demo_response += "*Please configure `GEMINI_API_KEY` in your environment to enable full conversational AI answers.*"
        
        return demo_response
