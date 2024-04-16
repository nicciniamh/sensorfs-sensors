"""
debugging tools
debugging and error messages are printed to stderr with a debug or error tag in color
along with the name of the calling funciton and it's caller.
"""
import inspect
import sys
import os
import pprint

debug_flag = False

def set_debug(flag):
	''' turn debugging on and off with boolean '''
	global debug_flag
	debug_flag = flag

def get_debug():
	''' get debug state as boolean '''
	global debug_flag
	return debug_flag

def _get_caller():
	''' Get information about the caller '''
	caller_frame = inspect.stack()[1]
	caller_function = caller_frame.function
	caller_module = inspect.getmodule(caller_frame[0]).__name__
	return caller_module, caller_function

def _get_grand_caller():
	''' Get information about the caller of the caller (grand caller) '''
	grand_caller_frame = inspect.stack()[2]
	grand_caller_function = grand_caller_frame.function
	grand_caller_module = inspect.getmodule(grand_caller_frame[0]).__name__
	return grand_caller_module, grand_caller_function


def _output(caller, tag,*args):
	'''
	colorize and print output
	'''
	print(f'{tag} - \033[1;36;40m{caller}\033[0m :\033[1;37;40m',*args, '\033[0m',file=sys.stderr)

def debug(*args):
	''' print *args as debug message with caller '''
	global debug_flag
	if debug_flag:
		frames = inspect.stack()
		grandcaller = frames[3] if len(frames) >= 4 else None
		gc='~none~'
		if grandcaller:
			grandcaller_file = os.path.basename(grandcaller.filename)
			grandcaller_line = grandcaller.lineno
			grandcaller_function = grandcaller.function
			gc=f"{grandcaller_file}:{grandcaller_line} {grandcaller_function}"

		frame = inspect.getouterframes(inspect.currentframe(), 2)[1]
		caller = frame[3]
		file = os.path.basename(frame[1])
		line = frame[2]
		cs = f'{file}:{line} {caller}'

		caller_text = f'{gc}->{cs}'
		tag = '\x1b[1;34;40mDEBUG\x1b[0m'
		_output(caller_text, tag, *args)

def error(*args):
	''' print *args as message message with caller '''
	global debug_flag
	if debug_flag:
		frames = inspect.stack()
		grandcaller = frames[3] if len(frames) >= 4 else None
		gc='~none~'
		if grandcaller:
			grandcaller_file = os.path.basename(grandcaller.filename)
			grandcaller_line = grandcaller.lineno
			grandcaller_function = grandcaller.function
			gc=f"{grandcaller_file}:{grandcaller_line} {grandcaller_function}"

		frame = inspect.getouterframes(inspect.currentframe(), 2)[1]
		caller = frame[3]
		file = os.path.basename(frame[1])
		line = frame[2]
		cs = f'{file}:{line} {caller}'

		caller_text = f'{gc}->{cs}'
		tag = '\x1b[1;34;40mDEBUG\x1b[0m'
		_output(caller,'\x1b[1;31;40mERROR\x1b[0m',*args)

def dump_object_properties(obj,tag=None):
	''' dump dict/object properties - dont use use dpprint instead '''
	global debug_flag
	if not type(obj) is dict:
		obj = obj.__dict__
	caller = inspect.getouterframes(inspect.currentframe(), 2)[1][3]
	if not tag:
		tag = f'{obj}'
	if debug_flag:
		props = []
		for k,v in obj.items():
			props.append(f'\t{k}={v}')
		props = '\n'.join(props)
		_output(caller,'\x1b[1;34;40mDEBUG\x1b[0m',f'properties for {tag}\n{props}')

def dpprint(obj,*args,**kwargs):
	''' debug wrapper for pprint. Each line is output as a debug message. '''
	if debug_flag:
		frames = inspect.stack()
		grandcaller = frames[3] if len(frames) >= 4 else None
		gc='~none~'
		if grandcaller:
			grandcaller_file = os.path.basename(grandcaller.filename)
			grandcaller_line = grandcaller.lineno
			grandcaller_function = grandcaller.function
			gc=f"{grandcaller_file}:{grandcaller_line} {grandcaller_function}"

		frame = inspect.getouterframes(inspect.currentframe(), 2)[1]
		caller = frame[3]
		file = os.path.basename(frame[1])
		line = frame[2]
		cs = f'{file}:{line} {caller}'

		caller_text = f'{gc}->{cs}'
		strings = pprint.pformat(obj,*args,**kwargs).split('\n')
		for s in strings:
			_output(caller,'\x1b[1;34;40mDEBUG\x1b[0m',s)