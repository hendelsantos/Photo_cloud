from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base

class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    album = Column(String)
    user_name = Column(String)
    upload_time = Column(DateTime, default=datetime.utcnow)

class TotalPhotos(Base):
    __tablename__ = "total_photos"
    id = Column(Integer, primary_key=True, index=True)
    count = Column(Integer, default=0)
