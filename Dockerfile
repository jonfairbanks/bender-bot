FROM python:3.9-alpine as base

RUN pip install --upgrade pip

RUN adduser -D worker
USER worker
WORKDIR /home/worker

ENV PATH="/home/worker/.local/bin:${PATH}"
RUN pip install --user pipenv

COPY --chown=worker:worker Pipfile Pipfile
RUN pipenv lock && pipenv requirements > requirements.txt
RUN pip install --user -r requirements.txt

COPY --chown=worker:worker . .

CMD ["python", "index.py"]