#!/usr/bin/env python3
import sys
import os
import json
import time
import argparse
import psutil
sys.path.append(os.path.expanduser('~/lib'))
prog_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
sys.path.append(prog_dir)
os.chdir(prog_dir)
from dflib import rest
from dflib.debug import *
pid_file = '/tmp/get-data.pid'
data_path = '/Volumes/RamDisk/sensordata'

def is_running():
	'''
	determine if the daemon is running.
	check for an exisiting pid file, check the pid. 
	if the pid is running return true, otherwise false.
	'''
	global pid_file
	debug("Checking for running process")
	if os.path.exists(pid_file):
		debug("pid_file exists")
		with open(pid_file) as f:
			old_pid = int(f.read().strip())
		try:
			debug(f"Checking for pid {old_pid}")
			p = psutil.Process(old_pid)
			return True
		except psutil.NoSuchProcess:
			pass
	return False

def startup():
	'''
	Check if daemon is running if not gork and exit else just exit
	'''
	global pid_file
	if not get_debug():
		if is_running():
			log(f'daemon already running')
			sys.exit(0)

		pid = os.fork()
		if pid > 0:
			sys.exit(0)

		with open(pid_file,"w") as f:
			print(os.getpid(),file=f)

		log(f'Daemon started, pid: {os.getpid()}')
	else:
		debug("Debug mode no daemon")

def log(*args):
	'''
	Write to logfile also debug if debug is enabled
	'''
	tfmt = '%m-%d-%Y %H:%M'
	with open("/tmp/get-data.log","a") as f:
		now = time.time()
		lt = time.localtime(now)
		tstr = time.strftime(tfmt,lt)
		print(f'{tstr}:',*args,file=f)
		debug(*args)

def get_config():
	'''
	read common config file 
	'''
	try:
		with open('sensors.json') as f:
			return  json.load(f)
	except:
		return None
def main(base_dir):
	'''
	loop through defined sensors and write data to {base_dir}/{host}-{sensor}.json
	sleep for poll interval miliseconds
	'''
	config = None
	while not config:
		config = get_config()
		if not config:
			time.sleep(1)
	poll_interval = config['poll_interval']/1000
	while True:
		time.sleep(poll_interval)
		config = get_config()
		if not config:
			continue
		poll_interval = config['poll_interval']/1000
		for name,sensor in config['sensors'].items():
			if '::' in name:
				continue
			#if not sensor['active']:
			#	continue
			host = sensor['host']
			sen = sensor['sensor']
			server = config['server']
			debug(server,host,sensor)
			data_file = f'{base_dir}/{host}-{sen}.json'
			client = rest.RestClient(
				server=server,
				host=host,
				sensor=sen)
			try:
				sensor_data = client.read()
				if not 'error' in sensor_data:
					with open(data_file,'w') as f:
						debug("Writing",data_file)
						json.dump(sensor_data,f,indent=2)
			except Exception as e:
				with open('/tmp/get-data.log','a') as f:
					log(f'Exception getting data for {host}-{sen}: {e}')

if __name__ == "__main__":
	parser = argparse.ArgumentParser(
			prog=f"get-data",
			description="Sensor background data collection via SensorFS RestAPI",
			epilog="A SensorFS RestAPI Example. See https://github.com/nicciniamh/sensorfs"
		)
	parser.add_argument('-d','--debug',action='store_true',default=False,help='turn on copious debugging messages')
	args = parser.parse_args()
	set_debug(args.debug)
	try:
		startup()
		main(data_path)
	except KeyboardInterrupt:
		pass
	except Exception as e:
		log(f'Exception: {e}')
