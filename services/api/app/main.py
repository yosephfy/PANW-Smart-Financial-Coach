from fastapi import FastAPI


app = FastAPI(title="Smart Financial Coach API", version="0.1.0")


@app.get("/", tags=["meta"])
def root():
    return {
        "name": "Smart Financial Coach API",
        "status": "ok",
        "endpoints": ["/health"],
    }


@app.get("/health", tags=["meta"])
def health():
    return {"status": "healthy"}

