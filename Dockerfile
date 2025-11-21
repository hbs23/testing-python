FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
#COPY .env .   # kalau local only, kalau CI hapus

EXPOSE 9500

CMD ["python", "app.py"]