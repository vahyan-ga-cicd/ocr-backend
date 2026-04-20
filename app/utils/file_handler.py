import cv2
import numpy as np
from fastapi import UploadFile
from pdf2image import convert_from_bytes


def get_images_from_upload(upload_file: UploadFile) -> list:
   
    upload_file.file.seek(0)
    file_bytes = upload_file.file.read()
    
    if len(file_bytes) == 0:
        return []

    is_pdf = upload_file.filename.lower().endswith('.pdf')
    images = []
    
    try:
        if is_pdf:
            try:
                # Convert PDF to images using pdf2image
                pil_images = convert_from_bytes(file_bytes)
                for img in pil_images:
                    # Convert PIL images to NumPy arrays for PaddleOCR
                    images.append(np.array(img))
            except Exception as e:
                print(f"PDF processing failed (likely missing Poppler): {e}")
                raise Exception("PDF processing is currently unavailable on this environment. Please upload images (.jpg, .png) instead.")
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
