#!/usr/bin/python2
import sys

import os
from mega import Mega
mega = Mega()

AUTH_FILE = os.environ.get('AUTH_FILE', 'mega_auth')

creds = open(AUTH_FILE).read().strip('\n ').split(':')
m = mega.login(*creds)

m.download_url(sys.argv[1])
