from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "postgresql://myuser:mypass@localhost:5432/mydb"  # <-- используешь localhost, если работаешь не из docker-контейнера!

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
