FROM python:3.11-slim

WORKDIR /app

COPY *.py ./
COPY mutate/ ./mutate/

COPY ./midpoint_binaries/ ./midpoint_binaries/
COPY ./midpoint_inputs/ ./midpoint_inputs/

RUN chmod +x ./midpoint_binaries/*

CMD ["python3", "main.py", "--binary=./midpoint_binaries", "--input=./midpoint_inputs"]