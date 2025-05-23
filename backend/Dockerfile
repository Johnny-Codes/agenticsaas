FROM python:3.12

WORKDIR /app

COPY requirements.txt .
# RUN pip install -r --no-cache-dir requirements.txt
RUN pip install -r requirements.txt

COPY . .

# Copy the entrypoint script and make it executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
# The CMD will be passed as arguments to the entrypoint script
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
