from datetime import datetime
from flask import jsonify, make_response
from flask_restful import Api, Resource
import json
import os
import re
#import unicodedata

import myTotalEnergiesCosts as mtecosts
import myGlobals as mg
from common.utils import myprint


class BaseCostsAPI(Resource):

    def __init__(self):
        pass
    
    def get(self, power):
        dt_now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        costs = mtecosts.getCostsFromCacheFile(power)
        myprint(1, dt_now, json.dumps(costs, ensure_ascii=False))
        # Example:
        # yearly fee Base,  base,       yearly fee HC,  Cost HP,    Cost HC 
        # ['137.64€',       '0.1442€',  '145.83€',      '0.1678€',  '0.1263€']
        if len(costs) != 5:
            # Something went wrong with costs parsing            
            myprint(0, f'Unable to get costs for power {power}')
            outputDict = {
                "value"	: 0,
                "unit"	: ''
            }
            return outputDict
        else:
            try:
                v = float(re.findall("\d+\.\d+",costs[1])[0])	# Numeric/floating value
                outputDict = {
                    "value" :	v,
                    "unit"  :	costs[1][-1]	# HACK: Last char is unit
                }
            except:
                myprint(0, dt_now, 'Unable to parse costs info')
                outputDict = {
                    "value" : 0,
                    "unit"  : ''
                }
            else:
                return outputDict
            
    def put(self, id):
        pass

    def delete(self, id):
        pass
