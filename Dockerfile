FROM python:3.9
RUN pip install pipenv
COPY Pipfile* ./
RUN pipenv install --system
COPY src src/
CMD python -m src