from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
import os
import requests
import time

import myGlobals as mg
import authinfo
import config

import myTotalEnergiesClient
from common.utils import myprint, dumpToFile, masked, color, dumpJsonToFile
from common.utils import lastLineFromConsumptionFile, computeConsumptionByDays, computeConsumptionByMonths, generateConsumptionChart

# Reload data from cache file if needed.
# Parse data to build the allContracts dict. 
def getDataFromCache():
    # What time is it ?
    dtNow = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    
    # Check if cache file has been updated by server thread
    currModTime = os.path.getmtime(mg.dataCachePath)
    dt = datetime.fromtimestamp(currModTime).strftime('%Y/%m/%d %H:%M:%S')
    myprint(1, '%s: Cache file last modification time: %s (%d)' % (dtNow,dt,currModTime))

    if currModTime > mg.prevModTime:
        myprint(1, 'Need to reload cache data from cache file (%d/%d)' % (mg.prevModTime,currModTime))
        # Reload local cache
        rawInfo = loadDataFromCacheFile(mg.dataCachePath)
        mg.prevModTime = currModTime
        # Rebuild allContracts dictionary
        mg.allContracts = buildAllContracts(rawInfo)
    else:
        myprint(1, 'Data cache is up to date')

    myprint(1, 'allContracts #entries: %d' % (len(mg.allContracts)))
    return mg.allContracts


####
# Build allContracts dictionnary with relevant information from data cache file    
def buildAllContracts(rawInfo):
    myprint(1, 'Building AllContracts dictionary from raw data (#contracts=%d)' % (len(rawInfo)))

    # Output dict
    allContracts = dict()

    #myprint(1, rawInfo)

    # Build miscInfo dict from dataLayer
    dl = rawInfo['dataLayer']

    contract = dl['PDL']
    allContracts[contract] = dict()
    
    miscInfo = dict()
    miscInfo['PDL']                      = dl['PDL']
    miscInfo['IDClient']                 = dl['IDClient']
    miscInfo['PuissanceSouscrite']       = dl['PuissanceSouscrite']
    miscInfo['ElecProchaineReleveDate']  = dl['ElecProchaineReleveDate']
    miscInfo['ElecProchaineFactureDate'] = dl['ElecProchaineFactureDate']
    allContracts[contract]['miscInfo'] = miscInfo

    # Build 'powerCons'
    allContracts[contract]['powerCons'] = rawInfo['powerCons']

    # Build 'consByDays'
    allContracts[contract]['consByDays'] = rawInfo['consByDays']

    # Build 'consByMonths'
    allContracts[contract]['consByMonths'] = rawInfo['consByMonths']

    #myprint(1, allContracts)

    return allContracts


####
def loadDataFromCacheFile(dataCachePath):
    try:
        with open(dataCachePath, 'r') as infile:
            data = infile.read()
            res = json.loads(data)
            return res
    except Exception as error: 
        myprint(0, f"Unable to open data cache file {dataCachePath}")
        return None

    
####
def getContractsInfo(contract):

    myprint(1, 'Looking for contract: %s%s%s' % (color.BOLD, contract, color.END))

    # Dict to contain all information for all contracts
    consumptionDict = dict()

    allContracts = getDataFromCache()
    
    if config.VERBOSE:
        if contract == 'all':
            myprint(0, 'Showing all contracts')
            return(allContracts)
        elif contract in allContracts:
            myprint(1, 'Contract %s FOUND' % contract)
            return(allContracts[contract])
        else:
            myprint(1, 'Contract %s NOT FOUND' % contract)
            return {}
    
    # Compact mode

    outputDict = dict()
    myprint(1, 'Generating outputDict for "contract" %s' % (contract))

    # Single contract requested
    if not contract in allContracts:
        return outputDict # empty dict
        
    oneContract = allContracts[contract]

    if config.MONTHS:
        # Show information about months
        try:
            outputDict = oneContract['consByMonths']
        except:
            myprint(1, 'No consumption')
            outputDict = {}
        #print(json.dumps(outputDict, ensure_ascii=False))
        return outputDict

    if config.DAYS:
        # Show information about days
        try:
            outputDict = oneContract['consByDays']
        except:
            myprint(1, 'No consumption')
            outputDict = {}
        #print(json.dumps(outputDict, ensure_ascii=False))
        return outputDict

    # Show total consumption information
    try:
        outputDict = oneContract['powerCons']
    except:
        myprint(1, 'No consumption')
        outputDict = {}
    return(outputDict)
    

def saveLastLineOfConsFiles():
    dtNow = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    outputFile = os.path.join(mg.moduleDirPath, 'lastLinesOfConsFiles.txt')
    
    with open(outputFile, "a") as out:
        for interval in ['30MIN', 'JOUR', 'MOIS']:
            inputFile = os.path.join(mg.moduleDirPath, mg.consumptionFilesDict[interval])
            if not os.path.isfile(inputFile):
                myprint(0, '%s consumption file does not exist' % (inputFile))
                return
            ll = lastLineFromConsumptionFile(inputFile)
        
            out.write('%s: %s: %s'% (interval,dtNow, ll))
        out.write('----\n')

    
# Get contract(s) info from SOSH Server and update the local cache file
def getContractsInfoFromTotalEnergiesServer(dataCachePath):
    myprint(2, 'Connecting to TOTAL ENERGIES Server')
    
    username, password = authinfo.decodeKey(config.TE_AUTH.encode('utf-8'))

    # If username / paswword have been provided on the command-line, use them
    try:
        a = getattr(config, 'TE_USERNAME')
    except:
        setattr(config, 'TE_USERNAME', username)
        
    try:
        a = getattr(config, 'TE_PASSWORD')
    except:
        setattr(config, 'TE_PASSWORD', password)

    if config.VERBOSE:
        print('%-15s: %s' % ('TE Username', config.TE_USERNAME))
        print('%-15s: %s' % ('TE Password', masked(config.TE_PASSWORD, 3)))

    with requests.session() as session:
        # Create connection to Sosh server, connect with given credentials
        te = myTotalEnergiesClient.TotalEnergies(config.TE_USERNAME, config.TE_PASSWORD, session)

        # Read current contracts information
        info = te.getContractsInformation()

        # Work done. Logout from server
        te.logout()

    #myprint(1, type(info), len(info))
    print(json.dumps(info, indent=4))
    
    # (Re-)build days chart (last 14 days only)
    bydays = computeConsumptionByDays()
    if not bydays:
        myprint(1, 'Unable to parse %s' % (mg.consumptionFilesDict['JOUR']))
    else:
        # dt = datetime.strptime(date, '%d/%m/%Y').strftime('%Y-%m-%d')
        # Re-write dates
        firstDate = datetime.strptime(bydays['date'][0], '%Y-%m-%d').strftime('%d/%m/%Y')
        lastDate  = datetime.strptime(bydays['date'][-1], '%Y-%m-%d').strftime('%d/%m/%Y')
        #lastDate  = bydays['date'][-1]
        outFilePath = generateConsumptionChart(bydays, interval='Day', opt='(%s - %s)' % (firstDate, lastDate))
        if not outFilePath:
            myprint(0, 'Failed to create plot chart (by day)')

    # (Re-)build months chart (last 12 months only)
    bymonths = computeConsumptionByMonths()
    if not bymonths:
        myprint(1, 'Unable to parse %s' % (mg.consumptionFilesDict['MOIS']))
    else:
        #print(json.dumps(bymonths, indent=4))
        firstDate = bymonths['date'][0]
        lastDate  = bymonths['date'][-1]
        outFilePath = generateConsumptionChart(bymonths, interval='Month', opt='(%s - %s)' % (firstDate, lastDate))
        if not outFilePath:
            myprint(0, 'Failed to create plot chart (by month)')
        

    # Update data cache
    res = dumpJsonToFile(dataCachePath, info)
    if res:
        myprint(1, 'Failed to update local data cache')
        return (res)

    #saveLastLineOfConsFiles()
