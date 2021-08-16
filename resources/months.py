from flask import jsonify, make_response, url_for  # redirect, request, url_for, current_app, flash, 
from flask_restful import Api, Resource
from flask_httpauth import HTTPBasicAuth
import json
import os

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

    def get(self, id):
        info = computeConsumptionbyMonths()
        outFilePath = generateConsumptionChart(info, 'Month')

    def put(self, id):
        pass

    def delete(self, id):
        pass


class Last6MonthsAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        config.DAYS   = False
        config.MONTHS = True

    def get(self, id):
        info = mtec.getContractsInfo(id)
        last6Months = sorted(info.items(), key=lambda kv: kv[0])[-6:]

        outputDict = dict()
        outputDict['Contract'] = id
        outputDict['MonthReports'] = list()
        for item in last6Months:
            #print(item) # item is a list of tuples
            date,(cons, unit, friendlyDate) = item
            #print(date,cons,unit,friendlyDate)
            outputDict['MonthReports'].append({"date":date, "value":cons, "unit":unit, "friendlyDate":friendlyDate})

        myprint(1, json.dumps(outputDict, ensure_ascii=False))
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

    def get(self, id):
        info = mtec.getContractsInfo(id)
        myprint(1, json.dumps(info, ensure_ascii=False))
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

    def get(self, id):
        info = mtec.getContractsInfo(id)
        #myprint(1, json.dumps(info, ensure_ascii=False))        
        # Get last record (e.g. last day in report)
        lastItem = sorted(info.items(), key=lambda kv: kv[0])[-1]
        myprint(1,'Last Item:',lastItem)
        o = {
            "date"  : lastItem[0],
            "value" : lastItem[1][0],
            "unit"  : lastItem[1][1],
            "friendlyDate" : lastItem[1][2],
        }
        # Check if this record has been already provided. In this case, skip it
        # if os.path.isfile(mg.lastDayCachePath):
        #     with open(mg.lastDayCachePath, "r") as f:
        #         oo = f.readline()
        #     myprint(1, 'Last Item dispatched from cache: %s' % (oo))
        #     if str(o) == oo:
        #         myprint(1, 'Last item already dispatched. Skipping output')
        #         return {}
        #     else:
        #         myprint(1, 'Updating last item dispatched: %s' % (o))
        #         f.write(str(o))
        #         return o
        # else:
        #     with open(mg.lastDayCachePath, "w") as f:
        #         f.write(str(o))
        #     myprint(1, '%s cache file created' % (mg.lastDayCachePath))
        #     return o
        return o
    
    def post(self):
        pass
