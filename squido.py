#!/usr/bin/env python
#dumb squid stat analyzer by ice
import requests
import sys, getopt
import json
import prettytable

database = []
running = True

modes = [
	{ "Splat Zones": ["area"] },
	{ "Tower Control": ["yagura"] },
	{ "Rainmaker": ["hoko"] },
	{ "Clam Blitz": ["asari"]},
	{ "Ranked modes": ["area", "yagura", "hoko", "asari"] },
	{ "Turf war": ["fest", "nawabari"] },
	{ "All": ["area", "yagura", "hoko", "fest", "nawabari", "asari"] }
]
maps = [
	{ "All": ["kombu", "ama", "manta", "tachiuo", "fujitsubo", "hokke", "mystery", "gangaze", "chozame", "battera", "bbass", "devon", "engawa", "hakofugu", "mozuku", "zatou"] },
	{ "The Reef": ["battera"] },
	{ "Humpback Pump Track": ["kombu"] },
	{ "Inkblot Art Academy": ["ama"] },
	{ "Musselforge Fitness": ["fujitsubo"] },
	{ "Starfish Mainstage": ["gangaze"] },
	{ "Sturgeon Shipyard": ["chozame"] },
	{ "Moray Towers": ["tachiuo"] },
	{ "Port Mackerel": ["hokke"] },
	{ "Manta Maria": ["manta"] },
	{ "Blackbelly Skatepark": ["bbass"] },
	{ "Shellendorf Institute": ["devon"] },
	{ "Snapper Canal": ["engawa"] },
	{ "Walleye Warehouse": ["hakofugu"] },
	{ "Kelp Dome": ["mozuku"] },
	{ "MakoMart": ["zatou"] },
	{ "Shifty Station": ["mystery"] }
]

def help():
	print("No mode selected: Requires -u or -f flag. Usage: ")
	print("./squido.py [Flags]")
	print("-u [Name]: User to scrape stats from stat.ink")
	print("-f [File]: JSON file to read match stats from. If used with -u, archives user stats to file.")

def sanitize_db(database):
	nomap = 0
	nomode = 0
	nowep = 0
	orig_total = len(database)
	for battle in database:
		bad = False
		if battle["map"] is None:
			nomap += 1
			bad = True
		if battle["rule"] is None:
			nomode += 1
			bad = True
		if battle["weapon"] is None:
			nowep += 1
			bad = True
		if bad:
			database.remove(battle)
	if (nomap != 0) or (nomode != 0) or (nowep != 0):
		print("Had " + str(orig_total) + " battles")
		print("Found " + str(nomap) + " maps missing, " + str(nomode) + " modes missing, and " + str(nowep) + " weapons missing")
		print("Now have " + str(len(database)) + " battles")
	return database 
	
def menu(items):
	global database
	database = sanitize_db(database)
	while True:
		for item in items:
			print("[" + str(items.index(item)+1) + "] " + list(item)[0])
		choice = input(">> ")
		try:
			choice = int(choice)-1
			if choice < 0 : raise ValueError
			return items[choice]
		except (ValueError, IndexError):
			pass

def retrieve_statink(username):
	print("Retrieving data for user " + username)
	# https://stat.ink/api/v2/battle?screen_name=[User]&count=50
	data = []
	done = False
	counter = "999999" 
	s = requests.Session()
	#repeat requests until we have a page with less than 50 results
	while not done:
		r = s.get("https://stat.ink/api/v2/battle",params={"screen_name": username,"count": "50","older_than":counter})
		datachunk = r.json()
		if len(datachunk) < 50:
			done = True
		else:
			counter = datachunk[49]["id"]
		try:
			data = data + datachunk
		except:
			print("Error retrieving data (possible bad username")
			return []
	return data

def retrieve_jsonfile(filename):
	try:
		f = open(filename, 'r')
	except:
		print("Could not open file " + filename)
		sys.exit(1)
	print("Reading data from file " + filename)
	data = json.load(f)
	return data

def write_jsonfile(filename, data):
	try:
		f = open(filename, 'w')
	except:
		print("Could not open file " + filename)
		sys.exit(1)
	f.write(json.dumps(data))
	f.close()
	
def statink_handler():
	global database
	print("Enter stat.ink username")
	choice = input(">> ")
	database = retrieve_statink(choice)

def filewrite_handler():
	global database
	print("Enter filename")
	choice = input(">> ")
	write_jsonfile(choice, database)
	
def fileread_handler():
	global database
	print("Enter filename")
	choice = input(">> ")
	database = retrieve_jsonfile(choice)
	
def mapmode_analyze():
	global database
	print("Select mode:")
	selected = menu(modes)
	mode_filter = list(selected.values())[0]
	mode_name = list(selected)[0]
	print("Select map:")
	selected = menu(maps)
	map_filter = list(selected.values())[0]
	map_name = list(selected)[0]
	filtered_battles = []
	#filter battles based on selection
	for battle in database:
		if (battle["map"] is not None) and (battle["rule"] is not None): #make sure map was actually recognized
			if (battle["rule"]["key"] in mode_filter) and (battle["map"]["key"] in map_filter):
				filtered_battles.append(battle)
	weapons = {}
	#legend can be rearranged to reorganize final table
	legend = ["Weapon", "WLR", "KDR", "ADR", "SR", "TR", "AGL", "Wins", "Losses", "Kills", "Assists", "Deaths", "Specials", "Turf", "Game Time"]
	internal = ["TG"]
	for battle in filtered_battles:
		cur_weapon = battle["weapon"]["key"]
		if battle["weapon"]["reskin_of"] is not None:
			#treat reskins as if they're the original, use the name of whichever gets found first
			cur_weapon = battle["weapon"]["reskin_of"]
		if cur_weapon not in weapons:
			weapons[cur_weapon] = {}
			weapons[cur_weapon]["Weapon"] = battle["weapon"]["name"]["en_US"]
			weapons[cur_weapon]["tg"] = 0 #internal counter for games with turf data
			for stat in legend:
				if stat != "Weapon":
					weapons[cur_weapon][stat] = 0
			for stat in internal:
				weapons[cur_weapon][stat] = 0
			#weapons[cur_weapon] = [battle["weapon"]["name"]["en_US"],0,0,0,0,0,0,0,0,0,0,0]
		#totaled stats:
		if battle["result"] == "win":
			weapons[cur_weapon]["Wins"] += 1 #wins
		else:
			weapons[cur_weapon]["Losses"] += 1 #losses
		weapons[cur_weapon]["Kills"] += battle["kill"] #kills
		weapons[cur_weapon]["Assists"] += (battle["kill_or_assist"] - battle["kill"]) #assists
		weapons[cur_weapon]["Deaths"] += battle["death"] #deaths
		weapons[cur_weapon]["Specials"] += battle["special"] #specials
		game_time = battle["end_at"]["time"] - battle["start_at"]["time"]
		weapons[cur_weapon]["Game Time"] += game_time
		if battle["my_point"] is not None:
			weapons[cur_weapon]["TG"] += 1
			weapons[cur_weapon]["Turf"] += battle["my_point"]
			weapons[cur_weapon]["TR"] += battle["my_point"]/(game_time/60)
		#if battle["kill_rate"] is not None:
		#	#idk what the fuck this stat even means but stat.ink has it (percentage based kdr?)
		#	weapons[cur_weapon]["KRA"] += battle["kill_rate"]
	table = prettytable.PrettyTable(legend)
	table.float_format = ".2"
	# calculated stats:
	for w in weapons:
		total_games = weapons[w]["Wins"]+weapons[w]["Losses"]
		weapons[w]["WLR"] = (weapons[w]["Wins"]/total_games) #winrate
		if weapons[w]["TG"] != 0:
			weapons[w]["TR"] = weapons[w]["TR"]/weapons[w]["TG"]
		else:
			weapons[w]["TR"] = 0
		weapons[w]["AGL"] = (weapons[w]["Game Time"]/total_games) #average game length
		if (total_games)<10:
			#if a weapon has less than 10 battles played, invert the winrate so it sorts to the bottom
			weapons[w]["WLR"] = 0 - weapons[w]["WLR"]
		weapons[w]["SR"] = (weapons[w]["Specials"]/total_games) # special rate
		if weapons[w]["Deaths"] == 0:
			weapons[w]["KDR"] = 999
			weapons[w]["ADR"] = 999
		else:
			weapons[w]["KDR"] = (weapons[w]["Kills"]/weapons[w]["Deaths"]) #kills/deaths
			weapons[w]["ADR"] = ((weapons[w]["Kills"]+weapons[w]["Assists"])/weapons[w]["Deaths"])# kills+assists/deaths
		#weapons[w]["KRA"] = (weapons[w]["KRA"]/total_games) # average out the kill rate
		new_row = []
		for item in legend:
			new_row.append(weapons[w][item])
		table.add_row(new_row)
	table.reversesort = True
	table.sortby = "WLR"
	table.align = "l"
	print(mode_name + " on " + map_name)
	print(table)
	print("WLR = Wins/Losses, KDR = Kills/Deaths, ADR = Assists+Kills/Deaths, SR = Specials/Game, TR = Turf/Minute, AGL = Game Time/Games played")

def weapon_analyze():
	global database
	weapon_selector = []
	#scan every battle for weapons with data for an easier to manage list
	for battle in database:
		cur_weapon = battle["weapon"]["key"]
		if battle["weapon"]["reskin_of"] is not None:
			cur_weapon = battle["weapon"]["reskin_of"]
		if weapon_selector == []:
			#always add the first weapon found
			weapon_selector.append({battle["weapon"]["name"]["en_US"]: cur_weapon})
		else:
			new = True
			for wep in weapon_selector:
				if cur_weapon == wep[list(wep)[0]]:
					#Check every weapon found so far, ignore if it's already added
					new = False
			if new:
				weapon_selector.append({battle["weapon"]["name"]["en_US"]: cur_weapon})
	print("Select weapon:")
	selected_weapon = menu(weapon_selector)
	print(selected_weapon)
	
main_menu = [
    { "Load battles from stat.ink": statink_handler },
    { "Load battles from file": fileread_handler },
	{ "Write battles to file": filewrite_handler },
	{ "Analyze mode/map combo": mapmode_analyze },
	{ "Analyze weapon": weapon_analyze },
    { "Exit": exit }
]
	
def main():
	global database
	while running:
		print("Battles loaded: " + str(len(database)))
		#some magic shit
		list(menu(main_menu).values())[0]()

def load(argv):
	global database
	try:
		opts, args = getopt.getopt(argv,"hu:f:")
	except getopt.GetoptError:
		help()
		sys.exit(2)
	username = ""
	filename = ""
	for opt, arg in opts:
		if opt == "-u":
			username = arg
		elif opt == "-f":
			filename = arg
		elif opt == "-h":
			help()
			sys.exit(0)
	battles = []
	if username != "":
		battles = retrieve_statink(username)
		print("Retrieved data for user " + username)
	if filename != "":
		if battles != []:
			write_jsonfile(filename, battles)
			print("Wrote data for user " + username + " to file " + filename)
		else:
			battles = retrieve_jsonfile(filename)
			print("Loaded data from file " + filename)
	database = battles
	main()
	sys.exit(0)
		
if __name__ == "__main__":
	load(sys.argv[1:])
