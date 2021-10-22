#!/usr/bin/env python

# Tool to get contracts information from totalenergies.fr

# Import or build our configuration. Must be FIRST
try:
    import config	# Shared global config variables (DEBUG,...)
except:
    #print('config.py does not exist. Generating...')
    import initConfig	# Check / Update / Create config.py module
    initConfig.initConfiguration()
    
# Import generated module
try:
    import config
except:
    print('config.py initialization has failed. Exiting')
    sys.exit(1)
    
import argparse
import builtins as __builtin__
from datetime import datetime
import inspect
import json
import logging
import os
import sys
import time

import myGlobals as mg
from common.utils import myprint, module_path, get_linenumber, color, dumpContractInformation

import authinfo		# Encode/Decode credentials
import myTotalEnergiesContracts as mtec
import myTotalEnergiesCosts as mtecosts
        
# Arguments parser
def parse_argv():
    desc = 'Get contract information/usage from Total Energies server'

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("-s", "--server",
                        action="store_true",                        
                        dest="server",
                        default=False,
                        help="run in server mode (as a Web Service)")
    parser.add_argument("-d", "--debug",
                        action="count",
                        dest="debug",
                        default=0,
                        help="print debug messages (to stdout)")
    parser.add_argument("-v", "--verbose",
                        action="store_true", dest="verbose", default=False,
                        help="provides more information")
    parser.add_argument('-f', '--file',
                        dest='logFile',
                        const='',
                        default=None,
                        action='store',
                        nargs='?',
                        metavar='LOGFILE',
                        help="write debug messages to FILE (default to <hostname>-debug.txt)")
    parser.add_argument("-C", "--cache",
                        action="store_true",
                        dest="useCache",
                        default=False,
                        help="Use local cache if available")
    parser.add_argument('-D', '--delay',
                        dest='updateDelay',
                        default=3600,
                        type=int,
                        action='store',
                        nargs='?',
                        metavar='DELAY',
                        help="update interval in seconds (server mode only)")
    parser.add_argument('-A', '--at',
                        dest='updateTime',
                        default="09:30AM",
                        type=str,
                        action='store',
                        nargs='?',
                        metavar='TIME',
                        help="update time, e.g. '09:30AM' (server mode only)")

    # Resources arguments
    parser.add_argument("--months",
                        action="store_true", dest="months", default=False,
                        help="shows information by month")
    parser.add_argument("--days",
                        action="store_true", dest="days", default=False,
                        help="shows information by day")
    parser.add_argument("--total",
                        action="store_true", dest="total", default=False,
                        help="shows information about total consumption")
    parser.add_argument("--costs",
                        action="store_true", dest="costs", default=False,
                        help="download/shows information about kWH costs")
    parser.add_argument("-m", "--misc",
                        action="store_true", dest="miscinfo", default=False,
                        help="provide miscellaneous information")

    # Credentials arguments    
    parser.add_argument('-u', '--user',
                        dest='userName',
                        help="Username to use for login")
    parser.add_argument('-p', '--password',
                        dest='password',
                        help="Password to use for login")
    parser.add_argument("-I", "--info",
                        action="store_true", dest="version", default=False,
                        help="print version and exit")

    parser.add_argument('contract',
                        nargs='*',
                        help='Contract (PDL) to show (Use "all" to show all contracts or "init" to initialize the configuration)')

    args = parser.parse_args()
    return args


####
def import_module_by_path(path):
    name = os.path.splitext(os.path.basename(path))[0]
    if sys.version_info[0] == 2:
        import imp
        return imp.load_source(name, path)
    elif sys.version_info[:2] <= (3, 4):
        from importlib.machinery import SourceFileLoader
        return SourceFileLoader(name, path).load_module()
    else:
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


#
# Import TotalEnergies module. Must be called *after* parsing arguments
#
def importModule(moduleDirPath, moduleName, name):
    modulePath = os.path.join(moduleDirPath, moduleName)
    mod = import_module_by_path(modulePath)
    globals()[name] = mod


####
def main():

    args = parse_argv()

    if args.version:
        print('%s: version %s' % (sys.argv[0], mg.VERSION))
        sys.exit(0)

    config.SERVER    = args.server
    config.VERBOSE   = args.verbose
    config.USE_CACHE = args.useCache
    config.DEBUG     = args.debug
    config.DAYS      = args.days
    config.MONTHS    = args.months
    config.TOTAL     = args.total
    config.COSTS     = args.costs
    config.MISCINFO  = args.miscinfo
    
    if config.DEBUG:
        myprint(1, 'Running in DEBUG mode (level=%d)' % config.DEBUG)
        myprint(1,
                'config.SERVER =',    config.SERVER,
                'config.VERBOSE =',   config.VERBOSE,
                'config.USE_CACHE =', config.USE_CACHE,
                'config.DAYS =',      config.DAYS,
                'config.MONTHS =',    config.MONTHS,
                'config.TOTAL =',     config.TOTAL,
                'config.COSTS =',     config.COSTS,
                'config.MISCINFO',    config.MISCINFO,
        )
        
    if args.logFile == None:
        #print('Using stdout')
        pass
    else:
        if args.logFile == '':
            config.LOGFILE = "totalenergies.fr.log"
        else:
            config.LOGFILE = args.logFile
        mg.configFilePath = os.path.join(mg.moduleDirPath, config.LOGFILE)
        print('Using log file: %s' % mg.configFilePath)
        try:
            sys.stdout = open(mg.configFilePath, "w")
            sys.stderr = sys.stdout            
        except:
            print('Cannot create log file')

    if config.SERVER:
        import myTotalEnergiesApiServer as mteas
        if config.DEBUG:
            mg.logger.info('myTotalEnergiesApiServer imported (line #%d)' % get_linenumber())
        
        if args.updateDelay:
            config.UPDATEDELAY = args.updateDelay
        else:
            config.UPDATEDELAY = 3600 # seconds
        myprint(0, 'Running in Server mode. Update interval: %d seconds' % config.UPDATEDELAY)
        
        if args.updateTime:
            config.UPDATETIME = args.updateTime
        else:
            config.UPDATETIME = "09:30AM"
        myprint(0, 'Running in Server mode. Update time: %s' % config.UPDATETIME)

        res = mteas.apiServerMain()
        myprint(1, 'myTotalEnergies API Server exited with code %d' % res)
        sys.exit(res)
        
    #
    # Standalone mode
    #

    if config.COSTS:
        # Read tariffs from Prix-Elec.com server and update cache file
        res = mtecosts.getTariffsInfoFromPrixElecServer(mg.costsDataCachePath)
        if res:
            myprint(0, 'Failed to get tariffs from prix-elec.com')
            sys.exit(res)
        myprint(0, f'{mg.costsDataCachePath} has been updated')
        if config.VERBOSE:
            # Show base costs... for various meter power
            for power in ['3','6','9','12','15', '18']:
                prices = mtecosts.getCostsFromCacheFile(power)
                mtecosts.dumpCosts(power, prices)
        # Exit 
        sys.exit(0)
    
    if not args.contract:
        contract = 'all'
    else:
        if 'init' in args.contract:
            initConfiguration()
            print('Config initialized. Re-run the command.')
            sys.exit(0)
        else:
            contract = args.contract[0]

    if config.USE_CACHE:
        # Load data from local cache
        info = mtec.getContractsInfo(contract)
        dumpContractInformation(contract, info)
        sys.exit(0)

    # Read data from TotalEnergies webserver
    res = mtec.getContractsInfoFromTotalEnergiesServer(mg.dataCachePath)
    if res:
        myprint(0, 'Failed to create/update local data cache')
        sys.exit(res)

    t = os.path.getmtime(mg.dataCachePath)
    dt = datetime.fromtimestamp(t).strftime('%Y/%m/%d %H:%M:%S')
    myprint(1, 'Cache file updated. Last modification time: %s' % dt)

    # Display information
    info = mtec.getContractsInfo(contract)
    dumpContractInformation(contract, info)
        
    if args.logFile and args.logFile != '':
        sys.stdout.close()
        sys.stderr.close()
        
# Entry point    
if __name__ == "__main__":

    dt_now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    logging.basicConfig(filename='myTotalEnergies-ws.log', level=logging.INFO)
    mg.logger = logging.getLogger(__name__)
    mg.logger.info('Running at %s. Args: %s' % (dt_now, ' '.join(sys.argv)))

    # Absolute pathname of directory containing this module
    mg.moduleDirPath = os.path.dirname(module_path(main))

    username, password = authinfo.decodeKey(config.TE_AUTH.encode('utf-8'))
    
    # Absolute pathname of data cache file
    mg.dataCachePath = os.path.join(mg.moduleDirPath, '.%s%s' % (username, mg.DATA_CACHE_FILE))

    # Absolute pathname of costs data cache file
    mg.costsDataCachePath = os.path.join(mg.moduleDirPath, '.%s' % (mg.COSTS_DATA_CACHE_FILE))
    
    # Absolute pathname of lastday cache file
    #mg.lastDayCachePath = os.path.join(mg.moduleDirPath, '.%s%s' % (username, mg.LASTDAY_CACHE_FILE))

    # Absolute pathnames of consumption files by interval
    for interval in ['JOUR', 'MOIS', 'ANNEE']:  # Avoid '30MIN'
        mg.consumptionFilesDict[interval] = os.path.join(mg.moduleDirPath, '.consumption-by-%s.csv' % (interval))

    # Let's go
    main()
