import gc
import threading
import cv2
import logging
import numpy as np
from paddleocr import PaddleOCR

_ocr_engine = None
_ocr_lock = threading.Lock()
_ocr_execution_lock = threading.Lock() # Lock for thread-safe OCR calls

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
                    cls_model_dir='/tmp/.paddleocr/cls',
                    det_limit_side_len=960, # Standard size, uses significantly less RAM than 1300/1500
                    det_limit_type='max',
                    cpu_threads=2 # Keep threads low to prevent memory overhead
                )
    return _ocr_engine


def extract_text_from_memory_image(img_array: np.ndarray) -> list[str]:
    try:
        if img_array.dtype != np.uint8:
            img_array = img_array.astype(np.uint8)

        # (Resizing is already handled in file_handler.py to target 960px)

        # PaddleOCR .ocr() call (Wrapped in lock as it's typically not thread-safe)
        with _ocr_execution_lock:
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
    try:
        for img in images:
            all_text.extend(extract_text_from_memory_image(img))
        return all_text
    finally:
        # Explicitly trigger garbage collection after processing a batch of images
        gc.collect()
