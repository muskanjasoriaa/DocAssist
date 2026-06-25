---
title: DocAssist
emoji: 📄
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# DocAssist: PDF Chat RAG Application

This is a Retrieval-Augmented Generation (RAG) web application that allows users to upload PDF documents and chat with them using the Gemini API.

## Local Development

1. Install requirements:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. Run the application:
   ```bash
   PYTHONPATH=backend python -m app.main
   ```
