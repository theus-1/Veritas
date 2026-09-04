from fastapi import FastAPI
from app.api.routers.analysis import router as create_analysis

app = FastAPI(
    title="Veritas API",
    version="0.1.0"
)

app.include_router(create_analysis)


@app.get("/")
async def root():
    return{"name": app.title,
           "version": app.version,
           "status": "Online"
           }

@app.get("/health")
async def health():
    return{"status": "healthy"}
