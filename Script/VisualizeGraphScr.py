# Add path to the Class folder. All classes can now be imported directly
from sys import path
from os import getcwd

from networkx.drawing.layout import planar_layout
path.append(getcwd() + "/../Class")
from CurriculumGraph import CurriculumGraph

# import plotting utils
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt

# Load additional libraries
import networkx as nx
import numpy as np
import pandas as pd

# Instantiate the class and useful variables.

cg = CurriculumGraph(r'../Data/FrequencyListOfTopics.xlsx')

# Adjacency = cg.Adjacency
# LeastDistance = cg.LeastDistance
# Route = cg.Route

# Show path from first to second argument
cg.PrintPath('1','370')

# Show graph
# nx.draw_kamada_kawai(cg.Graph, labels = cg.LabelDict, with_labels = True)
# plt.show()