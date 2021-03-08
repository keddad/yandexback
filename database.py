from sqlalchemy import create_engine, engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+psycopg2://postgres:password@localhost:5432/"

engine = create_engine(DATABASE_URL)
LocalSession = sessionmaker(bind=engine)

Base = declarative_base()