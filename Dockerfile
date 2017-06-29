FROM python:3.6-slim

RUN apt-get update && apt-get -y upgrade && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


RUN pip install --upgrade pip setuptools wheel
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade --process-dependency-links -r /tmp/requirements.txt && \
    rm -rf /root/.cache /tmp/* /var/tmp/*

ADD . ./iloop-to-model
WORKDIR iloop-to-model

ENV PYTHONPATH $PYTHONPATH:/iloop-to-model

ENTRYPOINT ["gunicorn"]
CMD ["-w", "4", "-b", "0.0.0.0:7000", "-t", "150", "-k", "aiohttp.worker.GunicornWebWorker", "iloop_to_model.app:app"]
