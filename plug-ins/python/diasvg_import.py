#  PyDia SVG Import
#  Copyright (c) 2003, Hans Breuer <hans@breuer.org>
#
#  Pure Python Dia Import Filter - to show how it is done.
#  It tries to be also tries to be more featureful and
#  robust then the SVG importer written in C, but as long
#  as PyDia has issues this will _not_ be the case. Known issues :
#  - Can't set 'bez_points' yet, requires support in PyDia and lib/bez*.c
#    and here
#  - Groups are not handled yet on the Dia side
#  - xlink stuff
#  - see FIXME in this file

#    This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import string, math

# Dias unit is cm, the default scale should be determined from svg:width and viewBox
dfUserScale = 0.05
dictUnitScales = {
	"em" : 0.03, "ex" : 0.03, #FIXME: these should be _relative_ to current font
	"px" : 1.0, "pt" : 0.0352778, "pc" : 0.4233333, 
	"cm" : 1.0, "mm" : 10.0, "in" : 25.4}

def Scaled(s) :
	# em, ex, px, pt, pc, cm, mm, in, and percentages
	if s[-1] in string.digits :
		# use global scale
		return float(s) * dfUserScale
	else :
		unit = s[-2:]
		try :
			return float(s[:-2]) * dictUnitScales[unit]
		except :
			# warn about invalid unit ??
			print "Unknown unit", s[:-2], s[-2:]
			return float(s) * dfUserScale
class Object :
	def __init__(self) :
		self.props = {"x" : 0, "y" : 0}
		# "line_width", "line_colour", "line_style"
	def style(self, s) :
		sp1 = string.split(s, ";")
		for s1 in sp1 :
			sp2 = string.split(string.strip(s1), ":")
			if len(sp2) == 2 :
				try :
					eval("self." + string.replace(sp2[0], "-", "_") + "(\"" + sp2[1] + "\")")
				except AttributeError :
					self.props[sp2[0]] = sp2[1]
	def x(self, s) :
		self.props["x"] = Scaled(s)
	def y(self, s) :
		self.props["y"] = Scaled(s)
	def width(self, s) :
		self.props["width"] = Scaled(s)
	def height(self, s) :
		self.props["height"] = Scaled(s)
	def stroke(self,s) :
		self.props["stroke"] = s.encode("UTF-8")
	def stroke_width(self,s) :
		self.props["stroke-width"] = Scaled(s)
	def fill(self,s) :
		self.props["fill"] = s
	def __repr__(self) :
		return self.dt + " : " + str(self.props)
	def Set(self, d) :
		pass
	def ApplyProps(self, o) :
		pass
	def Create(self) :
		print self.dt
		ot = dia.get_object_type (self.dt)
		o, h1, h2 = ot.create(self.props["x"], self.props["y"])
		# apply common props
		if self.props.has_key("stroke") and o.properties.has_key("line_colour") :
			if self.props["stroke"] != "none" :
				try :
					o.properties["line_colour"] = self.props["stroke"]
				except :
					pass # FIXME: not sure how to handle rgb(192,27,38)
		if self.props.has_key("fill") and o.properties.has_key("fill_colour") :
			if self.props["fill"] == "none" :
				o.properties["show_background"] = 0
			else :
				o.properties["show_background"] = 1
				try :
					o.properties["fill_colour"] =self.props["fill"]
				except :
					pass # not sure how to handle rgb(192,27,38)
		if self.props.has_key("stroke-width") and o.properties.has_key("line_width") :
			o.properties["line_width"] = self.props["stroke-width"]
		self.ApplyProps(o)
		return o

class Svg(Object) :
	# not a placeable object but similar while parsing
	def __init__(self) :
		Object.__init__(self)
		self.dt = "svg"
		self.bbox_w = None
		self.bbox_h = None
	def width(self,s) :
		global dfUserScale
		d = dfUserScale
		dfUserScale = 0.05
		self.bbox_w = Scaled(s)
		self.props["width"] = self.bbox_w
		dfUserScale = d
	def height(self,s) :
		global dfUserScale
		d = dfUserScale
		# with stupid info Dia still has a problem cause zooming is limited to 5.0%
		dfUserScale = 0.05
		self.bbox_h = Scaled(s)
		self.props["height"] = self.bbox_h
		dfUserScale = d
	def viewBox(self,s) :
		global dfUserScale
		self.props["viewBox"] = s
		sp = string.split(s, " ")
		w = float(sp[2]) - float(sp[0])
		h = float(sp[3]) - float(sp[1])
		# FIXME: the following relies on the call order of width,height,viewBox
		# which is _not_ the order it is in the file
		if self.bbox_w and self.bbox_h :
			dfUserScale = math.sqrt((self.bbox_w / w)*(self.bbox_h / h))
		elif self.bbox_w :
			dfUserScale = self.bbox_w / w
		elif self.bbox_h :
			dfUserScale = self.bbox_h / h
	def xmlns(self,s) :
		self.props["xmlns"] = s
	def version(self,s) :
		self.props["version"] = s
	def __repr__(self) :
		global dfUserScale
		return Object.__repr__(self) + "\nUserScale : " + str(dfUserScale)
	def Create(self) :
		return None
class Group(Object) :
	def __init__(self) :
		Object.__init__(self)
		self.dt = "None"
		self.childs = []
	def Add(self, o) :
		self.childs.append(o)
	def Create(self) :
		for o in self.childs :
			o.Create()
		return None
class Image(Object) :
	def __init__(self) :
		Object.__init__(self)
		self.dt = "Standard - Image"
	def preserveAspectRatio(self,s) :
		self.props["keep_aspect"] = s
	def xlink__href(self,s) :
		#print s
		if s[:8] == "file:///" :
			self.props["uri"] = s.encode("UTF-8")
		else :
			pass #FIXME how to import data into dia ??
	def Create(self) :
		if not (self.props.has_key("uri") or self.props.has_key("data")) :
			return None
		return Object.Create(self)
	def ApplyProps(self,o) :
		if self.props.has_key("width") :
			o.properties["elem_width"] = self.props["width"]
		if self.props.has_key("width") :
			o.properties["elem_height"] = self.props["height"]
		if self.props.has_key("uri") :
			o.properties["image_file"] = self.props["uri"][8:] 
class Line(Object) :
	def __init__(self) :
		Object.__init__(self)
		self.dt = "Standard - Line"
		# "line_width". "line_color"
		# "start_point". "end_point"
	def x1(self, s) :
		self.props["x"] = Scaled(s)
	def y1(self, s) :
		self.props["y"] = Scaled(s)
	def x2(self, s) :
		self.props["x2"] = Scaled(s)
	def y2(self, s) :
		self.props["y2"] = Scaled(s)
	def ApplyProps(self, o) :
		#pass
		o.properties["end_point"] = (self.props["x2"], self.props["y2"])
class Path(Object) :
	def __init__(self) :
		Object.__init__(self)
		self.dt = "Standard - BezierLine" # or Beziergon ?
	def d(self, s) :
		#FIXME: parse the strange path data
		self.props["data"] = s
	def Create(self) :
		return None # not yet
class Rect(Object) :
	def __init__(self) :
		Object.__init__(self)
		self.dt = "Standard - Box"
		# "corner_radius", 
	def ApplyProps(self,o) :
		o.properties["elem_width"] = self.props["width"]	
		o.properties["elem_height"] = self.props["height"]	
class Ellipse(Object) :
	def __init__(self) :
		Object.__init__(self)
		self.dt = "Standard - Ellipse"
		self.props["cx"] = 0
		self.props["cy"] = 0
		self.props["rx"] = 1
		self.props["ry"] = 1
	def cx(self,s) :
		self.props["cx"] = Scaled(s)
		self.props["x"] = self.props["cx"] - self.props["rx"]
	def cy(self,s) :
		self.props["cy"] = Scaled(s)
		self.props["y"] = self.props["cy"] - self.props["ry"]
	def rx(self,s) :
		self.props["rx"] = Scaled(s)
		self.props["x"] = self.props["cx"] - self.props["rx"]
	def ry(self,s) :
		self.props["ry"] = Scaled(s)
		self.props["y"] = self.props["cy"] - self.props["ry"]
	def ApplyProps(self,o) :
		o.properties["elem_width"] = 2.0 * self.props["rx"]	
		o.properties["elem_height"] = 2.0 * self.props["ry"]
class Circle(Ellipse) :
	def __init__(self) :
		Ellipse.__init__(self)
	def r(self,s) :
		Ellipse.rx(self,s)
		Ellipse.ry(self,s)
class Poly(Object) :
	def __init__(self) :	
		Object.__init__(self)
		self.dt = None # abstract class !
	def points(self,s) :
		sp1 = string.split(s)
		pts = []
		for s1 in sp1 :
			sp2 = string.split(s1, ",")
			if len(sp2) == 2 :
				pts.append((Scaled(sp2[0]), Scaled(sp2[1])))
		self.props["points"] = pts
	def ApplyProps(self,o) :
		o.properties["poly_points"] = self.props["points"]
class Polygon(Poly) :
	def __init__(self) :
		Poly.__init__(self)
		self.dt = "Standard - Polygon"
class Polyline(Poly) :
	def __init__(self) :
		Poly.__init__(self)
		self.dt = "Standard - PolyLine"
class Text(Object) :
	def __init__(self) :
		Object.__init__(self)
		self.dt = "Standard - Text"
		# text_font, text_height, text_color, text_alignment
	def Set(self, d) :
		if self.props.has_key("text") :
			self.props["text"] += d
		else :
			self.props["text"] = d
	def text_anchor(self,s) :
		self.props["text-anchor"] = s
	def font_size(self,s) :
		self.props["font-size"] = Scaled(s)
		# ?? self.props["y"] =self.props["y"] - Scaled(s)
	def font_weight(self, s) :
		self.props["font-weight"] = s
	def font_style(self, s) :
		self.props["font-style"] = s
	def font_family(self, s) :
		self.props["font-family"] = s
	def ApplyProps(self, o) :
		o.properties["text"] = self.props["text"].encode("UTF-8")
		if self.props.has_key("text-anchor") :
			if self.props["text-anchor"] == "middle" : o.properties["text_alignment"] = 1
			elif self.props["text-anchor"] == "end" : o.properties["text_alignment"] = 2
			else : o.properties["text_alignment"] = 0
		if self.props.has_key("fill") :
			o.properties["text_colour"] = self.props["fill"]
		if self.props.has_key("font-size") :
			o.properties["text_height"] = self.props["font-size"]
class Desc(Object) :
	#FIXME is this useful ?
	def __init__(self) :
		Object.__init__(self)
		self.dt = "UML - Note"
	def Set(self, d) :
		if self.props.has_key("text") :
			self.props["text"] += d
		else :
			self.props["text"] = d
	def Create(self) :
		if self.props.has_key("text") :
			dia.message(0, self.props["text"].encode("UTF-8"))
		return None
class Unknown(Object) :
	def __init__(self, name) :
		Object.__init__(self)
		self.dt = "svg:" + name
	def Create(self) :
		return None

class Importer :
	def __init__(self) :
		self.errors = {}
		self.objects = []
	def Parse(self, sData) :
		import xml.parsers.expat
		ctx = []
		# 3 handler functions
		def start_element(name, attrs) :
			#print "<" + name + ">"
			if 0 == string.find(name, "svg:") :
				name = name[4:]
			ctx.append(name) #push
			if 'g' == name : o = Group()
			else :
				s = string.capitalize(name) + "()"
				try :
					o = eval(s)
				except :
					o = Unknown(name)
			for a in attrs :
				ma = string.replace(a, "-", "_")
				# e.g. xlink:href -> xlink__href
				ma = string.replace(ma, ":", "__")
				s = "o." +  ma + "(\"" + attrs[a] + "\")"
				try :
					eval(s)
				except AttributeError, msg :
					if not self.errors.has_key(msg) :
						self.errors[msg] = s
				except SyntaxError, msg :
					if not self.errors.has_key(msg) :
						self.errors[msg] = s
			self.objects.append(o)
		def end_element(name):	
			del ctx[-1] # pop
		def char_data(data):
			# may be called multiple times for one string,
			if len(self.objects) > 0 : # FIXME
				self.objects[-1].Set(data)

		p = xml.parsers.expat.ParserCreate()
		p.StartElementHandler = start_element
		p.EndElementHandler = end_element
		p.CharacterDataHandler = char_data

		p.Parse(sData)
	def Render(self,data) :
		layer = data.active_layer
		for o in self.objects :
			od = o.Create()
			if od :
				layer.add_object(od)
		data.update_extents ()
		return 1
	def Dump(self) :
		for o in self.objects :
			print o
		for e in self.errors.keys() :
			print e, self.errors[e]

def Test() :
	import sys
	imp = Importer()
	sName = sys.argv[1]
	if sName[-1] == "z" :
		import gzip
		f = gzip.open(sName)
	else :
		f = open(sName)
	imp.Parse(f.read())
	if len(sys.argv) > 2 :
		sys.stdout = open(sys.argv[2], "wb")
	imp.Dump()
	sys.exit(0)

if __name__ == '__main__': Test()

def import_svg(sFile, diagramData) :
	imp = Importer()
	f = open(sFile)
	imp.Parse(f.read())
	return imp.Render(diagramData)

def import_svgz(sFile, diagramData) :
	import gzip
	imp = Importer()
	f = gzip.open(sFile)
	imp.Parse(f.read())
	return imp.Render(diagramData)

import dia
dia.register_import("SVG plain", "svg", import_svg)
dia.register_import("SVG compressed", "svgz", import_svgz)