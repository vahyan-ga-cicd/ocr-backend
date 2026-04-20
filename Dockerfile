# Use the AWS Lambda Python 3.9 base image
FROM public.ecr.aws/lambda/python:3.9

# Install system dependencies for PaddleOCR and OpenCV
# we need mesa-libGL, libX11, and libgomp
RUN yum install -y \
    mesa-libGL \
    libX11 \
    libXext \
    libXrender \
    libgomp \
    && yum clean all

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
# We use --no-cache-dir to keep the image size small
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Set the command for the Lambda handler
CMD [ "app.main.handler" ]
