FROM python:3.9.17-slim-bookworm

# set environment variables
ENV PYTHONUNBUFFERED 1
ENV DEBUG 0

# set base directory
WORKDIR /app
ENV PYTHONPATH /app

# upgrade pip version
RUN pip install --upgrade pip

# install requirements.txt
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# copy project files
COPY . .