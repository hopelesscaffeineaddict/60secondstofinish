# Start from a default ubuntu image.
FROM ubuntu:22.04

# Copy/Compile my fuzzer
COPY 60secondstofinish /
RUN chmod +x /60secondstofinish

# Run it.
CMD ["/bin/bash", "/60secondstofinish"]

