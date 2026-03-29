# Build stage
FROM python:3.14 AS builder

RUN apt-get update && apt-get install python3-dev gcc libc-dev make cmake -y
RUN pip install --upgrade pip
RUN pip install pipenv

WORKDIR /app
COPY ./src/Pipfile* ./
RUN pipenv lock && pipenv requirements > requirements.txt
RUN pip install --no-cache-dir -r requirements.txt --prefix=/install

#
# ----------------------------------------------------------------------
#

# Final stage
FROM python:3.14

# Don't generate .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turn off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Copy only the installed packages from the build stage
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=nobody:nogroup ./src .

# Force install certifi
RUN pip install certifi

# Force install filelock
RUN pip install filelock
RUN pip install --user filelock

USER nobody

CMD ["python", "index.py"]
