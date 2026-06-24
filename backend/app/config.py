import os

# Resolves the path to the backend/.env file
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
env_path = os.path.join(backend_dir, ".env")

# Automatically read settings from .env file if it exists
if os.path.exists(env_path):
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    # Strip any surrounding quotes or spaces
                    val = val.strip().strip('"').strip("'")
                    os.environ[key.strip()] = val
    except Exception as e:
        print(f"Error loading .env file: {e}")

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./vector_store.json")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

if settings.GEMINI_API_KEY:
    print("✅ Gemini API Key detected and loaded successfully!")
else:
    print("⚠️ No Gemini API Key detected. Running in Demo Mode.")

