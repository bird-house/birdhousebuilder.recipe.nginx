import logging
import sys

LOGGER = logging.getLogger('BUILDOUT')
PY2 = sys.version_info[0] == 2

if PY2:
    LOGGER.debug('Python 2.x')
    from urllib import urlretrieve

else:
    LOGGER.debug('Python 3.x')
    from urllib.request import urlretrieve
