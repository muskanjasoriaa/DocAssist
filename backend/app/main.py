import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.models.services.routers import documents, chat

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PDF Chat RAG API")

# Add CORS Middleware to enable communication from different ports if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

# Resolve absolute path to frontend directory
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(current_dir, "frontend")
os.makedirs(frontend_dir, exist_ok=True)

# Mount the static files server at the root level to serve the frontend interface
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

