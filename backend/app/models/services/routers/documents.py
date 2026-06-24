import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.collection import Document
from app.config import settings
from app.models.services.pdf_par import extract_chunks
from app.models.services.vector_store import LocalVectorStore

router = APIRouter(prefix="/documents", tags=["documents"])
vector_store = LocalVectorStore()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # 1. Create a database record
    db_doc = Document(filename=file.filename, filepath="", status="processing")
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    try:
        # 2. Save the uploaded file locally
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(settings.UPLOAD_DIR, f"{db_doc.id}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update filepath in database
        db_doc.filepath = file_path
        db.commit()

        # 3. Parse chunks and generate embeddings
        chunks = extract_chunks(file_path)
        
        if not chunks:
            db_doc.status = "failed"
            db.commit()
            raise HTTPException(status_code=400, detail="No readable text could be extracted from this PDF.")

        vector_store.add_document(db_doc.id, chunks)

        # 4. Mark status as ready
        db_doc.status = "ready"
        db.commit()

        return {"id": db_doc.id, "filename": db_doc.filename, "status": "ready"}

    except Exception as e:
        db_doc.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).all()
    return [{"id": d.id, "filename": d.filename, "upload_time": d.upload_time.isoformat() if d.upload_time else None, "status": d.status} for d in docs]

@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Delete PDF file
    if doc.filepath and os.path.exists(doc.filepath):
        try:
            os.remove(doc.filepath)
        except Exception as e:
            print(f"Error removing file {doc.filepath}: {e}")

    # Delete vectors
    vector_store.delete_document(doc_id)

    # Delete db record
    db.delete(doc)
    db.commit()

    return {"message": "Document deleted successfully"}
