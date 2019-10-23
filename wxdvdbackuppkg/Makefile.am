# Version 0.2.1: wxPython front end -- requires dd-dvd
pyprog_sub = sed \
			-e 's,[@]PYTHON[@],$(PYTHON),g' \
			-e 's,[@]PYTHON_VERSION[@],$(PYTHON_VERSION),g' \
			-e 's,[@]PYTHON_PREFIX[@],$(PYTHON_PREFIX),g' \
			-e 's,[@]PYTHON_EXEC_PREFIX[@],$(PYTHON_EXEC_PREFIX),g' \
			-e 's,[@]PYTHON_PLATFORM[@],$(PYTHON_PLATFORM),g' \
			-e 's,[@]pythondir[@],$(pythondir),g' \
			-e 's,[@]pkgpythondir[@],$(pkgpythondir),g' \
			-e 's,[@]pyexecdir[@],$(pyexecdir),g' \
			-e 's,[@]pkgpyexecdir[@],$(pkgpyexecdir),g' \
			-e 's,[@]PACKAGE[@],$(PACKAGE),g' \
			-e 's,[@]VERSION[@],$(VERSION),g'

if WITH_DD_DVD
if WITH_FRONTEND

pkgpython_PYTHON = *.py

endif
endif
