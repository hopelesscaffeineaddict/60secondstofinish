FROM python:3.11-slim

WORKDIR /app

COPY *.py ./
COPY mutate/ ./mutate/

ENTRYPOINT ["python3", "main.py", "--binary=binaries", "--input=example_inputs"]
