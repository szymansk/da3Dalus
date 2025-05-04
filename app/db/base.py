
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy import Column, Integer

@as_declarative()
class Base:
    id = Column(Integer, primary_key=True, index=True)

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

# Import all models here so they are registered with Base
#from app.models.aeroplane import Aeroplane, Wing, WingXSec, ControlSurface, Fuselage, FuselageXSecSuperEllipse
