from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.aeroplane import Aeroplane, Wing, WingXSec, ControlSurface, Fuselage, FuselageXSecSuperEllipse

# Create an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create all tables
Base.metadata.create_all(bind=engine)

# Create a session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Create a test aeroplane
aeroplane = Aeroplane(
    name="Test Aeroplane",
    xyz_ref=[0, 0, 0]
)

# Create a test wing
wing = Wing(
    name="Main Wing",
    symmetric=True
)

# Create test wing cross-sections
wing_xsec1 = WingXSec(
    xyz_le=[0, 0, 0],
    chord=0.18,
    twist=2,
    airfoil="./components/airfoil/naca0015.dat"
)

wing_xsec2 = WingXSec(
    xyz_le=[0.01, 0.5, 0],
    chord=0.16,
    twist=0,
    airfoil="./components/airfoil/naca0015.dat"
)

# Create a test control surface
control_surface = ControlSurface(
    name="Aileron",
    hinge_point=0.8,
    symmetric=False,
    deflection=5
)

# Create a test fuselage
fuselage = Fuselage(
    name="Fuselage"
)

# Create test fuselage cross-sections
fuselage_xsec1 = FuselageXSecSuperEllipse(
    xyz=[0, 0, 0],
    a=0.5,
    b=0.5,
    n=2
)

fuselage_xsec2 = FuselageXSecSuperEllipse(
    xyz=[0.01, 0.5, 0],
    a=0.6,
    b=0.4,
    n=1.5
)

# Add relationships
wing_xsec1.control_surface = control_surface
wing.x_secs.append(wing_xsec1)
wing.x_secs.append(wing_xsec2)
fuselage.x_secs.append(fuselage_xsec1)
fuselage.x_secs.append(fuselage_xsec2)
aeroplane.wings.append(wing)
aeroplane.fuselages.append(fuselage)

# Add to session and commit
db.add(aeroplane)
db.commit()

# Query to verify
aeroplane_from_db = db.query(Aeroplane).filter(Aeroplane.name == "Test Aeroplane").first()
print(f"Aeroplane UUID: {aeroplane_from_db.uuid}")
print(f"Aeroplane name: {aeroplane_from_db.name}")
print(f"Aeroplane xyz_ref: {aeroplane_from_db.xyz_ref}")
print(f"Number of wings: {len(aeroplane_from_db.wings)}")
print(f"Number of fuselages: {len(aeroplane_from_db.fuselages)}")
print(f"Wing name: {aeroplane_from_db.wings[0].name}")
print(f"Number of wing cross-sections: {len(aeroplane_from_db.wings[0].x_secs)}")
print(f"Control surface name: {aeroplane_from_db.wings[0].x_secs[0].control_surface.name}")
print(f"Fuselage name: {aeroplane_from_db.fuselages[0].name}")
print(f"Number of fuselage cross-sections: {len(aeroplane_from_db.fuselages[0].x_secs)}")

# Close session
db.close()
