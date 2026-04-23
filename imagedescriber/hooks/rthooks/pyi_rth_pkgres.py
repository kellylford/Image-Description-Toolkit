# No-op override for PyInstaller's pyi_rth_pkgres runtime hook.
# The default hook tries to import pkg_resources which pulls in jaraco.*,
# platformdirs, and other setuptools dependencies not needed at runtime.
