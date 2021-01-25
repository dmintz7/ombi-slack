FROM debian:10

LABEL maintainer="dmintz"

RUN apt-get update
RUN apt-get install -y python3 python3-dev python3-pip nginx
RUN pip3 install uwsgi

# We copy just the requirements.txt first to leverage Docker cache
COPY ./ /app
WORKDIR /app

RUN mkdir -p /app/logs

RUN pip3 install -r requirements.txt

ENV WEBROOT='/'

ENTRYPOINT [ "python3" ]
EXPOSE 80
CMD [ "app.py" ]