import asyncio
import logging
from fastapi import APIRouter, Request, HTTPException
from app.utils.file_handler import get_images_from_upload
from app.service.ocr_service import extract_text_from_all_images
from app.service.parser_engine import parse_extracted_text

router = APIRouter()

async def process_single_file(label: str, value: any):
    """Helper function to process a single uploaded file asynchronously."""
    try:
        # 1. Get images (Offload blocking I/O and conversion)
        images = await asyncio.to_thread(get_images_from_upload, value)
        
        if not images:
            return {
                "label_from_key": label,
                "filename": getattr(value, "filename", "unknown"),
                "error": "Image conversion failed or file was empty"
            }

        # 2. Extract Text (Offload CPU-bound OCR)
        text_lines = await asyncio.to_thread(extract_text_from_all_images, images)
        
        # 3. Parse fields (Offload CPU-bound parsing)
        analysis = await asyncio.to_thread(parse_extracted_text, text_lines)
        
        return {
            "label_from_key": label,
            "filename": value.filename,
            "status": "success" if text_lines else "no_text_found",
            "text_lines_count": len(text_lines),
            "analysis": analysis
        }
    except Exception as e:
        logging.error(f"Error processing {label}: {e}")
        return {
            "label_from_key": label,
            "filename": getattr(value, "filename", "unknown"),
            "error": str(e)
        }

@router.post("/ocr-reading")
async def process_documents(request: Request):
    try:
        form_data = await request.form()
        
        # Process documents sequentially to manage memory
        final_results = []
        for label, value in form_data.items():
            if hasattr(value, "filename") and value.filename:
                result = await process_single_file(label, value)
                final_results.append(result)

        if not final_results:
            return {"total_documents": 0, "documents": [], "message": "No files uploaded"}

        return {
            "total_documents": len(final_results),
            "documents": final_results
        }
        
    except Exception as e:
        logging.error(f"Global error in ocr-reading: {e}")
        raise HTTPException(status_code=500, detail=str(e))
