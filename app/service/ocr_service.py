import os


from paddleocr import PaddleOCR
import numpy as np
import logging


import threading

_ocr_engine = None
_ocr_lock = threading.Lock()

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        with _ocr_lock:
            if _ocr_engine is None:
                _ocr_engine = PaddleOCR(
                    use_angle_cls=True, 
                    lang='en',
                    use_gpu=False,
                    det_model_dir='/tmp/.paddleocr/det',
                    rec_model_dir='/tmp/.paddleocr/rec',
                    cls_model_dir='/tmp/.paddleocr/cls'
                )
    return _ocr_engine


def extract_text_from_memory_image(img_array: np.ndarray) -> list[str]:
   
    try:
      
        if img_array.dtype != np.uint8:
            img_array = img_array.astype(np.uint8)

        logging.info(f"Processing image with shape: {img_array.shape}")
        
        
        result = get_ocr_engine().ocr(img_array)
        
        extracted_lines = []
        if result and len(result) > 0 and result[0] is not None:
            for line in result[0]:
                text = line[1][0]
                extracted_lines.append(text)
        
        logging.info(f"Extracted {len(extracted_lines)} lines of text.")
        return extracted_lines
    except Exception as e:
        logging.error(f"Error during OCR extraction: {e}")
        return []

def extract_text_from_all_images(images: list[np.ndarray]) -> list[str]:
    
    all_text = []
    for img in images:
        all_text.extend(extract_text_from_memory_image(img))
    return all_text
