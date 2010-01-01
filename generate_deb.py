from py2deb import Py2deb
from glob import glob

version="0.1.0"
changelog=open("NEWS","r").read()

p=Py2deb("telepathy-gadu")
p.author="Krzysztof 'kkszysiu' Klinikowski"
p.mail="kkszysiu@gmail.com"
p.description="""telepathy-gadu is the GaduGadu connection manager for Telepathy"""
p.url = "http://github.com/kkszysiu/telepathy-gadu/"
p.depends="python, python-telepathy, python-twisted-core"
p.license="gpl"
p.section="net"
p.arch="all"

#we need to change paths in this file
f = open("data/org.freedesktop.Telepathy.ConnectionManager.gadu.service.in").read()
#telepathy-gadu file location for Ubuntu-like distros
f = f.replace('@LIBEXECDIR@', '/usr/lib/telepathy')

f2 = open('data/org.freedesktop.Telepathy.ConnectionManager.gadu.service', 'w')
f2.write(f)
f2.close()

p["/usr/lib/telepathy"]=["telepathy-gadu"]
p["/usr/share/dbus-1/services"]=["data/org.freedesktop.Telepathy.ConnectionManager.gadu.service|org.freedesktop.Telepathy.ConnectionManager.gadu.service"]
p["/usr/share/telepathy/managers"]=["data/gadu.manager|gadu.manager"]
p["/usr/lib/python2.6/dist-packages"]=\
glob("gadu/*.py")+\
glob("gadu/channel/*.py")+\
glob("gadu/util/*.py")+\
glob("gadu/lqsoft/*.py")+\
glob("gadu/lqsoft/cstruct/*.py")+\
glob("gadu/lqsoft/cstruct/fields/*.py")+\
glob("gadu/lqsoft/cstruct/test/*.py")+\
glob("gadu/lqsoft/pygadu/*.py")+\
glob("gadu/lqsoft/utils/*.py")



#p["/usr/share/fricorder"]=[i+"|"+i[5:] for i in \
#                         glob("data/*.*") + glob("data/templates/*")]
#p["/usr/bin"]=["fricorder.py|fricorder"]
#p["/usr/share/doc/fricorder"]=["README","COPYING",]

p.generate(version, changelog, rpm=True, src=True)

