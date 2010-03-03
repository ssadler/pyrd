#!/usr/bin/env python

import sys, os, time, re, math, urllib, socket, speedstack, fcntl, termios, struct, getopt
from urlparse import urlparse
from functools import partial
from cStringIO import StringIO

termcolors = {
	'black': '0;30',
	#'blue': '0;34',
	#'green': '0;32',
	'cyan': '36',
	#'red': '0;31',
	'purple': '35',
	#'brown': '0;33',
	#'l_grey': '0;37',
	#'d_grey': '1;30',
	#'l_blue': '1;34',
	#'l_green': '1;32',
	#'l_cyan': '1;36',
	#'l_red': '1;31',
	#'l_purple': '1;35',
	#'white': '1;37',
	'h_white': '47',
	'h_red': '41',
	'h_green': '42',
	'yellow': '33',
}
"""
'grey': '\033[1;30m%s\033[1;m',
'red': '\033[1;31m%s\033[1;m',
'green': '\033[1;32m%s\033[1;m',
'yellow': '\033[1;33m%s\033[1;m',
'blue': '\033[1;34m%s\033[1;m',
'magenta': '\033[1;35m%s\033[1;m',
'cyan': '\033[1;36m%s\033[1;m',
'white': '\033[1;37m%s\033[1;m',
'crimson': '\033[1;38m%s\033[1;m',
'h_red': '\033[1;41m%s\033[1;m',
'h_green': '\033[1;42m%s\033[1;m',
'hbrown': '\033[1;43m%s\033[1;m',
'hblue': '\033[1;44m%s\033[1;m',
'hmagenta': '\033[1;45m%s\033[1;m',
'hcyan': '\033[1;46m%s\033[1;m',
'hgrey': '\033[1;47m%s\033[1;m',
'hcrimson': '\033[1;48m%s\033[1;m'
"""

def format_bytes(b):
	if b == None: return 'Unknown'
	if b < 1000: return "%dB" % b
	if b < 1000000: return "%.1fK" % (math.floor(b/102.4)/10)
	if b < 1000000000: return "%.1eM" % (math.floor(b/104857.6)/10)
	return "%.1fG" % (math.floor(b/107374182.4)/10)

def get_terminal_size():
	### decide on *some* terminal size
	# try open fds
	cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
	if not cr:
		# ...then ctty
		try:
			fd = os.open(os.ctermid(), os.O_RDONLY)
			cr = ioctl_GWINSZ(fd)
			os.close(fd)
		except:
			pass
		if not cr:
			# env vars or finally defaults
			try:
				cr = (env['LINES'], env['COLUMNS'])
			except:
				cr = (25, 80)
	# reverse rows, cols
	return int(cr[1]), int(cr[0])


class Client():
	pass

class HTTPClient(Client):
	useragent = "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.3) Gecko/2008100320 Firefox/3.0.1"
	cookies = {}
	maxredirs = 3
	verbose = True

	def __init__(self, teller, verbose=False):
		self.c_tell = teller
		self.verbose = verbose
	
	def getresponse(self, uri, offset):
		history = [uri]
		for i in xrange(self.maxredirs):
			headers = self.getrequestheaders(history[-1], offset)
			port = uri.port if uri.port else 80
			s = socket.socket()
			s.connect((uri.hostname, port))
			s.sendall(headers)
			if self.verbose: self.c_tell(headers, color="h_red")
			try:
				response = self.__class__.HTTPResponse(s, self)
				acceptcode = [200]
				if offset:
					acceptcode.append(206)
				if not response.code in acceptcode:
					raise Exception('Bad response code: ' + str(response.code))
				return (response, history)
			except self.HTTPResponse.HTTPRedirect, e:
				history.append(e.uri)
				s.close()
		s.close()
		raise Exception("Redirect limit reached")

	class HTTPResponse():
		bufsize = 4096
		def __init__(self, s, client, verbose=False):
			self.s = s
			self.rawheaders = self.__class__.readrawheaders(self.s)
			self.client = client
			if self.client.verbose:
				self.client.c_tell(self.rawheaders, color="h_green")
			headerdata = self.parseresponseheaders(self.rawheaders)
			self.code, self.contentlen, self.offset, redirecturi, self.filename = headerdata
			if redirecturi:
				raise self.HTTPRedirect(redirecturi)


		def recvall(self, writer, progress_callback):
			
			recvtime = 0.2
			self.s.settimeout(recvtime)
			
			idletime = 0.0
			maxidletime = 60.0
			
			while True:
				try:
					while True:
						progress_callback(self.offset, download.WORKING)
						chunk = self.s.recv(self.bufsize)
						idletime = 0
						chunklen = len(chunk)
						if not chunklen:
							progress_callback(self.offset, download.COMPLETE)
							self.s.shutdown(socket.SHUT_RDWR)
							self.s.close()
							return
						self.offset += chunklen
						writer(chunk)
				except socket.timeout:
					idletime += recvtime
					if idletime >= maxidletime:
						progress_callback(self.offset, download.STALLED)
						self.s.shutdown(socket.SHUT_RDWR)
						self.s.close()
						raise self.Timeout()

		def getoffset(self):
			return self.offset
		
		def getcontentlen(self):
			return self.contentlen


		class HTTPRedirect(Exception):
			def __init__(self, uri):
				self.uri = uri
	
		class Timeout(Exception): pass


		@staticmethod
		def readrawheaders(s):
			chunk = StringIO()
			last4 = '    '
			for i in xrange(1024):
				b = s.recv(1)
				chunk.write(b)
				last4 = last4[1:] + b
				if last4 == "\r\n\r\n":
					chunk = chunk.getvalue()
					if chunk[:4] == 'HTTP':
						return chunk
			raise Exception("Invalid Response headers")

		
		def parseresponseheaders(self, rawheaders):
			headers = [line.strip() for line in rawheaders.strip().splitlines()]
			contentlen = None
			responsecode = None
			offset = 0
			redirecturi = None
			filename = None
			for header in headers:
				if header.lower().startswith('location: '):
					redirecturi = urlparse(header[10:].strip())
				if contentlen == None and header.lower().startswith('content-length: '):
					contentlen = int(header[16:])
				if header.startswith('HTTP'):
					responsecode = int(header[9:12])
				if header.lower().startswith('set-cookie: '):
					cookiedata = re.findall('(\w+)=([^;]+)',header[12:])
					name, value = cookiedata.pop(0)
					cookiedata = dict(cookiedata)
					#if not 'domain' in cookiedata: cookiedata['domain'] = uri.hostname
					if not 'path' in cookiedata: cookiedata['path'] = '/'
					self.client.cookies[name] = ("%s=%s" % (name,value), cookiedata)
				if header.lower().startswith('content-range: '):
					m = re.compile('.*?bytes (\d+)-(\d+)/(\d+)').match(header)
					offset, contentlen = (int(m.group(1)), int(m.group(3)))

				if header.lower().startswith('content-disposition: '):
					filename = re.findall('^.*?filename=([^\s]+)$', header).pop(0)[0]

			return (responsecode, contentlen, offset, redirecturi, filename)

	



	def setcookie(self, host, cookie, path):
		name, value = cookie.split('=', 1)
		self.cookies[name] = (cookie, {'domain': host, 'path': path})
	
	def getrequestheaders(self, uri, offset=None):
		path = uri.path if uri.path else '/' + ("?" + uri.query if uri.query else '')
		headers = [
			"GET %s HTTP/1.1" % path,
			"Host: " + uri.hostname,
			"User-Agent: " + self.useragent,
			"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
			"Accept-Language: en-us,en;q=0.5",
			"Accept-Encoding: None",
			"Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7",
			"Connection: Close",
			#"Keep-Alive: 300",
		]
		if offset:
			headers.append('Range: bytes=%d-' % offset)
		for cookiename, cookiedata in self.cookies.items():
			rawcookie, cookieattributes = cookiedata
			if not uri.hostname.endswith(cookieattributes['domain'].strip('.')):
				break
			if not path.startswith(cookieattributes['path']):
				break
			headers.append("Cookie: " + rawcookie)

		return "\r\n".join(headers) + "\r\n\r\n"
	
		raise Exception('Invalid headers recieved:\n' + chunk.getvalue())


class download():
	
	STARTING = 0
	COMPLETE = 0
	WORKING = 1
	STALLED = 2
	ERROR = 3

	@classmethod
	def download(cls, uristr, dlpath, speedlimit=None, verbose=False):

		dlpath = os.path.abspath(dlpath)
		uri = urlparse(uristr)
		cls.tell("Downloading " + uristr)
		filename = os.path.basename(urllib.url2pathname(uri.path)) or uri.hostname
		filepath = os.path.join(dlpath, filename)
		if os.path.isfile(filepath):
			cls.tell("File exists: \"%s\", skipping" % filename)
			return
		tmpfilepath = filepath + '.pyrdpart'
		tmpfile = open(tmpfilepath, 'ab')
		
		client = HTTPClient(cls.tell, verbose=verbose)
		if uri.scheme.startswith('http') and 'RAPIDSHARE_COOKIE' in os.environ:
			client.setcookie('rapidshare.com', os.environ['RAPIDSHARE_COOKIE'], '/')
		
		speedlimit = speedlimit or 0
		
		delay = 60
		while True:
			try:
				offset = tmpfile.tell()
				response, history = client.getresponse(uri, offset)
				r_offset = response.getoffset()
				if r_offset != offset:
					print "Server does not support resume, truncating"
					tmpfile.seek(r_offset)
					tmpfile.truncate()
				ss = speedstack.create(speedlimit, 0.2)
				display = TerminalProgress(filename, response.getcontentlen())
				progress_update = partial(cls.progress_update, ss, display)
				response.recvall(tmpfile.write, progress_update)
				break
			except HTTPClient.HTTPResponse.Timeout:
				cls.tell("Download timed out. Delaying for %d seconds." % delay)
				time.sleep(delay)
			except socket.gaierror:
				print socket.gaierror
				cls.tell("Socket error. Delaying for %d seconds." % delay)
				time.sleep(delay)
		
		tmpfile.close()
		os.rename(tmpfilepath, filepath)





	@staticmethod
	def truncatefile(file, offset):
		file.seek(offset)
		file.truncate()
	
	@classmethod
	def progress_update(cls, ss, display, offset, state):
		force = state == cls.COMPLETE
		speed = speedstack.update(ss, int(offset), int(force))
		if speed != None:
			display.update(offset, speed)

	@staticmethod
	def tell(str, color=None):
		if color:
			str = "\033[%sm%s\033[1;m" % (termcolors[color], str)
		print str



class TerminalProgress():
	def __init__(self, filename, contentlen):
		self.contentlen = contentlen or None
		self.filename = ' ' + filename

	
	def update(self, current, speed):
		# ^Ci-7.2.25-1-i686           3.4M   62.1K/s 00:01:18 [###################---------------------------]  41%
		percent = float(current) / float(self.contentlen) if self.contentlen else None
		
		out = []
		out.append("%7s" % format_bytes(current))
		out.append("%7s/s" % format_bytes(speed))
		
		
		eta = "  Unknown"
		if speed > 0 and percent:
			secs = math.ceil(self.contentlen * (1-percent) / speed)
			h, m, s = (secs / 3600, (secs % 3600) / 60, secs % 60)
			if h < 100:
				eta = '  %02d:%02d:%02d' % (h, m, s)
		out.append(eta)

		
		

		meterchars = 20
		filled = int(math.floor(percent*meterchars)) if percent else 0
		notfilled = meterchars - filled
		out += ["  [", "#" * filled, "-" * notfilled, "]"]
		
		if percent: out.append("%4d%%" % int(math.floor(percent*100.0)))

		out.append(" ")
		
		out = [''.join(out)]
		fnamechars = get_terminal_size()[0] - len(out[0])
		if len(self.filename) <= fnamechars:
			fname = self.filename.ljust(fnamechars)
		else:
			fname = self.filename[:fnamechars]

		out = ''.join([fname]+out)
		
		out = self.__class__.colorise(out, 'h_white')
		out = self.__class__.colorise(out, "black")
		
		sys.stdout.write("\r" + out)
		sys.stdout.flush()


	@staticmethod
	def colorise(data, color, bold=False):
		code = ('1;' if bold else '') + termcolors[color]
		return "\033[%sm%s\033[1;m" % (code, data) 


		

def getsocket(host, proxy=None):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(host)
	return s

def socket_check(s):
	readable, writeable, in_error = select.select([s], [s], [s], 5)
	return (s in readable, s in writeable, s in in_error)
	


def get_opts(argv=None, stdin=None):
	if not argv: argv = sys.argv[1:]
	if not stdin: stdin = sys.stdin

	cmdopts = {'-l': None, '--speedlimit': None}
	cmdoptlist, args = getopt.getopt(argv, 'l:v',['speedlimit=', 'proxy='])
	
	cmdopts.update(dict(cmdoptlist))
	opts = {}
	opts['speedlimit'] = int(cmdopts['-l'] or cmdopts['--speedlimit'] or 0) * 1024 or None
	opts['dlpath'] = '.'
	opts['verbose'] = '-v' in cmdoptlist
	
	re_uri = re.compile('^\w+://')

	if len(args) > 1:
		raise Exception('Too many args')
	if len(args) == 0 or args[0] == '-':
		urilist = stdin.readlines()
	elif re_uri.match(args[0]):
		urilist = args[0].splitlines()
	else:
		f = open(args[0])
		urilist = f.readlines()
		f.close()
		opts['dlpath'] = os.path.dirname(os.path.abspath(args[0]))
	
	urilist = [uri.strip() for uri in urilist if re_uri.match(uri)]
	opts['urllist'] = urilist
	
	return opts

def main():
	opts = get_opts()
	for uristr in opts['urllist']:
		download.download(uristr, opts['dlpath'], opts['speedlimit'])

def ioctl_GWINSZ(fd): #### TABULATION FUNCTIONS
	try: ### Discover terminal width
		return struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
	except:
		return None




if __name__ == '__main__':
	main()




