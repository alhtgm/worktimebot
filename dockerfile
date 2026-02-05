FROM python:3.14.3

WORKDIR /usr/src/app

COPY . .

CMD ["python", "./mainbot.py"]
