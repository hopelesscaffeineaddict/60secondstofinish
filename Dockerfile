FROM python:3.11-slim

WORKDIR /app

COPY *.py ./
COPY mutate/ ./mutate/

COPY harness.c .
RUN apt-get update && apt-get install -y gcc
RUN gcc harness.c -o harness

ENTRYPOINT ["python3", "main.py", "--binary=/binaries", "--input=/example_inputs"]
