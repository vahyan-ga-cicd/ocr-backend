import cv2
import numpy as np
import fitz  # PyMuPDF
from fastapi import UploadFile


def get_images_from_upload(upload_file: UploadFile) -> list:
   
    upload_file.file.seek(0)
    file_bytes = upload_file.file.read()
    
    if len(file_bytes) == 0:
        return []

    is_pdf = upload_file.filename.lower().endswith('.pdf')
    images = []
    
    try:
        if is_pdf:
            # Convert PDF to images using PyMuPDF (fitz)
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                pix = page.get_pixmap()
                # Convert pixmap to numpy array (RGB)
                img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                # PaddleOCR works with RGB, so we can append directly
                images.append(img_data)
            doc.close()
        else:
            # --- OPEN CV LOGIC ---
            # 1. Convert bytes to a 1D numpy array
            nparr = np.frombuffer(file_bytes, np.uint8)
            # 2. Decode the array into an image (OpenCV reads as BGR)
            img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img_bgr is not None:
                # 3. Convert BGR to RGB 
                
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                # img_rgb = cv2.resize(img_rgb, (1024, 1024))
                images.append(img_rgb)
    except Exception as e:
        print(f"Error processing image with OpenCV: {e}")
        return []
        
    return images
