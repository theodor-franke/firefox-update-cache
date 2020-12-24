import os

# The location where the .mar update files are saved
UPDATE_FILE_PATH = os.path.dirname(os.path.abspath(__file__)) + '/updates'

# The URL of the Server that serves the .mar update files
SERVER_URL = 'http://192.168.188.105'

# The Upstream Update-Server
MOZILLA_AUS_URL = 'https://aus5.mozilla.org'

# False: The server will download the .mar file and returns the xml when the download is finished -> not recommended
# True: The server will return the original xml file and download the .mar in the background. The server will return the
#       already downloaded .mar file when the same .mar file is requested again.
LOAD_UPDATES_ASYNCHRONOUS = True
