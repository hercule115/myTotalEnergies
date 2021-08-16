import myGlobals as mg
from common.utils import get_linenumber
from datetime import datetime
from dateutil.relativedelta import relativedelta
from flask import Flask
from flask_restful import Api, Resource
import inspect
import json
from multiprocessing import Process, Value
import os
import sys
import time

import config
from common.utils import myprint, isFileOlderThanXMinutes, sleepUntil

import myTotalEnergiesContracts as mtec

from resources.days import DaysAPI, LastDayAPI, LastDaySimAPI, DaysChartAPI
from resources.months import MonthsAPI, LastMonthAPI, MonthsChartAPI, Last6MonthsAPI
from resources.misc import TotalAPI

    
DATACACHE_AGING_IN_MINUTES = 60

apiResources = {
    "days" : [
        (DaysAPI,       '/myte/api/v1.0/days/<string:id>',    'days'),
        (LastDayAPI,    '/myte/api/v1.0/lastday/<string:id>', 'lastday'),
        (LastDaySimAPI, '/myte/api/v1.0/lastdaysim/<string:id>', 'lastdaysim'),
        (DaysChartAPI,  '/myte/api/v1.0/dayschart/<string:id>', 'dayschart')        
        ],
    "months" : [
        (MonthsAPI,     '/myte/api/v1.0/months/<string:id>',    'months'),
        (LastMonthAPI,  '/myte/api/v1.0/lastmonth/<string:id>', 'lastmonth'),
        (MonthsChartAPI,'/myte/api/v1.0/monthschart/<string:id>', 'monthschart'),
        (Last6MonthsAPI,'/myte/api/v1.0/last6months/<string:id>', 'last6months')        
        ],
    "misc" : [
        (TotalAPI,     '/myte/api/v1.0/total/<string:id>',    'total'),
        ]
}

def foreverLoop(loop_on, dataCachePath, debug, updateDelay, updateTime):
    config.DEBUG = debug

    class color:
        BOLD      = '\033[1m'
        UNDERLINE = '\033[4m'
        END       = '\033[0m'

    # Re-define myprint() as child process don't share globals :(
    def myprint(level, *args, **kwargs):
        import builtins as __builtin__
        
        if level <= config.DEBUG:
            __builtin__.print('%s%s()%s:' % (color.BOLD, inspect.stack()[1][3], color.END), *args, **kwargs)

    #myprint(1,'Started. Updating cache file every %d seconds (%s).' % (updateDelay, time.strftime('%H:%M:%S', time.gmtime(updateDelay))))
    myprint(1,'Started. Updating cache file at %s.' % (updateTime))
    myprint(1,'Cache file: %s' % dataCachePath)
    
    while True:
        if loop_on.value == True:
            #time.sleep(updateDelay)
            sleepUntil(updateTime) # Sets the time to sleep until. "09:30AM"
            myprint(0, 'Reloading cache file from server...')
            res = mtec.getContractsInfoFromTotalEnergiesServer(dataCachePath)
            if res:
                myprint(0, 'Failed to create/update local data cache')
            dt_now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            myprint(0, '%s: Data collected from server' % (dt_now))            


def apiServerMain():

    dt_now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    mg.logger.info('Launching server at %s' % dt_now)
    myprint(1, 'Launching server...')
    
    app = Flask(__name__, static_url_path="")
    api = Api(app)

    for resourceName, resourceParamList in apiResources.items():
        for resource in resourceParamList:
            resApi = resource[0]
            resUrl = resource[1]
            resEndpoint = resource[2]
            myprint(1, 'Adding Resource:', resourceName, resApi, resUrl, resEndpoint)
            api.add_resource(resApi, resUrl, endpoint=resEndpoint)
            
    # Check if local cache file exists.
    # In this case, check its modification time and reload it from TotalEnergies server if too old.
    if os.path.isfile(mg.dataCachePath):
        if isFileOlderThanXMinutes(mg.dataCachePath, minutes=DATACACHE_AGING_IN_MINUTES):
            t = os.path.getmtime(mg.dataCachePath)
            dt = datetime.fromtimestamp(t).strftime('%Y/%m/%d %H:%M:%S')
            myprint(0, 'Cache file outdated (%s). Deleting and reloading from TotalEnergies server' % dt)
            # Remove data cache file and reload from server
            os.remove(mg.dataCachePath)
            res = mtec.getContractsInfoFromTotalEnergiesServer(mg.dataCachePath)
            if res:
                myprint(0, 'Failed to create local data cache. Aborting server')
                return(res)
    else:
        res = mtec.getContractsInfoFromTotalEnergiesServer(mg.dataCachePath)        
        if res:
            myprint(0, 'Failed to create local data cache. Aborting server')
            return(res)
        
    recording_on = Value('b', True)
    p = Process(target=foreverLoop, args=(recording_on,
                                          mg.dataCachePath,
                                          config.DEBUG,
                                          config.UPDATEDELAY,
                                          config.UPDATETIME))
    p.start()  
    app.run(debug=True, use_reloader=False, port=5001) ##, host="0.0.0.0", port=6420)
    p.join()

    return(0)
