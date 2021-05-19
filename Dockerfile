FROM python:3.7

ENV FLYWHEEL /flywheel/v0
RUN mkdir -p $FLYWHEEL

# Install external dependencies 
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt


COPY run.py $FLYWHEEL
COPY manifest.json $FLYWHEEL
COPY utils $FLYWHEEL/utils



