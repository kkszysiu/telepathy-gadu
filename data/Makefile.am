managerdir = $(datadir)/telepathy/managers
manager_DATA = sunshine.manager

servicedir = $(datadir)/dbus-1/services
service_in_files = org.freedesktop.Telepathy.ConnectionManager.sunshine.service.in
service_DATA = $(service_in_files:.service.in=.service)

$(service_DATA): $(service_in_files) Makefile
	@sed -e "s|\@LIBEXECDIR\@|$(libexecdir)|" $< > $@

EXTRA_DIST = $(manager_DATA) \
	$(service_in_files)

clean-local:
	rm -f *~ $(service_DATA)
