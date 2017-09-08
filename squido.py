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
	{ "Ranked modes": ["area", "yagura", "hoko"] },
	{ "Turf war": ["fest", "nawabari"] },
	{ "All": ["area", "yagura", "hoko", "fest", "nawabari"] }
]
maps = [
	{ "All": ["kombu", "ama", "manta", "tachiuo", "fujitsubo", "hokke", "mystery", "gangaze", "chozame", "battera"] },
	{ "The Reef": ["battera"] },
	{ "Humpback Pump Track": ["kombu"] },
	{ "Inkblot Art Academy": ["ama"] },
	{ "Musselforge Fitness": ["fujitsubo"] },
	{ "Starfish Mainstage": ["gangaze"] },
	{ "Sturgeon Shipyard": ["chozame"] },
	{ "Moray Towers": ["tachiuo"] },
	{ "Port Mackerel": ["hokke"] },
	{ "Manta Maria": ["manta"] },
	{ "Shifty Station": ["mystery"] }
]

def help():
	print("No mode selected: Requires -u or -f flag. Usage: ")
	print("./squido.py [Flags]")
	print("-u [Name]: User to scrape stats from stat.ink")
	print("-f [File]: JSON file to read match stats from. If used with -u, archives user stats to file.")
	
def menu(items):
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
		data = data + datachunk
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
		if battle["map"] is not None: #make sure map was actually recognized
			if (battle["rule"]["key"] in mode_filter) and (battle["map"]["key"] in map_filter):
				filtered_battles.append(battle)
	weapons = {}
	#need to find a way to make this easier to rearrange
	legend = ["Weapon", "Wins", "Losses", "Win/Loss %", "Kills", "Assists", "Deaths", "Specials", "Special ratio", "Kill/Death ratio", "Kill+Assist/Death ratio",  "Kill rate average"]
	for battle in filtered_battles:
		cur_weapon = battle["weapon"]["key"]
		if battle["weapon"]["reskin_of"] is not None:
			#treat reskins as if they're the original, use the name of whichever gets found first
			cur_weapon = battle["weapon"]["reskin_of"]
		if cur_weapon not in weapons:
			weapons[cur_weapon] = [battle["weapon"]["name"]["en_US"],0,0,0,0,0,0,0,0,0,0,0]
		#total stats:
		if battle["result"] == "win":
			weapons[cur_weapon][1] += 1 #wins
		else:
			weapons[cur_weapon][2] += 1 #losses
		weapons[cur_weapon][4] += battle["kill"] #kills
		weapons[cur_weapon][5] += (battle["kill_or_assist"] - battle["kill"]) #assists
		weapons[cur_weapon][6] += battle["death"] #deaths
		weapons[cur_weapon][7] += battle["special"] #specials
		#turf logic? need to account for games missing data/games with shorter duration
		if battle["kill_rate"] is not None:
			#idk what the fuck this stat even means but stat.ink has it (percentage based kdr?)
			weapons[cur_weapon][11] += battle["kill_rate"]
	table = prettytable.PrettyTable(legend)
	table.float_format = ".2"
	# calculated stats:
	for w in weapons:
		weapons[w][3] = (weapons[w][1]/(weapons[w][1]+weapons[w][2])) #winrate
		if (weapons[w][1]+weapons[w][2])<10:
			#if a weapon has less than 10 battles played, invert the winrate so it sorts to the bottom
			weapons[w][3] = 0 - weapons[w][3]
		weapons[w][8] = (weapons[w][7]/(weapons[w][1]+weapons[w][2])) # special rate
		weapons[w][9] = (weapons[w][4]/weapons[w][6]) #kills/deaths
		weapons[w][10] = ((weapons[w][4]+weapons[w][5])/weapons[w][6])# kills+assists/deaths
		weapons[w][11] = (weapons[w][11]/(weapons[w][1]+weapons[w][2])) # average out the kill rate
		table.add_row(weapons[w])
	table.reversesort = True
	table.sortby = "Win/Loss %"
	print(mode_name + " on " + map_name)
	print(table)

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