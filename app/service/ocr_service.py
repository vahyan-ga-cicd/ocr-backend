import gc
import threading
import cv2
import logging
import numpy as np
from paddleocr import PaddleOCR

import os

# Set HOME to /tmp for Lambda to ensure PaddleOCR has a writable directory for models
if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    os.environ['HOME'] = '/tmp'

_ocr_engine = None
_ocr_lock = threading.Lock()
_ocr_execution_lock = threading.Lock()

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        with _ocr_lock:
            if _ocr_engine is None:
                # Optimized for AWS Lambda (Memory & Latency)
                _ocr_engine = PaddleOCR(
                    use_angle_cls=True, 
                    lang='en',
                    use_gpu=False,
                    use_onnx=False,
                    det_model_dir='/opt/paddle_models/det/en/en_PP-OCRv3_det_infer',
                    rec_model_dir='/opt/paddle_models/rec/en/en_PP-OCRv4_rec_infer',
                    cls_model_dir='/opt/paddle_models/cls/ch_ppocr_mobile_v2.0_cls_infer',
                    det_limit_side_len=800,
                    det_limit_type='max',
                    cpu_threads=2,
                    show_log=False
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
