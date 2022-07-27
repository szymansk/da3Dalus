FROM python:3.7-slim

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_ENV=development

ENTRYPOINT [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
