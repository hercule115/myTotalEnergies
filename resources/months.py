from datetime import datetime
from flask import jsonify, make_response, url_for  # redirect, request, url_for, current_app, flash, 
from flask_restful import Api, Resource
from flask_httpauth import HTTPBasicAuth
import json
import os
import unicodedata

import config
import authinfo
import myTotalEnergiesContracts as mtec
import myGlobals as mg
from common.utils import myprint, masked, computeConsumptionByMonths, generateConsumptionChart

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


class MonthsChartAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        config.DAYS   = False
        config.MONTHS = True
        config.TOTAL  = False

    def get(self, id):
        dt_now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        myprint(1, dt_now, 'Generating plot chart (by month)')

        bymonths = computeConsumptionByMonths()
        if not bymonths:
            myprint(1, f'Unable to parse {mg.consumptionFilesDict["MOIS"]}')
            return

        #print(json.dumps(bymonths, indent=4))
        firstDate = bymonths['date'][0]
        lastDate  = bymonths['date'][-1]
        outFilePath = generateConsumptionChart(bymonths, interval='Month', opt='(%s - %s)' % (firstDate, lastDate))
        if not outFilePath:
            myprint(0, 'Failed to create plot chart (by month)')
            
    def put(self, id):
        pass

    def delete(self, id):
        pass


class Last6MonthsAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        config.DAYS   = False
        config.MONTHS = True
        config.TOTAL  = False

    def get(self, id):
        info = mtec.getContractsInfo(id)
        last6Months = sorted(info.items(), key=lambda kv: kv[0])[-6:]

        outputDict = dict()
        outputDict["Contract"] = id
        outputDict["MonthReports"] = list()
        for item in last6Months:
            #print(item) # item is a list of tuples
            date,(cons, unit, friendlyDate) = item
            #print(date,cons,unit,friendlyDate)
            outputDict["MonthReports"].append(
                {
                    "date":  date,
                    "value": cons,
                    "unit":  unit,
                    "friendlyDate":friendlyDate,
                }
            )

        myprint(1, json.dumps(outputDict, ensure_ascii=False))
        #r = unicode(str, errors='replace')
        return outputDict

    def put(self, id):
        pass

    def delete(self, id):
        pass
    
    
class MonthsAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        config.DAYS   = False
        config.MONTHS = True
        config.TOTAL  = False

    def get(self, id):
        dt_now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        info = mtec.getContractsInfo(id)
        myprint(1, dt_now, json.dumps(info, ensure_ascii=False))
        return info

    def put(self, id):
        pass

    def delete(self, id):
        pass


class LastMonthAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        config.DAYS = False
        config.MONTHS = True
        config.TOTAL  = False

    def get(self, id):
        info = mtec.getContractsInfo(id)
        #myprint(1, json.dumps(info, ensure_ascii=False))        
        # Get last record (e.g. last day in report)
        lastItem = sorted(info.items(), key=lambda kv: kv[0])[-1]
        myprint(1,'Last Item:',lastItem)
        outputDict = {
            "date"  : lastItem[0],
            "value" : lastItem[1][0],
            "unit"  : lastItem[1][1],
            "friendlyDate" : lastItem[1][2],
        }
        return outputDict
    
    def post(self):
        pass
