FROM python:3.8-slim-buster

WORKDIR /hrc2readerforweb

# Install production dependencies.
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Install tesseract and its dependencies
RUN apt-get update -qqy && apt-get install -qqy \
    tesseract-ocr \
    libtesseract-dev \
    tesseract-ocr-eng

# Set the TESSDATA_PREFIX environment variable
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/
ENV PATH="$PATH:/usr/bin/tesseract"

COPY . .

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
CMD [ "python3", "app.py" ]