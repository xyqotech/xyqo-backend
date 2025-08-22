"""
Simple health check endpoint for Railway
"""
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.get("/health")
async def health():
    return PlainTextResponse("OK")

@app.get("/")
async def root():
    return {"status": "healthy", "service": "xyqo-backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
