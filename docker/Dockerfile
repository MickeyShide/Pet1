FROM python:3.14-slim

WORKDIR /var/www

ENV PYTHONPATH=/var/www

RUN python -m pip install --upgrade pip wheel setuptools

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt --root-user-action=ignore

COPY . .

EXPOSE 4000

ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["app.main:app", "--host", "0.0.0.0", "--port", "4000"]
