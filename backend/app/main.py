from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return{"name": "Veritas API",
           "version": "0.1.0",
           "status": "Online"
           }

@app.get("/health")
async def health():
    return{"status": "healthy"}
