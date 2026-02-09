import sys
from pathlib import Path


print('python:', sys.version)

import multimethod
print('multimethod: ok')

import nlopt
print('nlopt: ok', getattr(nlopt, '__version__', 'unknown'))

import vtk
print('vtk:', vtk.vtkVersion.GetVTKVersion())

import cadquery as cq
print('cadquery: ok', getattr(cq, '__version__', 'unknown'))

from OCP.gp import gp_Pnt
print('OCP: ok')

import aerosandbox as asb
print('aerosandbox: ok', getattr(asb, '__version__', 'unknown'))

import fastapi_mcp as mcp
print('fastapi_mcp: ok', getattr(mcp, '__version__', 'unknown'))

import ocp_vscode 
print('ocp_vscode: ok', getattr(ocp_vscode, '__version__', 'unknown'))

import plotly.express as px
fig = px.scatter(x=[1,2,3], y=[4,5,6])
fig.write_image("test.png")
print("plotly write_image: ok")
