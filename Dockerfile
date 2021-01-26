FROM debian:10

LABEL maintainer="dmintz"

RUN apt-get update
RUN apt-get install -y python3 python3-dev python3-pip nginx

COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt

COPY ./ /app
WORKDIR /app

RUN mkdir -p /app/logs


ENV WEBROOT='/'

ENTRYPOINT [ "python3" ]
EXPOSE 80
CMD [ "app.py" ]