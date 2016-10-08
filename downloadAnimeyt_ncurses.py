#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Librerías del sistema
import sys, os

# Librerías web
import urllib, urllib2, cookielib

# Librerías útiles
import re, curses, traceback, threading, time

class CursedMenu(object):
	'''A class which abstracts the horrors of building a curses-based menu system'''

	def __init__(self, directorio):
		'''Initialization'''
		self.block = False
		self.directorio = directorio
		self.screen = curses.initscr()
		curses.noecho()
		curses.cbreak()
		curses.start_color()
		self.screen.keypad(1)
		self.animes = getAllAnimes()
		#options = ['First', 'casa', 'perro', 'coche', 'gato', 'lapiz', 'goma', 'casandra', 'tortuga', 'gato', 'paella', 'ingles']
		options = map(lambda x: x[1], self.animes)
		self.pila = [{'title':'Escribe un anime a buscar:', 'subtitle':'Opciones', 'options':options, 'original':options, 'filter':''}]

		# Highlighted and Normal line definitions
		curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
		self.highlighted = curses.color_pair(1)
		self.normal = curses.A_NORMAL
		self.show(self.pila[-1]['options'][:9], title=self.pila[-1]['title'], subtitle=self.pila[-1]['subtitle'])


	def show(self, options, title="Title", subtitle="Subtitle"):
		'''Draws a menu with the given parameters'''
		self.set_options(options)
		self.title = title
		self.subtitle = subtitle
		self.selected = 0
		if not self.block:
			self.draw_menu()
		else:
			self.draw()

	def set_options(self, options):
		'''Validates that the last option is "Exit"'''
		if options == [] or options[-1] is not 'Exit':
			options.append('Exit')
		self.options = options


	def draw_menu(self):
		'''Actually draws the menu and handles branching'''
		request = ""
		try:
			while request is not "Exit":
				self.draw()
				request = self.get_user_input()
				self.handle_request(request)
			self.__exit__()

		# Also calls __exit__, but adds traceback after
		except Exception as exception:
			self.__exit__()
			traceback.print_exc()


	def draw(self):
		'''Draw the menu and lines'''
		self.screen.border(0)
		self.screen.addstr(2,2, self.title, curses.A_STANDOUT) # Title for this menu
		self.screen.addstr(4,2, self.subtitle, curses.A_BOLD) #Subtitle for this menu

		# Display all the menu items, showing the 'pos' item highlighted
		for index in range(len(self.options)):
			textstyle = self.normal
			if index == self.selected:
				textstyle = self.highlighted
			self.screen.addstr(5+index,4, "%d - %s" % (index+1, self.options[index]), textstyle)

		self.screen.refresh()


	def get_user_input(self):
		if not self.block:
			'''Gets the user's input and acts appropriately'''
			user_in = self.screen.getch() # Gets user input

			'''Enter and Exit Keys are special cases'''
			if user_in == 10:
				return self.options[self.selected]
			if user_in == 27:
				return self.options[-1]
			
			# Si borramos elemento del filtro
			if user_in == 263:
				self.pila[-1]['filter'] = self.pila[-1]['filter'][:-1]
				filtro = self.pila[-1]['filter']
				self.screen.clear()
				options = self.pila[-1]['original']
				options = filter(lambda x: filtro.lower() in x.lower(), options)
				title = self.pila[-1]['filter']
				if title == "":
					title = self.pila[-1]['title']
				else:
					title = "Filtrando por: "+title
				self.show(options[:9], title=title, subtitle=self.pila[-1]['subtitle'])
			
			if user_in >= ord('a') and user_in <= ord('z') or user_in >= ord('A') and user_in <= ord('Z') or user_in == ord(' '):
				if re.match("[a-zA-Z ]", chr(user_in)) != None:
					self.screen.clear()
					self.pila[-1]['filter']+=chr(user_in)
					filtro = self.pila[-1]['filter']
					if filtro != '':
						options = self.pila[-1]['original']
						options = filter(lambda x: filtro.lower() in x.lower(), options)
						self.show(options[:9], title="Filtrando por: "+filtro, subtitle=self.pila[-1]['subtitle'])

			# This is a number; check to see if we can set it
			if user_in >= ord('1') and user_in <= ord(str(min(9,len(self.options)+1))):
				self.selected = user_in - ord('0') - 1 # convert keypress back to a number, then subtract 1 to get index
				return

			# Increment or Decrement
			if user_in == curses.KEY_DOWN: # down arrow
				self.selected += 1
			if user_in == curses.KEY_UP: # up arrow
				self.selected -=1
			self.selected = self.selected % len(self.options)
			return
		else:
			return


	def handle_request(self, request):
		'''This is where you do things with the request'''
		if request is None: return
		elif request == "Exit":
			self.pila.pop()
			if len(self.pila) > 0:
				self.screen.clear()
				filtro = self.pila[-1]['filter']
				if filtro == "":
					title = self.pila[-1]['title']
				else:
					title = "Filtrando por: "+filtro
				options = self.pila[-1]['original']
				options = filter(lambda x: filtro.lower() in x.lower(), options)
				self.show(options[:9], title=title, subtitle=self.pila[-1]['subtitle'])
			else:
				return
		elif request == "Descargar":
			#print self.pila[-1]['url']
			self.block = True
			self.downloadSerie(self.pila[-1]['url'], self.directorio)
			self.block = False
		elif request == "Descargado!!":
			return
		else:
			anime = filter(lambda x: x[1] == request, self.animes)
			options = ['Descargar']
			self.pila.append({'title':'Descargar {0} en el directorio {1}'.format(anime[0][1], self.directorio), 'subtitle':'Opciones', 'options':options, 'original':options, 'filter':'', 'url':anime[0][0]})
			self.screen.clear()
			self.show(self.pila[-1]['options'][:9], title=self.pila[-1]['title'], subtitle=self.pila[-1]['subtitle'])
			return


	def __exit__(self):
		curses.endwin()
		os.system('clear')
		exit(0)
		
	########################################################################
	#    Función que inicia el proceso de descarga de una serie entera     #
	########################################################################
	def downloadSerie(self, url, directorio):
		cj = cookielib.CookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
		opener.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Sabayon Chrome/19.0.1084.52 Safari/536.5')]
		pagina = opener.open(url).read()
		listChapters = re.findall('<a.*?href="(http://www.animeyt.tv/ver/.*?)"', pagina.replace('\n',''))
		nChapters = len(listChapters)
		for i,c in enumerate(listChapters):
			self.screen.clear()
			self.pila[-1]['options'][0] = "Descargando {0}/{1}".format(i, nChapters)
			self.show(self.pila[-1]['options'][:9], self.pila[-1]['title'], self.pila[-1]['subtitle'])
			downloadChapter(c, directorio)
		self.screen.clear()
		self.pila[-1]['options'][0] = "Descargado!!"
		self.show(self.pila[-1]['options'][:9], self.pila[-1]['title'], self.pila[-1]['subtitle'])


###############################################
#    Función que obtiene todos los animes     #
###############################################
def getAllAnimes():
	global ANIMES
	ANIMES = []
	print "Cargando..."
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Sabayon Chrome/19.0.1084.52 Safari/536.5')]
	pagina = opener.open("http://www.animeyt.tv/animes").read().replace('\n', '')
	npages = int(re.findall('<li class="pager__item".*?>([0-9]+)<.*?</li>', pagina)[-1])
	
	id_hilos=[]
	for i in range(1, npages+1):
		idh = threading.Thread(target=getAnimesPage,args=("http://www.animeyt.tv/animes/?page={0}".format(i),))
		idh.start()
		id_hilos.append(idh)
	for idh in id_hilos:
		idh.join()
	
	return ANIMES

def getAnimesPage(url):
	global semaforo
	global ANIMES
	semaforo.acquire()
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Sabayon Chrome/19.0.1084.52 Safari/536.5')]
	pagina = opener.open(url).read().replace('\n', '')
	animes = re.findall('<article.*?<a href="(.*?)".*?alt="(.*?)".*?</article>', pagina)
	for a in animes:
		ANIMES.append(a)
	semaforo.release()



###################################################################
#    Función que inicia el proceso de descarga de un capítulo     #
###################################################################
def downloadChapter(url, directorio):
	urlVideo = getUrlDownloadChapter(url)
	
	seccionNombre = url.split('/')[-1]
	nombre = re.findall('[a-z\-]+', seccionNombre)[0]
	nc = re.findall('[0-9]+', seccionNombre)
	if len(nc) == 1:
		nombre += "{0}".format(nc[0])
	else:
		nombre += "{0}-{1}".format(nc[0], nc[-1])
	directorio = "{0}/{1}.mp4".format(directorio, nombre)
	downloadVideo(urlVideo, directorio)

########################################################################
#    Función que obtiene la url del vídeo del capítulo a descargar     #
########################################################################
def getUrlDownloadChapter(url):
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Sabayon Chrome/19.0.1084.52 Safari/536.5')]
	pagina = opener.open(url).read()
	urlVideo = re.findall('href="(http://www.animeyt.tv/descargar/.*?)"', pagina.replace("\n", ""))[0]
	pagina = opener.open(urlVideo).read()
	return re.findall('function crearBoton.*?url.*?=.*?"(.*?)"', pagina.replace('\n',''))[0]

########################################
#    Función que descarga un vídeo     #
########################################
def downloadVideo(url, directorio):
	try:
		# si el archivo no existe, lo descargamos
		print "Descargando {0} en {1}".format(url, directorio)
		time.sleep(5)
		if not os.path.isfile(directorio):
			urllib.urlretrieve(url, directorio)
	except:
		sys.stderr.write("Error al descargar {0}\n".format(directorio))



###########################
#    Función de ayuda     #
###########################
def printHelp(name):
	print "USO: {0} (opcional)directorio".format(name)
	print "Si no se indica un directorio, se descarga en el actual"

###############
#    MAIN     #
###############
def main():
	# Semáforo
	global semaforo
	semaforo = threading.Semaphore(10)
	
	directorio = "."
	
	if len(sys.argv) == 2:
		if sys.argv[1] == '-h':
			printHelp(sys.argv[0])
			return
		else:
			directorio = sys.argv[1]
	if not os.path.exists(directorio):
		print "No existe el directorio indicado"
	else:
		# Iniciamos ncurses
		cm = CursedMenu(directorio)


if __name__ == "__main__":
	main()
