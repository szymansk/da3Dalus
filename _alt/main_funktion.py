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
from Airplane.AirplaneFactory import AirplaneFactory

from Airplane.Wing.WingFactory import WingFactory
#from Fluegel import fluegel
#from Rumpf import profil
from _alt.Einleseservice import einlesen
from stl_exporter.Exporter import *

import os
import Extra.Zipfolder as myZip
import urllib.request
from app import app
#from flask import Flask, request, redirect, jsonify, send_file
#from werkzeug.utils import secure_filename
import logging
from probe_rumps_cutout_2 import *

from Extra.ConstructionStepsViewer import ConstructionStepsViewer




def open_wing(filename):
	ein=einlesen()
	p1=profil()
	f2=fluegel()
	tigl_h=ein.cpacs_einlesen(filename)
	f2.make_fluegel(tigl_h)
	
	#p1.make_profil(tigl_h)
	#display, start_display, add_menu, add_function_to_menu = init_display()
	#display.DisplayShape(flugelfertig)
	#start_display()
	#display.FitAll()

def open_fuselage(filename):
	ein=einlesen()
	p1=profil()
	tigl_h=ein.cpacs_einlesen(filename)
	p1.make_profil(tigl_h)

def create_fuselage(filename):
	tigl_h= extract_tigl(filename)
	a=aircombat_test(True, tigl_h)
	a.test1()
    

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','xml','json'])

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_file(files):
    # check if the post request has the file part
	if 'file' not in files:
		resp = jsonify({'message' : 'No file part in the request'})
		resp.status_code = 400
		return resp
	file = files['file']

	if file.filename == '':
		resp = jsonify({'message' : 'No file selected for uploading'})
		resp.status_code = 400
		return resp
	return None
    
def extract_tigl(file_path):
	tixi_h = tixi3wrapper.Tixi3()
	tigl_h = tigl3wrapper.Tigl3()
	tixi_h.open(file_path)
	tigl_h.open(tixi_h, "")
	return tigl_h
 
@app.route('/create_airplane', methods=['POST'])
def create_right_wing():
	resp= check_file(request.files)
	if resp != None: 
		return resp
	else:
		file= request.files['file']
	
	if file and allowed_file(file.filename):
		filename = secure_filename(file.filename)
		file_path = "test_cpacs\\" + filename
		file.save(file_path)
		tigl_h= extract_tigl(file_path)
		'''
		wing_thikness=0.01
		rib_spacing=1
		rib_thikness=0.2
		'''
		wing_thikness=float(request.args.get("wing_thikness"))
		rib_spacing=float(request.args.get("rib_spacing"))
		rib_thikness=float(request.args.get("rib_thikness"))
		print("wing:",wing_thikness,"rib_s:" ,rib_spacing, "rib_t",rib_thikness)
		airplane_factory=AirplaneFactory(tigl_h,wing_thikness,rib_spacing,rib_thikness)
		airplane_factory.create_right_main_wing()
		return send_file("right_mainwing.stl")

	else:
		resp = jsonify({'message' : 'Allowed file types are txt, pdf, png, jpg, jpeg, gif'})
		resp.status_code = 400
		return resp


@app.route('/wing-upload', methods=['POST'])
def upload_wing():
    '''
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
	'''
    resp= check_file(request.files)
    if resp != None: 
        return resp
    else:
        file= request.files['file']

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = filename
        file.save(file_path)
        # resp = jsonify({'message' : 'File successfully uploaded'})
        # resp.status_code = 201
        open_wing(file_path)
        # return resp
        return send_file("p_right_mainwing.stl")

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
		#open_fuselage(file_path)
		create_fuselage(file_path)
		logging.debug("prepering to send zip")
		return send_file("stls\\fuselage.zip")

	else:
		resp = jsonify({'message' : 'Allowed file types are txt, pdf, png, jpg, jpeg, gif'})
		resp.status_code = 400
		return resp

def my_logging():
    #logging.basicConfig(filename='example.log', level=logging.INFO)
	logging.basicConfig(level=logging.INFO)
	logging.debug("Start logging")
    
def development():
	i_cpacs=1
	md=ConstructionStepsViewer.instance(True)
	tixi_h = tixi3wrapper.Tixi3()
	tigl_h = tigl3wrapper.Tigl3()
	if i_cpacs==1:
		tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_v2.xml")
	if i_cpacs==2:
		tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\CPACS_30_D150.xml")
	if i_cpacs==3:
		tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_skaliert_f38_one_profile.xml")
	if i_cpacs==4:
		tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\tinywing_skaliert.xml")
	tigl_h.open(tixi_h, "")
	shell_thikness=0.01
	fuselage_rib_spacing=1.5
	rib_spacing=4
	rib_thikness=0.2
	airplane_factory=AirplaneFactory(tigl_h,shell_thikness,fuselage_rib_spacing,rib_spacing,rib_thikness)
	#display, start_display, add_menu, add_function_to_menu = init_display()
	d_ribs=False
	variant=2 
	if variant==1:
		airplane_factory.create_airplane()
		airplane_factory.fuse_all_wings()
		#display.DisplayShape(airplane_factory.airplane.allwings)
		#display.DisplayShape(airplane_factory.airplane.fuselage)
	elif variant==2:
		airplane_factory.create_right_main_wing()
		#display.DisplayShape( airplane_factory.airplane.wings.get("right_mainwing"))
	elif variant==3:
		#airplane_factory.create_right_mainwing()
		airplane_factory.create_aircombat_fuselage()
		#display.DisplayShape(airplane_factory.airplane.fuselage, transparency=0.8)
		#display.DisplayShape(airplane_factory.rib_factory.rib.ribs)
		#try:
			#display_this_shape(airplane_factory.fuselage_factory.fuselage.with_ribs)
		#except:
			#logging.error("Not possible to display Fuselage with ribs")
	else:
		logging.debug("invalid variant")
  
	#if d_ribs:
		#display.DisplayShape(airplane_factory.rib_factory.rib.ribs)
  
	myZip.zip_stls()
	#box = BRepPrimAPI_MakeBox(1, 1, 1).Shape()
	#display.DisplayShape(box)

	#display.FitAll()
	#start_display()
	
	md.start()

def dev2():
	tigl_h= extract_tigl(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_v2.xml")
	a=aircombat_test(True, tigl_h)
	a.test1()
    
if __name__ == "__main__":
	my_logging()
	#development()
	dev2()
	#app.run()
	
	

    
