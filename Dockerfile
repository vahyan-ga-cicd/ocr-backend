# Use the AWS Lambda Python 3.9 base image
FROM public.ecr.aws/lambda/python:3.9

# Install system dependencies for PaddleOCR and OpenCV
# we need mesa-libGL, libX11, libgomp, and BUILD TOOLS (gcc) for pymupdf
RUN yum install -y \
    mesa-libGL \
    libX11 \
    libXext \
    libXrender \
    libgomp \
    gcc \
    gcc-c++ \
    make \
    && yum clean all

# Upgrade pip and build tools to ensure we find wheels
RUN pip install --upgrade pip setuptools wheel

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
# We use --no-cache-dir to keep the image size small
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Pre-download PaddleOCR models to avoid runtime downloads and save RAM
# We download det, rec, and cls models for English
RUN mkdir -p /root/.paddleocr/whl/det/en/en_PP-OCRv3_det_infer \
    && mkdir -p /root/.paddleocr/whl/rec/en/en_PP-OCRv4_rec_infer \
    && mkdir -p /root/.paddleocr/whl/cls/ch_ppocr_mobile_v2.0_cls_infer \
    && python3 -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='en', show_log=False)"

# Set the command for the Lambda handler
CMD [ "app.main.handler" ]
