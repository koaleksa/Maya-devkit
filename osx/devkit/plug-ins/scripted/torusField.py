#-
# ==========================================================================
# Copyright (C) 1995 - 2006 Autodesk, Inc. and/or its licensors.  All 
# rights reserved.
#
# The coded instructions, statements, computer programs, and/or related 
# material (collectively the "Data") in these files contain unpublished 
# information proprietary to Autodesk, Inc. ("Autodesk") and/or its 
# licensors, which is protected by U.S. and Canadian federal copyright 
# law and by international treaties.
#
# The Data is provided for use exclusively by You. You have the right 
# to use, modify, and incorporate this Data into other products for 
# purposes authorized by the Autodesk software license agreement, 
# without fee.
#
# The copyright notices in the Software and this entire statement, 
# including the above license grant, this restriction and the 
# following disclaimer, must be included in all copies of the 
# Software, in whole or in part, and all derivative works of 
# the Software, unless such copies or derivative works are solely 
# in the form of machine-executable object code generated by a 
# source language processor.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. 
# AUTODESK DOES NOT MAKE AND HEREBY DISCLAIMS ANY EXPRESS OR IMPLIED 
# WARRANTIES INCLUDING, BUT NOT LIMITED TO, THE WARRANTIES OF 
# NON-INFRINGEMENT, MERCHANTABILITY OR FITNESS FOR A PARTICULAR 
# PURPOSE, OR ARISING FROM A COURSE OF DEALING, USAGE, OR 
# TRADE PRACTICE. IN NO EVENT WILL AUTODESK AND/OR ITS LICENSORS 
# BE LIABLE FOR ANY LOST REVENUES, DATA, OR PROFITS, OR SPECIAL, 
# DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES, EVEN IF AUTODESK 
# AND/OR ITS LICENSORS HAS BEEN ADVISED OF THE POSSIBILITY 
# OR PROBABILITY OF SUCH DAMAGES.
#
# ==========================================================================
#+

#
# Creation Date:   3 October 2006
#
# Example Plugin: torusField.py
#
#  Description
#	The torusField node implements an attraction-and-repel field.
#
#	The field repels all objects between itself and repelDistance attribute
#	and attracts objects greater than attractDistance attribute from itself.  
#	This will eventually result in the objects clustering
#	in a torus shape around the field.
#
#	See torusFieldTest.py for usage
#

import math, sys
import maya.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMayaMPx as OpenMayaMPx
import maya.OpenMayaRender as OpenMayaRender

kPluginName = "spTorusField"
kPluginNodeId = OpenMaya.MTypeId(0x87008)

glRenderer = OpenMayaRender.MHardwareRenderer.theRenderer()
glFT = glRenderer.glFunctionTable()

def statusError(msg):
	sys.stderr.write("%s\n" % message)
	raise	# called from exception handlers only, reraise exception


# Node definition
class TorusField(OpenMayaMPx.MPxFieldNode):
	# Attributes
	# minimum distance from field at which repel is applied
	#
	aMinDistance = OpenMaya.MObject()

	# min distance from field at which the force attracts
	#
	aAttractDistance = OpenMaya.MObject()

	# max distance from field at which the force repels.
	#
	aRepelDistance = OpenMaya.MObject()

	# drag exerted on the attractRepel force.
	#
	aDrag = OpenMaya.MObject()

	# amplitude/magnitude of the swarm force.
	#
	aSwarmAmplitude = OpenMaya.MObject()

	# frequency of the swarm force.
	#
	aSwarmFrequency = OpenMaya.MObject()

	# phase of the swarm force.
	#
	aSwarmPhase = OpenMaya.MObject()


	def __init__(self):
		OpenMayaMPx.MPxFieldNode.__init__(self)


	def compute(self, plug, block):
		"""
		Compute output force.
		"""
		outputForce = OpenMayaMPx.cvar.MPxFieldNode_mOutputForce
		if not (plug == outputForce):
			return

		# get the logical index of the element this plug refers to.
		#
		try:
			multiIndex = plug.logicalIndex()
		except:
			statusError("ERROR in plug.logicalIndex.")

		# Get input data handle, use outputArrayValue since we do not
		# want to evaluate both inputs, only the one related to the
		# requested multiIndex. Evaluating both inputs at once would cause
		# a dependency graph loop.
		#
		inputData = OpenMayaMPx.cvar.MPxFieldNode_mInputData
		try:
			hInputArray = block.outputArrayValue(inputData)
		except:
			statusError("ERROR in hInputArray = block.outputArrayValue().")

		try:
			hInputArray.jumpToElement(multiIndex)
		except:
			statusError("ERROR: hInputArray.jumpToElement failed.")

		# get children of aInputData.
		#
		try:
			hCompond = hInputArray.inputValue()
		except:
			statusError("ERROR in hCompond=hInputArray.inputValue")

		inputPositions = OpenMayaMPx.cvar.MPxFieldNode_mInputPositions
		hPosition = hCompond.child(inputPositions)
		dPosition = hPosition.data()
		fnPosition = OpenMaya.MFnVectorArrayData(dPosition)
		try:
			points = fnPosition.array()
		except:
			statusError("ERROR in fnPosition.array(), not find points.")

		inputVelocities = OpenMayaMPx.cvar.MPxFieldNode_mInputVelocities
		hVelocity = hCompond.child(inputVelocities)
		dVelocity = hVelocity.data()
		fnVelocity = OpenMaya.MFnVectorArrayData(dVelocity)
		try:
			velocities = fnVelocity.array()
		except:
			statusError("ERROR in fnVelocity.array(), not find velocities.")

		inputMass = OpenMayaMPx.cvar.MPxFieldNode_mInputMass
		hMass = hCompond.child(inputMass)
		dMass = hMass.data()
		fnMass = OpenMaya.MFnDoubleArrayData(dMass)
		try:
			masses = fnMass.array()
		except:
			statusError("ERROR in fnMass.array(), not find masses.")

		# Compute the output force.
		#
		forceArray = OpenMaya.MVectorArray()
		useMaxDistSet = self.__useMaxDistanceValue(block)
		if useMaxDistSet:
			self.__applyMaxDist(block, points, velocities, masses, forceArray)
		else:
			self.__applyNoMaxDist(block, points, velocities, masses, forceArray)

		# get output data handle
		#
		try:
			hOutArray = block.outputArrayValue(outputForce)
		except:
			statusError("ERROR in hOutArray = block.outputArrayValue.")
		try:
			bOutArray = hOutArray.builder()
		except:
			statusError("ERROR in bOutArray = hOutArray.builder.")

		# get output force array from block.
		#
		try:
			hOut = bOutArray.addElement(multiIndex)
		except:
			statusError("ERROR in hOut = bOutArray.addElement.")

		fnOutputForce = OpenMaya.MFnVectorArrayData()
		try:
			dOutputForce = fnOutputForce.create(forceArray)
		except:
			statusError("ERROR in dOutputForce = fnOutputForce.create")

		# update data block with new output force data.
		#
		hOut.setMObject(dOutputForce)
		block.setClean(plug)


	def draw (self, view, path, style, status):
		"""
		Draw a set of rings to symbolie the field. This does not override default icon, you can do that by implementing the iconBitmap() function
		"""
		TORUS_PI = 3.14159265
		TORUS_2PI = 2.0 * TORUS_PI
		EDGES = 30
		SEGMENTS = 20

		view.beginGL()
		for j in range(SEGMENTS):
			glFT.glPushMatrix()
			glFT.glRotatef(360.0 * j / SEGMENTS, 0.0, 1.0, 0.0)
			glFT.glTranslatef(1.5, 0.0, 0.0)
			for i in range(EDGES):
				glFT.glBegin(OpenMayaRender.MGL_LINE_STRIP)
				p0 = TORUS_2PI * i / EDGES
				p1 = TORUS_2PI * (i+1) / EDGES
				glFT.glVertex2f(math.cos(p0), math.sin(p0))
				glFT.glVertex2f(math.cos(p1), math.sin(p1))
				glFT.glEnd()
			glFT.glPopMatrix()
		view.endGL()


	def getForceAtPoint(self, points, velocities, masses, forceArray, deltaTime):
		"""
		This method is not required to be overridden, it is only necessary
		for compatibility with the MFnField function set.
		"""
		block = forceCache()
		useMaxDistSet = self.__useMaxDistanceValue(block)
		if useMaxDistSet:
			self.__applyMaxDist(block, points, velocities, masses, forceArray)
		else:
			self.__applyNoMaxDist(block, points, velocities, masses, forceArray)


	def iconSizeAndOrigin(self, width, height, xbo, ybo):
		OpenMaya.MScriptUtil.setUint( width, 32 )
		OpenMaya.MScriptUtil.setUint( height, 32 )
		OpenMaya.MScriptUtil.setUint( xbo, 4 )
		OpenMaya.MScriptUtil.setUint( ybo, 4 )


	def iconBitmap(self, bitmap):
		OpenMaya.MScriptUtil.setUcharArray( bitmap, 0, 0x18 )
		OpenMaya.MScriptUtil.setUcharArray( bitmap, 4, 0x66 )
		OpenMaya.MScriptUtil.setUcharArray( bitmap, 8, 0xC3 )
		OpenMaya.MScriptUtil.setUcharArray( bitmap, 12, 0x81 )
		OpenMaya.MScriptUtil.setUcharArray( bitmap, 16, 0x81 )
		OpenMaya.MScriptUtil.setUcharArray( bitmap, 20, 0xC3 )
		OpenMaya.MScriptUtil.setUcharArray( bitmap, 24, 0x66 )
		OpenMaya.MScriptUtil.setUcharArray( bitmap, 28, 0x18 )


	# methods to compute output force.
	#
	def __applyNoMaxDist(self, block, points, velocities, masses, outputForce):
		"""
		Compute output force in the case that the useMaxDistance is not set.
		"""
		# points and velocities should have the same length. If not return.
		#
		if points.length() != velocities.length():
			return

		# clear the output force array
		#
		outputForce.clear()

		# get field parameters.
		#
		magValue = self.__magnitudeValue(block)
		minDist = self.__minDistanceValue(block)
		attractDist = self.__attractDistanceValue(block)
		repelDist = self.__repelDistanceValue(block)
		dragMag = self.__dragValue(block)
		swarmAmp = self.__swarmAmplitudeValue(block)

		# get owner's data. posArray may have only one point which is the centroid
		# (if this has owner) or field position(if without owner). Or it may have
		# a list of points if with owner and applyPerVertex.
		#
		posArray = self.__ownerPosition(block)

		fieldPosCount = posArray.length()
		receptorSize = points.length()

		# With this model,if max distance isn't set then we
		# also don't attenuate, because 1 - dist/maxDist isn't
		# meaningful. No max distance and no attenuation.
		#
		for ptIndex in range(receptorSize):
			forceV = OpenMaya.MVector(0.0,0.0,0.0)
			receptorPoint = points[ptIndex]

			# Apply from every field position to every receptor position.
			#
			distance = 0.0
			for i in range(fieldPosCount-1, -1, -1):
				difference = receptorPoint - posArray[i]
				distance = difference.length()

				if distance < minDist:
					continue

				if distance <= repelDist:
					forceV += difference * magValue
				elif distance >= attractDist:
					forceV += -difference * magValue

			# Apply drag/swarm only if the object is inside the zone
			# the repulsion-attraction is pushing the object to.
			#
			if distance >= repelDist and distance <= attractDist:
				if dragMag > 0:
					if fieldPosCount > 0:
						dragForceV = velocities[ptIndex] * (-dragMag) * fieldPosCount
						forceV += dragForceV

				if swarmAmp > 0:
					frequency = self.__swarmFrequencyValue(block)
					phase = OpenMaya.MVector(0.0, 0.0, frequency)

					# Add swarm in here
					#
					for i in range(fieldPosCount-1, -1, -1):
						difference = receptorPoint - posArray[i]
						difference = (difference + phase) * frequency

						noiseEffect = [ difference[i] for i in range(3) ]
						if( (noiseEffect[0] < -2147483647.0) or
							(noiseEffect[0] >  2147483647.0) or
							(noiseEffect[1] < -2147483647.0) or
							(noiseEffect[1] >  2147483647.0) or
							(noiseEffect[2] < -2147483647.0) or
							(noiseEffect[2] >  2147483647.0) ):
							continue

						noiseOut = self.__noiseFunction(noiseEffect)
						swarmForce = OpenMaya.MVector(noiseOut[0] * swarmAmp,
														noiseOut[1] * swarmAmp,
														noiseOut[2] * swarmAmp)
						forceV += swarmForce

			outputForce.append(forceV)


	def __applyMaxDist(self, block, points, velocities, masses, outputForce):
		"""
		Compute output force in the case that the useMaxDistance is set.
		"""
		# points and velocities should have the same length. If not return.
		#
		if points.length() != velocities.length():
			return

		# clear the output force array.
		#
		outputForce.clear()

		# get field parameters.
		#
		magValue = self.__magnitudeValue(block)
		attenValue = self.__attenuationValue(block)
		maxDist = self.__maxDistanceValue(block)
		minDist = self.__minDistanceValue(block)
		attractDist = self.__attractDistanceValue(block)
		repelDist = self.__repelDistanceValue(block)
		dragMag = self.__dragValue(block)
		swarmAmp = self.__swarmAmplitudeValue(block)

		# get owner's data. posArray may have only one point which is the centroid
		# (if this has owner) or field position(if without owner). Or it may have
		# a list of points if with owner and applyPerVertex.
		#
		posArray = self.__ownerPosition(block)

		fieldPosCount = posArray.length()
		receptorSize = points.length()

		for ptIndex in range(receptorSize):
			receptorPoint = points[ptIndex]

			# Apply from every field position to every receptor position.
			#
			forceV = OpenMaya.MVector(0,0,0)
			sumForceV = OpenMaya.MVector(0,0,0)
			for i in range(fieldPosCount-1, -1, -1):
				difference = receptorPoint-posArray[i]
				distance  = difference.length()

				if (distance < minDist or distance > maxDist):
					continue

				if attenValue > 0.0:
					force = magValue * (math.pow((1.0-(distance/maxDist)),attenValue))
					forceV = difference * force
				elif (distance <= repelDist):
					forceV = difference * magValue
				elif (distance >= attractDist):
					forceV = -difference * magValue						

				# Apply drag and swarm if the object is inside
				# the zone the repulsion-attraction is pushing the
				# object to, and if they are set.
				#
				if distance >= repelDist and distance <= attractDist:
					if dragMag > 0:
						if fieldPosCount > 0:
							dragForceV = velocities[ptIndex] * (-dragMag) * fieldPosCount
							forceV += dragForceV

					if swarmAmp > 0:
						frequency = self.__swarmFrequencyValue(block)
						phase = OpenMaya.MVector(0.0, 0.0, frequency)

						# Add swarm in here
						#
						for i in range(fieldPosCount-1, -1, -1):
							difference = receptorPoint - posArray[i]
							difference = (difference + phase) * frequency

							noiseEffect = [ difference[i] for i in range(3) ]
							if( (noiseEffect[0] < -2147483647.0) or
								(noiseEffect[0] >  2147483647.0) or
								(noiseEffect[1] < -2147483647.0) or
								(noiseEffect[1] >  2147483647.0) or
								(noiseEffect[2] < -2147483647.0) or
								(noiseEffect[2] >  2147483647.0) ):
								continue

							noiseOut = self.__noiseFunction(noiseEffect)
							swarmForce = OpenMaya.MVector(noiseOut[0] * swarmAmp,
															noiseOut[1] * swarmAmp,
															noiseOut[2] * swarmAmp)
							forceV += swarmForce

				if (maxDist > 0.0):
					forceV *= self.falloffCurve(distance/maxDist)
				sumForceV += forceV

			outputForce.append(sumForceV)


	def __ownerPosition(self, block):
		"""
		If this field has an owner, get the owner's position array or
		centroid, then assign it to the ownerPosArray.
		If it does not have owner, get the field position in the world
		space, and assign it to the given array, ownerPosArray.
		"""
		ownerPosArray = OpenMaya.MVectorArray()
		if self.__applyPerVertexValue(block):
			ownerPos = OpenMayaMPx.cvar.MPxFieldNode_mOwnerPosData
			try:
				hOwnerPos = block.inputValue(ownerPos)
			except:
				# get the field position in the world space
				# and add it into ownerPosArray.
				#
				worldPos = self.__getWorldPosition()
				ownerPosArray.append(worldPos)
			else:
				dOwnerPos = hOwnerPos.data()
				fnOwnerPos = OpenMaya.MFnVectorArrayData(dOwnerPos)
				try:
					posArray = fnOwnerPos.array()
				except:
					worldPos = self.__getWorldPosition()
					ownerPosArray.append(worldPos)
				else:
					# assign vectors from block to ownerPosArray.
					#
					for i in range(posArray.length()):
						ownerPosArray.append(posArray[i])
		else:
			try:
				centroidV = self.__ownerCentroidValue(block)
			except:
				# get the field position in the world space.
				#
				worldPos = self.__getWorldPosition()
				ownerPosArray.append(worldPos)
			else:
				ownerPosArray.append(centroidV)	

		return ownerPosArray


	def __getWorldPosition(self):
		thisNode = self.thisMObject()
		fnThisNode = OpenMaya.MFnDependencyNode(thisNode)

		# get worldMatrix attribute.
		#
		worldMatrixAttr = fnThisNode.attribute("worldMatrix")

		# build worldMatrix plug, and specify which element the plug refers to.
		# We use the first element(the first dagPath of this field).
		#
		matrixPlug = OpenMaya.MPlug(thisNode, worldMatrixAttr)
		matrixPlug = matrixPlug.elementByLogicalIndex(0)

		# Get the value of the 'worldMatrix' attribute
		#
		try:
			matrixObject = matrixPlug.asMObject(matrixObject)
		except:
			statusError("TorusField.__getWorldPosition: get matrixObject")

		try:
			worldMatrixData = OpenMaya.MFnMatrixData(matrixObject)
		except:
			statusError("TorusField.__getWorldPosition: get worldMatrixData")

		try:
			worldMatrix = worldMatrixData.matrix()
		except:
			statusError("TorusField.__getWorldPosition: get worldMatrix")

		# assign the translate to the given vector.
		#
		return OpenMaya.MVector(worldMatrix(3, 0), worldMatrix(3, 1), worldMatrix(3, 2))


	def __noiseFunction(self, inNoise):
		"""
		A noise function
		"""
		# Shared data for noise computation
		#
		xlim = [ [0,0], [0,0], [0,0] ] # integer bound for point
		xarg = [0.0, 0.0, 0.0 ] # fractional part

		# Helper functions to compute noise
		#
		rand3a = lambda x,y,z: frand(67*(x)+59*(y)+71*(z))
		rand3b = lambda x,y,z: frand(73*(x)+79*(y)+83*(z))
		rand3c = lambda x,y,z: frand(89*(x)+97*(y)+101*(z))
		rand3d = lambda x,y,z: frand(103*(x)+107*(y)+109*(z))

		def frand(s):
			seed = s << 13^s
			return (1.0 - ((s*(s*s*15731+789221)+1376312589) & 0x7fffffff)/1073741824.0)

		def hermite(p0, p1, r0, r1, t):
			t2 = t * t
			t3 = t2 * t
			_3t2 = 3.0 * t2
			_2t3 = 2.0 * t3 

			return (p0*(_2t3-_3t2+1) + p1*(-_2t3+_3t2) + r0*(t3-2.0*t2+t) + r1*(t3-t2))

		def interpolate(i, n):
			f = [ 0.0, 0.0, 0.0, 0.0 ]
			if n == 0: # at 0, return lattice value
				f[0] = rand3a( xlim[0][i&1], xlim[1][i>>1&1], xlim[2][i>>2] )
				f[1] = rand3b( xlim[0][i&1], xlim[1][i>>1&1], xlim[2][i>>2] )
				f[2] = rand3c( xlim[0][i&1], xlim[1][i>>1&1], xlim[2][i>>2] )
				f[3] = rand3d( xlim[0][i&1], xlim[1][i>>1&1], xlim[2][i>>2] )
			else:
				n -= 1
				f0 = interpolate(i, n) # compute first half
				f1 = interpolate(i | 1<<n, n) # compute second half

				# use linear interpolation for slopes
				f[0] = (1.0 - xarg[n]) * f0[0] + xarg[n] * f1[0]
				f[1] = (1.0 - xarg[n]) * f0[1] + xarg[n] * f1[1]
				f[2] = (1.0 - xarg[n]) * f0[2] + xarg[n] * f1[2]

				# use hermite interpolation for values
				f[3] = hermite(f0[3], f1[3], f0[n], f1[n], xarg[n])

			return f

		xlim[0][0] = int(math.floor(inNoise[0]))
		xlim[0][1] = xlim[0][0] + 1
		xlim[1][0] = int(math.floor(inNoise[1]))
		xlim[1][1] = xlim[1][0] + 1
		xlim[2][0] = int(math.floor(inNoise[2]))
		xlim[2][1] = xlim[2][0] + 1

		xarg[0] = inNoise[0] - xlim[0][0]
		xarg[1] = inNoise[1] - xlim[1][0]
		xarg[2] = inNoise[2] - xlim[2][0]

		return interpolate(0, 3)


	# methods to get attribute value.
	#
	def __magnitudeValue(self, block):
		magnitude = OpenMayaMPx.cvar.MPxFieldNode_mMagnitude
		hValue = block.inputValue(magnitude)
		return hValue.asDouble()


	def __attenuationValue(self, block):
		attenuation = OpenMayaMPx.cvar.MPxFieldNode_mAttenuation
		hValue = block.inputValue(attenuation)
		return hValue.asDouble()


	def __maxDistanceValue(self, block):
		maxDistance = OpenMayaMPx.cvar.MPxFieldNode_mMaxDistance
		hValue = block.inputValue(maxDistance)
		return hValue.asDouble()


	def __useMaxDistanceValue(self, block):
		useMaxDistance = OpenMayaMPx.cvar.MPxFieldNode_mUseMaxDistance
		hValue = block.inputValue(useMaxDistance)
		return hValue.asBool()


	def __applyPerVertexValue(self, block):
		applyPerVertex = OpenMayaMPx.cvar.MPxFieldNode_mApplyPerVertex
		hValue = block.inputValue(applyPerVertex)
		return hValue.asBool()


	# methods to get attribute value of local attributes.
	#
	def __minDistanceValue(self, block):
		hValue = block.inputValue(TorusField.aMinDistance)
		return hValue.asDouble()


	def __attractDistanceValue(self, block):
		hValue = block.inputValue(TorusField.aAttractDistance)
		return hValue.asDouble()


	def __repelDistanceValue(self, block):
		hValue = block.inputValue(TorusField.aRepelDistance)
		return hValue.asDouble()


	def __dragValue(self, block):
		hValue = block.inputValue(TorusField.aDrag)
		return hValue.asDouble()


	def __swarmAmplitudeValue(self, block):
		hValue = block.inputValue(TorusField.aSwarmAmplitude)
		return hValue.asDouble()


	def __swarmFrequencyValue(self, block):
		hValue = block.inputValue(TorusField.aSwarmFrequency)
		return hValue.asDouble()


	def __swarmPhaseValue(self, block):
		hValue = block.inputValue(TorusField.aSwarmPhase)
		return hValue.asDouble()


	def __ownerCentroidValue(self, block):
		ownerCentroidX = OpenMayaMPx.cvar.MPxFieldNode_mOwnerCentroidX
		ownerCentroidY = OpenMayaMPx.cvar.MPxFieldNode_mOwnerCentroidY
		ownerCentroidZ = OpenMayaMPx.cvar.MPxFieldNode_mOwnerCentroidZ
		hValueX = block.inputValue(ownerCentroidX)
		hValueY = block.inputValue(ownerCentroidY)
		hValueZ = block.inputValue(ownerCentroidZ)
		return OpenMaya.MVector(hValueX.asDouble(),
									hValueY.asDouble(),
									hValueZ.asDouble())


############################################################################


# creator
def nodeCreator():
	return OpenMayaMPx.asMPxPtr(TorusField())


# initializer
def nodeInitializer():
	numAttr = OpenMaya.MFnNumericAttribute()

	# create the field basic attributes.
	#
	TorusField.aMinDistance = numAttr.create("minDistance", "mnd", OpenMaya.MFnNumericData.kDouble, 0.0)
	numAttr.setKeyable(True)
	try:
		TorusField.addAttribute(TorusField.aMinDistance)
	except:
		statusError("ERROR adding aMinDistance attribute.")

	TorusField.aAttractDistance = numAttr.create("attractDistance", "ad", OpenMaya.MFnNumericData.kDouble, 20.0)
	numAttr.setKeyable(True)
	try:
		TorusField.addAttribute(TorusField.aAttractDistance)
	except:
		statusError("ERROR adding aAttractDistance attribute.")

	TorusField.aRepelDistance = numAttr.create("repelDistance", "rd", OpenMaya.MFnNumericData.kDouble, 10.0)
	numAttr.setKeyable(True)
	try:
		TorusField.addAttribute(TorusField.aRepelDistance)
	except:
		statusError("ERROR adding aRepelDistance attribute.")

	TorusField.aDrag = numAttr.create("drag", "d", OpenMaya.MFnNumericData.kDouble, 0.0)
	numAttr.setKeyable(True)
	try:
		TorusField.addAttribute(TorusField.aDrag)
	except:
		statusError("ERROR adding aDrag attribute.")

	TorusField.aSwarmAmplitude = numAttr.create("swarmAmplitude", "samp", OpenMaya.MFnNumericData.kDouble, 0.0)
	numAttr.setKeyable(True)
	try:
		TorusField.addAttribute(TorusField.aSwarmAmplitude)
	except:
		statusError("ERROR adding aSwarmAmplitude attribute.")

	TorusField.aSwarmFrequency = numAttr.create("swarmFrequency", "sfrq", OpenMaya.MFnNumericData.kDouble, 1.0)
	numAttr.setKeyable(True)
	try:
		TorusField.addAttribute(TorusField.aSwarmFrequency)
	except:
		statusError("ERROR adding aSwarmFrequency attribute.")

	TorusField.aSwarmPhase = numAttr.create("swarmPhase", "sa", OpenMaya.MFnNumericData.kDouble, 0.0)
	numAttr.setKeyable(True)
	try:
		TorusField.addAttribute(TorusField.aSwarmPhase)
	except:
		statusError("ERROR adding aSwarmPhase attribute.")


# initialize the script plug-in
def initializePlugin(mobject):
	mplugin = OpenMayaMPx.MFnPlugin(mobject, "Autodesk", "1.0", "Any")
	try:
		mplugin.registerNode(kPluginName, kPluginNodeId, nodeCreator, nodeInitializer, OpenMayaMPx.MPxNode.kFieldNode)
	except:
		statusError("Failed to register node: %s" % kPluginName)


# uninitialize the script plug-in
def uninitializePlugin(mobject):
	mplugin = OpenMayaMPx.MFnPlugin(mobject)
	try:
		mplugin.deregisterNode(kPluginNodeId)
	except:
		statusError("Failed to deregister node: %s" % kPluginName)