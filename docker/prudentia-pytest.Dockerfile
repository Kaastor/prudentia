FROM python:3.12-slim
RUN python -m pip install --no-cache-dir "pytest>=8" "pytest-json-report>=1.5"
WORKDIR /workspace
