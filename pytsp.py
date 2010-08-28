#!/usr/bin/env python
# encoding: utf-8
"""
pytsp.py

Created by maurizio on 2010-05-02.
Copyright (c) 2010 Maurizio Leo. All rights reserved.
"""

import os
import re
import time
import itertools
#from subprocess import call
import subprocess, shlex
from random import randrange
import matplotlib.path as mpath
import matplotlib.pyplot as plt

acoWestCmd = "../ACOTSP.V1.0/acotsp -i ch150_west.tsp -m 100 -b 5 -r 1 -v -l 3"
acoEastCmd = "../ACOTSP.V1.0/acotsp -i ch150_east.tsp -m 100 -b 5 -r 1 -v -l 3"

acoCityFile = "./ch150.tsp"
westCityFile = "./ch150_west.tsp"
eastCityFile = "./ch150_east.tsp"

westSolnFile = "../ACOTSP.V1.0/stat.ch150_west.tsp"
eastSolnFile = "../ACOTSP.V1.0/stat.ch150_east.tsp"

class TrashCan:
	def __init__(self, index, xcoord, ycoord):
		self.index = index
		self.xcoord = float(xcoord)
		self.ycoord = float(ycoord)
		
	def __str__(self):
		return "%s %s %s" % (self.index, self.xcoord, self.ycoord)
	
	def __cmp__(self, other):
		return cmp(self.index, other.index)
		
class Tour:
	"""A list of trash cans with overall tour length"""
	def __init__(self, trashCanList, tourLen):
		self.trashCanList = trashCanList
		self.tourLen = int(tourLen)

def parseACOTrashCanFile(filename):
	"""
	Return a list of TrashCans
	"""
	cities = []
	
	f = open(filename, "r")
	f.readline()
	f.readline()
	f.readline()
	f.readline()
	f.readline()
	f.readline()
	
	# Parse the city can info (e.g. index<space>xcoord<space>ycoord)
	for line in f:
		m = re.search(r'^(.*?)\s(.*?)\s(.*?)$', line)

		if m is None:
			continue
			
		index = m.group(1)
		xcoord = m.group(2)
		ycoord = m.group(3)
		c = TrashCan(index, xcoord, ycoord)
	
		cities.append(c)
	
	f.close()
	return cities

def parseACOSolutionFile(filename):
	""" Return a Tour """
	tourList = []
	f = open(filename, "r")

	# Discard all extra information till we get to the solution
	line = ""
	while re.match(r'^Best solution', line) is None:
		line = f.readline()

	# Get the length of this best tour
	tourLen = f.readline().strip()

	# Read in cities in the best tour solution (e.g. index<space>xcoord<space>ycoord)
	for line in f:
		m = re.search(r'(.*?)\s(.*?)\s(.*?)$', line)
		xc = float(m.group(2))
		
		# The "amazing" provided ACO code will output erroneous can locations because
		# the DIMENSION of the input file must be larger than 75 (so a bunch of cans
		# with 0 value must be removed).
		if xc > 0:
			tourList.append(TrashCan(m.group(1), m.group(2), m.group(3)))

	f.close()	
	return Tour(tourList, tourLen)

def outputACOTrashCanFile(trashCanList, filename):
	if len(trashCanList) == 0:
		raise Exception("Trash can list cannot be empty when outputting file")
	
	f = open(filename, "w")
	
	# Write the standard TSP file header
	f.write("NAME: %s\n" % filename.strip("./"))
	f.write("TYPE: TSP\n")
	f.write("COMMENT: Leo's File\n")

	# HACK: Has to be set something high like 150 to prevent "amazing" ACO code from crashing.
	# f.write("DIMENSION: " + str(len(trashCanList)) + "\n")
	f.write("DIMENSION: 150\n")
	
	f.write("EDGE_WEIGHT_TYPE: EUC_2D\n")
	f.write("NODE_COORD_SECTION\n")
	
	# Write the cans to the output file.
	for tc in trashCanList:
		f.write("%s\n" % tc)
	
	f.write("EOF\n")
	f.close()

def plotMap():
	fig = plt.figure(figsize=(12, 12))
	ax = fig.add_subplot(111)
	ax.grid()
	ax.set_xlim(0, 700)
	ax.set_ylim(0, 700)
	ax.set_title('Trash Can Locations')
	ax.set_xlabel('East -->')
	ax.set_ylabel('North -->')
	
	# Plot a line indicating East and West
	ax.plot([345, 345], [700, 0], 'g--')

	# Legend
	# ax.legend([line], ['Optimal Tour', length], 'upper right', shadow=True)
	
	return ax;

def plotTrashCanLocations(axes, markerString, trashCanList):
	"""Plot a list of points on the graph representing trash cans"""

	# Plot the cities as markers on the map (West = blue markers, East = red markers)
	for tc in trashCanList:
		axes.plot(tc.xcoord, tc.ycoord, markerString, markersize=9)
#		axes.annotate(tc.index, (tc.xcoord, tc.ycoord))

def plotTrashCanTour(axes, tour):
	"""Plot a tour with points and connecting lines"""
	if len(tour.trashCanList) == 0:
		raise Exception("Trash can list cannot be empty when plotting")

	Path = mpath.Path
	pathdata = []
	i = 0
	startTrashCan = tour.trashCanList[0]

	for tc in tour.trashCanList:
		if i == 0:
			pathdata.append((Path.MOVETO, (tc.xcoord, tc.ycoord)))
			i = i + 1
					
		pathdata.append((Path.LINETO, (tc.xcoord, tc.ycoord)))
	
	# Close up path
	pathdata.append((Path.CLOSEPOLY, (startTrashCan.xcoord, startTrashCan.ycoord)))
	
	codes, verts = zip(*pathdata)
	path = mpath.Path(verts, codes)
	x, y = zip(*path.vertices)
	
	# Plot a star for starting can
	axes.plot(x[0], y[0], 'k*', markersize=18)
	
	line, = axes.plot(x, y, 'g-')
	line.set_label('Optimal Tour')

def runACOWestEast(westCanList, eastCanList, silent=False):
	""" Run the ACO C code on the given east and west can lists """
	
	t0 = time.time()
		
	# Output WEST city file for ACO input
	outputACOTrashCanFile(westCanList, westCityFile)
	print "[Running WEST: Can Count: %d, ACO Cmd : %s]" % (len(westCanList), acoWestCmd)
	runACO(acoWestCmd, silent)
	westSolutionTour = parseACOSolutionFile(westSolnFile)

	# Output EAST city file for ACO input
	outputACOTrashCanFile(eastCanList, eastCityFile)
	print "[Running EAST: Can Count: %d, ACO Cmd : %s]" % (len(eastCanList), acoEastCmd)
	runACO(acoEastCmd, silent)
	eastSolutionTour = parseACOSolutionFile(eastSolnFile)
	
	print time.time() - t0, "seconds of ACO execution time."
	
	return (westSolutionTour, eastSolutionTour)

def runACO(command, silent=False):
	"""
	Call external ACO C program
	"""
	if silent is True:
#		subprocess.call([command], shell=True, stderr=open(os.devnull, 'w'), stdout=open(os.devnull, 'w') )
		subprocess.call(shlex.split(command), shell=False, stderr=None, stdout=None )
	else:
		subprocess.call(shlex.split(command))

#------------------------------------------------------------------------------
# File pre-processing functions
#------------------------------------------------------------------------------
def splitEastWest(trashCanList):
	"""
	Split the trash cans 50% east and 50% west, directly in half
	"""
	westCans = []
	eastCans = []
	
	total = 0
	for tc in trashCanList:
		total = total + float(tc.xcoord)

	avg = total / len(trashCanList)
	
	for tc in trashCanList:
		if float(tc.xcoord) > float(avg):
			eastCans.append(tc)
		else:
			westCans.append(tc)
	
	return (westCans, eastCans)

def part1(trashCanList):
	"""
	Do Part 1 of the assignment.
	Split trash cans in 50/50 even split according to East location.
	"""
	(westCans, eastCans) = splitEastWest(trashCanList)
	
	# Run the ACO on each West and East list
	(westSolutionTour, eastSolutionTour) = runACOWestEast(westCans, eastCans, True);
	
	return (westSolutionTour, eastSolutionTour)

def part2(trashCanList):
	"""
	Do Part 2 of the assignment.
	"""
	
	# Number of cans to try to move around
	canSwapCount = 9
	
	(westCans, eastCans) = splitEastWest(trashCanList)

	# Run control (no cans removed)
	print "Running control."
	(westSolutionTour, eastSolutionTour) = runACOWestEast(westCans, eastCans, True)
	bestWestLen = westSolutionTour.tourLen
	bestEastLen = eastSolutionTour.tourLen
	print "Control: W-Len: %d, E-Len: %d" % (bestWestLen, bestEastLen)

	# Sort cans by x-coordinates
	westSorted = sorted(westCans, key=lambda trashcan: trashcan.xcoord)
	eastSorted = sorted(eastCans, key=lambda trashcan: trashcan.xcoord)

	#Grab middle cans
	wSize = len(westSorted)
	west10MidCans = westSorted[wSize - canSwapCount:wSize]
	eSize = len(eastSorted)
	east10MidCans = eastSorted[0:canSwapCount]

	for wmc in west10MidCans:
		westSorted.remove(wmc)
	
	for emc in east10MidCans:
		eastSorted.remove(emc)

	# Save can lists w/o middle for later reset tour trials
	westConst = list(westSorted)
	eastConst = list(eastSorted)

	# Concat both lists to get combination list
	midCans = list(east10MidCans)
	midCans.extend(west10MidCans)

	tmpFile = open('BestOutput.tsp', 'w')
	t1 = time.clock();

	for j in range(3, 10):
		i = 0
		r = list(itertools.combinations(midCans, j))
		
		for comb in r:
			print "-- [Running trial #%d of %d, combination size: %d] --" % (i, len(r), len(comb))
			i = i +1

			# Setup two lists for run
			westSorted.extend(comb)
			tmp = list(midCans)
			for re in comb:
				tmp.remove(re)
			eastSorted.extend(tmp)
			
			(wst, est) = runACOWestEast(westSorted, eastSorted, True)
			
			if wst.tourLen <= bestWestLen and est.tourLen <= bestEastLen:
				print "!!!!!!!! Better route: W-Len: [%d vs %d], E-Len: [%d vs %d]" % (wst.tourLen, bestWestLen, est.tourLen, bestEastLen)
				westSolutionTour = Tour(wst)
				eastSolutionTour = Tour(est)
				
				bestWestLen = int(wst.tourLen)
				bestEastLen = int(est.tourLen)
				
				# Output solution tour
				output = "----- West Len: %d, East Len: %d ----" % (bestWestLen, bestEastLen)
				tmpFile.write(output)
				tmpFile.write("West Solution Tour:\n")
				for foo in westSolutionTour.trashCanList:
					tmpFile.write(foo.index + '\n')
				
				tmpFile.write("East Solution Tour:\n")
				for bar in eastSolutionTour.trashCanList:
					tmpFile.write(bar.index + '\n')
					
				tmpFile.flush()

			else:
				pass
#				print "Found crappy route: W-Len: [%d vs %d], E-Len: [%d vs %d]" % (wst.tourLen, bestWestLen, est.tourLen, bestEastLen)
				# Reset lists
				
			westSorted = list(westConst)
			eastSorted = list(eastConst)
		
	tmpFile.close()
	print time.time() - t1, "seconds of total tour optimization.\n"

	return (westSolutionTour, eastSolutionTour)

def part3(westCans, eastCans):

	# Run the ACO on each West and East list
	(westSolutionTour, eastSolutionTour) = runACOWestEast(westCans, eastCans, True);
	
	return (westSolutionTour, eastSolutionTour)	

#------------------------------------------------------------------------------
# Main
#------------------------------------------------------------------------------
if __name__ == '__main__':

	print "Running TSP..."
	os.chdir('../ACOTSP.V1.0/')
	
	#-------------------------------------------
	# Parse main input file
	#-------------------------------------------
	cans = parseACOTrashCanFile(acoCityFile)
	
	# Part 1
	(westSolutionTour, eastSolutionTour) = part1(cans)
	
	# Part 2
#	(westSolutionTour, eastSolutionTour) = part2(cans)

	# Part 3, 4, 5
	westCans = parseACOTrashCanFile(westCityFile)
	eastCans = parseACOTrashCanFile(eastCityFile)
	
#	(westSolutionTour, eastSolutionTour) = part3(westCans, eastCans)
	
	#-------------------------------------------	
	# Print stats
	#-------------------------------------------
	
	print "-------------------------------------"
	print "-- Statistics -----------------------"
	print "-------------------------------------"	
	print "East Cans: %s, West Cans: %s" % (len(westSolutionTour.trashCanList), len(eastSolutionTour.trashCanList))
	print "Optimal paths: \tWest: %s, East: %s" % (westSolutionTour.tourLen, eastSolutionTour.tourLen)
	print ""
	
	#-------------------------------------------	
	# Plot & show the map
	#-------------------------------------------
	axes = plotMap()
	
	# Plot can locations
	plotTrashCanLocations(axes, "bo", westCans)
	plotTrashCanLocations(axes, "ro", eastCans)
	
	# Plot west and east tours
	plotTrashCanTour(axes, westSolutionTour)
	plotTrashCanTour(axes, eastSolutionTour)
	
	plt.show()
