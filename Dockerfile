# Use the official Python base image
FROM python:3.12.1-slim
RUN apt-get update \
    && apt-get install -y gcc libc-dev
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt --verbose
COPY . .
EXPOSE 8000

# ENVIRONMENT VARIABLES
ENV DATABASE_URL=postgresql+asyncpg://kuanggy:712211@localhost:5432/restaurant_recommmendation
ENV MLFLOW_URI=runs:/20667a37d29345be907ccc4007dd9978/recommend
ENV MLFLOW_ARTIFACT_PATH=file:///Users/kuangsmacbook/Desktop/Works/LINEMAN\ MLE/attachment/mlruns/

# Start the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
