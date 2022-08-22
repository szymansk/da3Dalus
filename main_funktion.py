#!/usr/bin/env python
# coding: utf-8

# In[1]:


from __future__ import print_function

from tigl3.tigl3wrapper import Tigl3, TiglBoolean
from tixi3.tixi3wrapper import Tixi3
import sys

from tigl3.geometry import CTiglTransformation

import tigl3.configuration, tigl3.geometry, tigl3.boolean_ops, tigl3.exports
from OCC.Core.Quantity import Quantity_NOC_RED
import os

import tigl3.curve_factories
import tigl3.surface_factories
from OCC.Core.gp import gp_Pnt, gp_OX, gp_OY,gp_OZ, gp_Vec, gp_Trsf, gp_DZ, gp_Ax2, gp_Ax3, gp_Pnt2d, gp_Dir2d, gp_Ax2d, gp_Dir
from OCC.Core.gp import gp_Ax1, gp_Pnt, gp_Dir, gp_Trsf
from OCC.Display.SimpleGui import init_display

from OCC.Display.WebGl.jupyter_renderer import JupyterRenderer
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeEdge
from OCC.Core.GC import GC_MakeArcOfCircle, GC_MakeSegment
from OCC.Core.GCE2d import GCE2d_MakeSegment
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeBox

from OCC.Core.BRep import BRep_Tool_Surface, BRep_Builder
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCC.Core.TopoDS import topods, TopoDS_Edge, TopoDS_Compound
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCC.Core.TopTools import TopTools_ListOfShape

from OCC.Core.BOPAlgo import BOPAlgo_MakerVolume

from OCC.Core.BRepOffset import BRepOffset_Skin
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakeThickSolid, BRepOffsetAPI_ThruSections

from OCC.Core.BRepFeat import (
	BRepFeat_MakePrism,
	BRepFeat_MakeDPrism,
	BRepFeat_SplitShape,
	BRepFeat_MakeLinearForm,
	BRepFeat_MakeRevol,
)

from OCC.Core.Geom import Geom_CylindricalSurface, Geom_Plane, Geom_Surface
from OCC.Core.Geom2d import Geom2d_TrimmedCurve, Geom2d_Ellipse, Geom2d_Curve

from OCC.Core.TopoDS import TopoDS_Shell, TopoDS_Solid, TopoDS_Wire, TopoDS_Edge
from OCC.Core import StlAPI

import numpy as np

from OCC.Core.BRepAlgoAPI import (
	BRepAlgoAPI_Fuse,
	BRepAlgoAPI_Common,
	BRepAlgoAPI_Section,
	BRepAlgoAPI_Cut,
)

from OCC.Extend.TopologyUtils import TopologyExplorer
from OCC.Extend.ShapeFactory import translate_shp

from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop_VolumeProperties, brepgprop_SurfaceProperties


from tixi3 import tixi3wrapper
from tigl3 import tigl3wrapper
import tigl3.configuration, tigl3.geometry, tigl3.boolean_ops, tigl3.exports

from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.Bnd import Bnd_Box
from tigl3.geometry import CTiglTransformation
import tigl3.geometry as TGeo
from OCC.Core.Quantity import Quantity_NOC_RED
import os

from math import radians
from AirplaneFactory import AirplaneFactory

from WingFactory import WingFactory

builder = BRep_Builder()
shell = TopoDS_Shell()
builder.MakeShell(shell)


#import sys

#sys.path.append("C:/Users/motto/cad-modelling-service")



from Fluegel import fluegel
from Rumpf import profil
from Einleseservice import einlesen
from Ausgabeservice import *

import os
import urllib.request
from app import app
from flask import Flask, request, redirect, jsonify, send_file
from werkzeug.utils import secure_filename

def open_wing(filename):
	ein=einlesen()
	p1=profil()
	f2=fluegel()
	tigl_h=ein.cpacs_einlesen(filename)
	f2.make_fluegel(tigl_h)
	p1.make_profil(tigl_h)
	#display, start_display, add_menu, add_function_to_menu = init_display()
	#display.DisplayShape(flugelfertig)
	#start_display()
	#display.FitAll()

def open_fuselage(filename):
	ein=einlesen()
	p1=profil()
	tigl_h=ein.cpacs_einlesen(filename)
	p1.make_profil(tigl_h)

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','xml','json'])

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/wing-upload', methods=['POST'])
def upload_wing():
	# check if the post request has the file part
	if 'file' not in request.files:
		resp = jsonify({'message' : 'No file part in the request'})
		resp.status_code = 400
		return resp
	file = request.files['file']

	if file.filename == '':
		resp = jsonify({'message' : 'No file selected for uploading'})
		resp.status_code = 400
		return resp

	if file and allowed_file(file.filename):
		filename = secure_filename(file.filename)
		file_path = filename
		file.save(file_path)
		# resp = jsonify({'message' : 'File successfully uploaded'})
		# resp.status_code = 201
		open_wing(file_path)
		# return resp
		return send_file("fluegel.stl")

	else:
		resp = jsonify({'message' : 'Allowed file types are txt, pdf, png, jpg, jpeg, gif'})
		resp.status_code = 400
		return resp

@app.route('/fuselage-upload', methods=['POST'])
def upload_fuselage():
	# check if the post request has the file part
	if 'file' not in request.files:
		resp = jsonify({'message' : 'No file part in the request'})
		resp.status_code = 400
		return resp
	file = request.files['file']

	if file.filename == '':
		resp = jsonify({'message' : 'No file selected for uploading'})
		resp.status_code = 400
		return resp

	if file and allowed_file(file.filename):
		filename = secure_filename(file.filename)
		file_path = filename
		file.save(file_path)
		# resp = jsonify({'message' : 'File successfully uploaded'})
		# resp.status_code = 201
		open_fuselage(file_path)
		# return resp
		return send_file("rumpf.stl")

	else:
		resp = jsonify({'message' : 'Allowed file types are txt, pdf, png, jpg, jpeg, gif'})
		resp.status_code = 400
		return resp

if __name__ == "__main__":
	#open_file("C:/uploads/D150_v30.xml")
	#open_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))
	#app.run()
	tixi_h = tixi3wrapper.Tixi3()
	tigl_h = tigl3wrapper.Tigl3()
	#tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\fluegel_test_1008.xml")
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\CPACS_30_D150.xml")
	tigl_h.open(tixi_h, "")
	wing_thikness=0.01
	rib_spacing=4
	rib_thikness=0.2
	airplane_factory=AirplaneFactory(tigl_h,wing_thikness,rib_spacing,rib_thikness)
	airplane_factory.create_airplane()
	airplane_factory.fuse_all_wings()
	
	box = BRepPrimAPI_MakeBox(1, 1, 1).Shape()
	box2 = BRepPrimAPI_MakeBox(1, 1, 1).Shape()
	trafo= TGeo.CTiglTransformation()
	#trafo.add_translation(0,wf.wing.rib.height,0)
	#box2=trafo.transform(box2)
	display, start_display, add_menu, add_function_to_menu = init_display()
	display.DisplayShape(airplane_factory.airplane.allwings)
	#display.DisplayShape(wf.wing.rib.ribs)
	display.DisplayShape(box)
	display.DisplayShape(box2)
	start_display()
	display.FitAll()
