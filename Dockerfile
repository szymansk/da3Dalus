FROM adesso-cis1-ba-lm-dev01.test-server.ag:4567/da3dalus/cad-modelling-service/conda-base:latest

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=main_funktion.py
ENV FLASK_ENV=development

ENTRYPOINT [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
