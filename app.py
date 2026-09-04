from fastapi import FastAPI

app = FastAPI(
    title="UNG-MDM",
    description="Uganda National Grid Master Data Management corporate enterprise platform.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "service": "UNG-MDM",
        "name": "Uganda National Grid Master Data Management",
        "classification": "corporate-enterprise",
        "version": "0.1.0",
        "status": "foundation-ready",
    }


@app.get("/health")
def health():
    return {
        "service": "UNG-MDM",
        "status": "healthy",
        "version": "0.1.0",
    }
