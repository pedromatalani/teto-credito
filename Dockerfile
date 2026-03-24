FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN mkdir -p /data
ENV PORT=10000
EXPOSE 10000
CMD ["python3", "server.py"]
