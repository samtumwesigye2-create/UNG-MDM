from fastapi import FastAPI

from app import app as mdm_app
from sso_router import router as sso_router

app = FastAPI(title="UNG-MDM", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(sso_router)
app.mount("/", mdm_app)
