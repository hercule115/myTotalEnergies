# Some glogal constants
VERSION = '1.0'
DATA_CACHE_FILE = '.contracts.json'
LASTDAY_CACHE_FILE = '.lastday.json'

# Global variables
logger = None
moduleDirPath = ''
dataCachePath = ''
lastDayCachePath = ''
contractsInfo = None
prevModTime = 0
allContracts = {}
consumptionFilesDict = {}
    
# Config parameters
mandatoryFields = [('a',['TE_AUTH', ('s','TE_USERNAME'), ('p','TE_PASSWORD')])]
optionalFields  = [('d','DEBUG', 0),
                   ('b','VERBOSE', 'False'),
                   ('s','LOGFILE')]
