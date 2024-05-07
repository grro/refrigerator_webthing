FROM python:3-alpine

ENV port 8342
ENV addr http://example.org
ENV directory /etc/refrigerator

RUN cd /etc
RUN mkdir app
WORKDIR /etc/app
ADD *.py /etc/app/
ADD requirements.txt /etc/app/.
RUN pip install -r requirements.txt

CMD python /etc/app/refrigerator_webthing.py $port $addr $directory


