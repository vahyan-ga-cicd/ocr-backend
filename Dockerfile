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

# Set the command for the Lambda handler
CMD [ "app.main.handler" ]
