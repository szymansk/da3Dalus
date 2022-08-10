FROM continuumio/miniconda3:latest

RUN conda install -yc dlr-sc tigl3
RUN conda install -c conda-forge pythreejs

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=main_funktion.py
ENV FLASK_ENV=development

ENTRYPOINT [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
