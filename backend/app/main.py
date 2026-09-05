from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.analysis import router as analysis_router
from app.core.config import Config
from app.core.exceptions import VeritasException

config = Config()

app = FastAPI(
    title="Veritas API",
    description="API para análise e verificação de notícias.",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=config.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    analysis_router,
    prefix="/analysis",
    tags=["Analysis"],
)


@app.get("/")
async def root():
    return {
        "message": "Veritas API funcionando."
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }


@app.exception_handler(VeritasException)
async def veritas_exception_handler(
    request: Request,
    exc: VeritasException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        },
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Ocorreu um erro interno no servidor.",
            }
        },
    )
