FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc

ENTRYPOINT ["python3", "main.py", "--binary=./binaries", "--input=./example_inputs"]
