import cv2
import numpy as np
import fitz  # PyMuPDF
from fastapi import UploadFile


def _resize_image_to_target(img: np.ndarray, max_dim: int = 800) -> np.ndarray:
    """Helper to resize image while maintaining aspect ratio if it exceeds max_dim."""
    h, w = img.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return img


def get_images_from_upload(upload_file: UploadFile) -> list:
   
    upload_file.file.seek(0)
    file_bytes = upload_file.file.read()
    
    if len(file_bytes) == 0:
        return []

    is_pdf = upload_file.filename.lower().endswith('.pdf')
    images = []
    
    try:
        if is_pdf:
            # Convert PDF to images using PyMuPDF (fitz) at 90 DPI (Aggressive optimization for memory)
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            matrix = fitz.Matrix(90 / 72, 90 / 72)
            
            for page in doc:
                pix = page.get_pixmap(matrix=matrix)
                # Convert pixmap to numpy array (RGB)
                img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                # Resize if it's still too large (e.g. very large page size)
                img_data = _resize_image_to_target(img_data)
                images.append(img_data)
            doc.close()
        else:
            # Open CV logic for images
            nparr = np.frombuffer(file_bytes, np.uint8)
            img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img_bgr is not None:
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                # Resize for optimization
                img_rgb = _resize_image_to_target(img_rgb)
                images.append(img_rgb)
    except Exception as e:
        print(f"Error processing document: {e}")
        return []
        
    return images
