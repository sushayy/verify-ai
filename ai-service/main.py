from fastapi import FastAPI
from dotenv import load_dotenv
from google import genai

load_dotenv()

app = FastAPI(title="Verify AI - AI Service")

client = genai.Client()


@app.get("/health")
def health():
    return {"status": "ok", "message": "AI service is running"}


@app.get("/test-gemini")
def test_gemini():
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents="Say 'Gemini connection successful' and nothing else.",
    )
    return {"response": response.text}
