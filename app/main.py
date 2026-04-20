# import os
# os.environ['FLAGS_use_mkldnn'] = '0'
# os.environ['PADDLE_ONEDNN_OPTERS'] = '0'
# os.environ['PADDLE_WITH_MKLDNN'] = 'OFF'

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.routes import documents

app = FastAPI(
    title="OCR Reading API",
    description="A simple API to read documents and extract form fields using OCR",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])

@app.get("/")
async def root():
    return {"message": "Welcome to the OCR Reading API. Go to /docs for API documentation."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
