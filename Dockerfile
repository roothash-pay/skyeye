FROM python:3.12
ENV PYTHONUNBUFFERED 1

WORKDIR /app
ADD . /app

COPY ./scripts /app/skyeye/scripts

# Install system dependencies for monitoring and debugging
RUN apt-get update && \
    apt-get install -y vim redis-tools jq && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt
EXPOSE 8201
CMD ["gunicorn", "skyeye.wsgi:application", "--bind", "0.0.0.0:8201"]
