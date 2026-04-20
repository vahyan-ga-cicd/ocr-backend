from fastapi import APIRouter, Request, HTTPException, UploadFile
from app.utils.file_handler import get_images_from_upload
from app.service.ocr_service import extract_text_from_all_images
from app.service.parser_engine import parse_extracted_text
import logging

router = APIRouter()

@router.post("/ocr-reading")
async def process_documents(request: Request):
    try:
        form_data = await request.form()
        final_results = []
        
        for label, value in form_data.items():
            if hasattr(value, "filename") and value.filename:
                # 1. Get images (and check if they exist)
                images = get_images_from_upload(value)
                
                if not images:
                    final_results.append({
                        "label_from_key": label,
                        "filename": value.filename,
                        "error": "Image conversion failed or file was empty"
                    })
                    continue

                # 2. Extract Text
                text_lines = extract_text_from_all_images(images)
                
                # 3. Parse fields
                analysis = parse_extracted_text(text_lines)
                
                final_results.append({
                    "label_from_key": label,
                    "filename": value.filename,
                    "status": "success" if text_lines else "no_text_found",
                    "text_lines_count": len(text_lines),
                    "analysis": analysis
                })

        return {
            "total_documents": len(final_results),
            "documents": final_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
