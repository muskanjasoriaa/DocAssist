FROM python:3.10-slim

WORKDIR /code

# Install system dependencies if needed (PyMuPDF is pre-compiled, so slim is fine)
COPY ./backend/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the backend code
COPY ./backend/app /code/app

# Set environment variables
ENV PYTHONPATH=/code
ENV UPLOAD_DIR=/code/uploads
ENV VECTOR_DB_PATH=/code/vector_store.json

# Expose Hugging Face's default port
EXPOSE 7860

# Run FastAPI using uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
