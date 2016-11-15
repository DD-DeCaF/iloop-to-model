FROM python:3.5

ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt

ADD . ./iloop-to-model
WORKDIR iloop-to-model

ENV PYTHONPATH $PYTHONPATH:/iloop-to-model

ENTRYPOINT ["gunicorn"]
CMD ["-w", "4", "-b", "0.0.0.0:7000", "-t", "150", "-k", "aiohttp.worker.GunicornWebWorker", "iloop_to_model.app:app"]