FROM python:3-alpine

ENV name unknown
ENV port 8342
ENV addr http://example.org
ENV directory /etc/switch

RUN cd /etc
RUN mkdir app
WORKDIR /etc/app
ADD *.py /etc/app/
ADD requirements.txt /etc/app/.
RUN pip install -r requirements.txt

CMD python /etc/app/switch_webthing.py $port $name $addr $directory


