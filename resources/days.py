from flask import jsonify, make_response # redirect, request, url_for, current_app, flash, 
from flask_restful import Api, Resource
from flask_httpauth import HTTPBasicAuth
import json
import os

import config
import authinfo
import myTotalEnergiesContracts as mtec
import myGlobals as mg
from common.utils import myprint, masked, computeConsumptionByDays, generateConsumptionChart

from datetime import datetime
import random

auth = HTTPBasicAuth()

@auth.get_password
def get_password(username):
    myprint(1, 'Checking username %s' % username)
    
    u, p = authinfo.decodeKey(config.TE_AUTH.encode('utf-8'))

    myprint(1, '%-15s: %s' % ('TotalEnergies Username', u))
    myprint(1, '%-15s: %s' % ('TotalEnergies Password', masked(p, 3)))

    if u == '':
        myprint(0, 'Unable to decode config.TE_AUTH')
        return None

    if username != u:
        myprint(0, 'Invalid username %s' % username)
        return None

    myprint(1, 'Username is valid')
    return p


@auth.error_handler
def unauthorized():
    # return 403 instead of 401 to prevent browsers from displaying the default
    # auth dialog
    return make_response(jsonify({'message': 'Unauthorized access'}), 403)


class DaysAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        config.DAYS   = True
        config.MONTHS = False
        config.TOTAL  = False
        
    def get(self, id):
        info = mtec.getContractsInfo(id)
        myprint(1, json.dumps(info, ensure_ascii=False))
        return (info)

    def put(self, id):
        pass

    def delete(self, id):
        pass


class LastDayAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        config.DAYS   = True
        config.MONTHS = False
        config.TOTAL  = False
        
    def get(self, id):
        info = mtec.getContractsInfo(id)
        #myprint(1, json.dumps(info, ensure_ascii=False))        
        # Get last record (e.g. last day in report)
        lastItem = sorted(info.items(), key=lambda kv: kv[0])[-1]
        myprint(1,'Last Item:',lastItem)
        outputDict = {
            "date"      : lastItem[0],
            "value"     : lastItem[1][0],
            "unit"      : lastItem[1][1],
            "friendlyDate" : lastItem[1][2],
        }
        return outputDict
    
    def post(self):
        pass

    
class DaysChartAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        config.DAYS   = True
        config.MONTHS = False
        config.TOTAL  = False

    def get(self, id):
        # info = computeConsumptionByDays()
        # firstDate = info['date'][0]
        # lastDate  = info['date'][-1]
        # #print(len(days['date']),firstDate,lastDate)
        # outFilePath = generateConsumptionChart(info, interval='Day', opt='(%s / %s)' % (firstDate, lastDate))

        bydays = computeConsumptionByDays()
        if not bydays:
            myprint(1, f'Unable to parse {mg.consumptionFilesDict["JOUR"]}')
            return
        # Re-write dates
        firstDate = datetime.strptime(bydays['date'][0], '%Y-%m-%d').strftime('%d/%m/%Y')
        lastDate  = datetime.strptime(bydays['date'][-1], '%Y-%m-%d').strftime('%d/%m/%Y')
        outFilePath = generateConsumptionChart(bydays, interval='Day', opt='(%s - %s)' % (firstDate, lastDate))
        if not outFilePath:
            myprint(0, 'Failed to create plot chart (by day)')
            
    def put(self, id):
        pass

    def delete(self, id):
        pass
