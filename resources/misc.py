from datetime import datetime
from flask import jsonify, make_response, url_for  # redirect, request, url_for, current_app, flash, 
from flask_restful import Api, Resource
from flask_httpauth import HTTPBasicAuth
import json
import os

import config
import authinfo
import myTotalEnergiesContracts as mtec
import myGlobals as mg
from common.utils import myprint, masked, computeConsumptionByMonths, generateConsumptionChart, computeTotalConsumption

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


class TotalAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        # Set config.DAYS and config.MONTHS as False to get total consumption information
        config.DAYS   = False
        config.MONTHS = False
        config.MISCINFO = False
        config.TOTAL  = True

    def get(self, id):
        dt_now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        info = mtec.getContractsInfo(id)
        myprint(1, dt_now, json.dumps(info, ensure_ascii=False))
        outputDict = {
            "date"   : info['totalConsumptionDate'],
            "value"  : info['totalConsumptionVol'],
            "unit"   : info['totalConsumptionUnit'],
        }
        return outputDict

    def put(self, id):
        pass

    def delete(self, id):
        pass


class MiscInfoAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        # Set config.* to False but config.DATALAYER to get misc. info
        config.DAYS   = False
        config.MONTHS = False
        config.TOTAL  = False
        config.MISCINFO = True

    def get(self, id):
        dt_now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        info = mtec.getContractsInfo(id)
        myprint(1, dt_now, json.dumps(info, ensure_ascii=False))   
        outputDict = {
            "Offre"			: info['Offre'],
            "PuissanceSouscrite"	: info['PuissanceSouscrite'],
            "OptionTarifaire"		: info['OptionTarifaire'],
            "NumeroCompteurELEC"	: info['NumeroCompteurELEC'],
            "IDClient"			: info['IDClient'],
            "PDL"			: info['PDL'],
        }
        return outputDict

    def put(self, id):
        pass

    def delete(self, id):
        pass
    
