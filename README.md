# DocAssist AI

DocAssist AI is an enterprise-grade document assistant built using Retrieval-Augmented Generation (RAG). It allows organizations to upload PDFs and documents into collections and enables users to ask questions based on those documents.

## Features

### Admin Dashboard

* User authentication
* Upload PDF, DOCX, and TXT files
* Create and manage collections
* View and delete documents

### User Dashboard

* Interactive chat interface
* Ask questions from uploaded documents
* View chat history
* Source-based responses

## Tech Stack

### Frontend

* Next.js
* TypeScript
* Tailwind CSS
* Shadcn UI

### Backend

* FastAPI
* LangChain

### Database

* PostgreSQL

### Vector Database

* Qdrant

### AI Model

* OpenAI GPT-4o / Gemini

## Architecture

Document Upload → Text Extraction → Chunking → Embeddings → Vector Database → Retrieval → LLM Response

## Project Structure

frontend/
backend/
uploads/
vector_store/
docker-compose.yml

## Future Enhancements

* Voice Assistant
* Multi-language support
* Analytics Dashboard
* Human Support Escalation
* Email Summaries

## Objective

The goal of this project is to provide an intelligent knowledge assistant that helps users retrieve accurate information from organizational documents efficiently.
