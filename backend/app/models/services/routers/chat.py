from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.services.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["chat"])
rag_service = RAGService()

class ChatRequest(BaseModel):
    document_id: int
    message: str

@router.post("")
def chat_with_document(request: ChatRequest):
    try:
        answer = rag_service.generate_answer(request.document_id, request.message)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
