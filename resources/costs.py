from flask import jsonify, make_response
from flask_restful import Api, Resource
import json
import os
import re
#import unicodedata

#import authinfo
import myTotalEnergiesCosts as mtecosts
import myGlobals as mg
from common.utils import myprint


class BaseCostsAPI(Resource):

    def __init__(self):
        pass
    
    def get(self, power):
        costs = mtecosts.getCostsFromCacheFile(power)
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
        else:
            v = float(re.findall("\d+\.\d+",costs[1])[0])	# Numeric/floating value
            outputDict = {
                "value"	:	v,
                "unit"	:	costs[1][-1]	# HACK: Last char is unit
            }
        return outputDict

    def put(self, id):
        pass

    def delete(self, id):
        pass
