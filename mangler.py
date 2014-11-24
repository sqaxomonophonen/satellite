#!/usr/bin/env python

import os
import sys
import time
import datetime
import math
import json

db = {}

def dbmerge(norad, data, ifexists = False):
	if norad not in db:
		if ifexists:
			return
		db[norad] = {}
	elif "epoch" in data and "epoch" in db[norad] and data["epoch"] < db[norad]["epoch"]:
		return
	for k in data.keys():
		db[norad][k] = data[k]

if len(sys.argv) < 2:
	sys.stderr.write("usage: %s <file> [file...]" % sys.argv[0])
	sys.exit(1)

def read_lines(path):
	with open(path) as f:
		return f.readlines()

def is_tle(lines):
	total = 0
	tles = 0
	for line in lines:
		line = line.strip()
		if len(line) == 0: continue
		total += 1
		if len(line) == 69:
			tles += 1
	return tles > total/2

def parse_tle(lines, set):
	name = ""
	norad = None
	classification = None
	epoch = None
	intn = None

	for line in lines:
		line = line.strip()
		if len(line) == 0: continue

		if len(line) == 69:
			# CHECKSUM
			chksum = 0
			for c in line[0:68]:
				if c >= "0" and c <= "9":
					chksum += int(c)
				elif c == "-":
					chksum += 1
			chksum %= 10
			if (chksum) != int(line[68:69]):
				raise ValueError("checksum fail (%d) for TLE line: %s" % (chksum, line))


			# helper functions
			def get_line_number():
				if line[0:2] == "1 ":
					return 1
				elif line[0:2] == "2 ":
					return 2
				else:
					raise ValueError("invalid TLE line: %s" % line)

			def get_norad():
				return line[2:7]


			ln = get_line_number()

			# LINE 1
			if ln == 1:
				norad = get_norad()
				classification = line[7:8]
				intn = line[9:17]
				e = line[18:32]
				yy = int(e[0:2])
				yyyy = 1900 + yy if yy > 56 else 2000 + yy
				days = float(e[2:])
				epoch = datetime.datetime(yyyy,1,1) + datetime.timedelta(days)

			# LINE 2
			elif ln == 2:
				if get_norad() != norad:
					raise ValueError("norad number mismatch: %s vs %s" % (norad, get_norad()))
				inclination = float(line[8:16])
				right_ascension_of_ascending_node = float(line[17:25])
				eccentricity = float("0." + line[26:33])
				argument_of_perigee = float(line[34:42])
				mean_anomaly = float(line[43:51])
				mean_motion = float(line[52:63])
				revolution_number = int(line[63:68])
				dbmerge(norad, {
					"name": name,
					"set": set,
					"classification": classification,
					"epoch": epoch,
					"intn": intn,
					"inclination": inclination,
					"right_ascension_of_ascending_node": right_ascension_of_ascending_node,
					"eccentricity": eccentricity,
					"argument_of_perigee": argument_of_perigee,
					"mean_anomaly": mean_anomaly,
					"mean_motion": mean_motion,
					"revolution_number": revolution_number,
				})
		else:
			name = line.strip()

def is_satcat(lines):
	return len(lines[0]) == 134 and len(lines[-1]) == 134

def parse_satcat(lines):
	for line in lines:
		norad = line[13:18]
		owner = line[49:56].strip()
		dbmerge(norad, {"owner": owner}, True)

for path in sys.argv[1:]:
	lines = read_lines(path)

	if is_tle(lines):
		print "TLE %s ..." % path
		parse_tle(lines, os.path.splitext(os.path.basename(path))[0])
	elif is_satcat(lines):
		print "SATCAT %s ..." % path
		parse_satcat(lines)
	else:
		raise ValueError("cannot parse %s: could not guess filetype" % path)

max_epoch = max([v['epoch'] for v in db.values()])

print "writing data0.js ..."
data0 = {"_epoch": long(long(time.mktime(max_epoch.timetuple())) * 1e3 + max_epoch.microsecond / 1e3)}
for k,v in db.items():
	if v['set'] not in data0:
		data0[v['set']] = []
	M0 = v['mean_anomaly']
	dd = max_epoch - v['epoch']
	M = M0 + 360.0 * (dd.total_seconds() / (24.0*60.0*60.0) / v['mean_motion'])
	M %= 360.0
	data0[v['set']].append([
		k,
		v['inclination'],
		v['right_ascension_of_ascending_node'],
		v['eccentricity'],
		v['argument_of_perigee'],
		M,
		v['mean_motion'],
		('owner' in v) and v['owner'] or "?"
	])
with open("data0.js", "w") as f: f.write("var data0=" + json.dumps(data0, cls = json.JSONEncoder).replace(" ", "") + ";\n")
