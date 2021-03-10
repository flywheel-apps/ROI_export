FROM python:3.7

ENV FLYWHEEL /flywheel/v0
RUN mkdir -p $FLYWHEEL

# Install external dependencies 
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY run.py $FLYWHEEL
COPY manifest.json $FLYWHEEL
COPY utils/load_data.py $FLYWHEEL
COPY utils/import_data.py $FLYWHEEL
COPY utils/flywheel_helpers.py $FLYWHEEL
COPY utils/mapping_class.py $FLYWHEEL


