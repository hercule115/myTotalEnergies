from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import requests
import time
import shutil

import myGlobals as mg
import httpHeaders as hh
import config

from common.utils import myprint, color, dumpToFile, dumpJsonToFile

PRIX_KWH_2021_FILE = 'prix-kwh-2021-te.html'
PRIX_KWH_2021_URL  = 'https://prix-elec.com/tarifs/fournisseurs/totalenergies'

class color:
    PURPLE    = '\033[95m'
    CYAN      = '\033[96m'
    DARKCYAN  = '\033[36m'
    BLUE      = '\033[94m'
    GREEN     = '\033[92m'
    YELLOW    = '\033[93m'
    RED       = '\033[91m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
    END       = '\033[0m'

# Dictionary containing the HTTP requests to send to the server
PRIX_ELEC_HTTP_REQUESTS = {
    "tarifsFournisseursTotalEnergies" : {
        "info" : "Connect to www.prix-elec.com and get tariffs page for TE",
        "rqst" : {
            "type" : 'GET',
            "url"  : PRIX_KWH_2021_URL,
            "headers" : {
            },
        },
        "resp" : {
            "code" : 200,
            #"dumpResponse" : PRIX_KWH_2021_FILE,
            "updateCookies" : False,
        },
        "returnText" : True,
    },
}


class TotalEnergiesCosts:
    def __init__(self, session):
        self._session  = session
        # Dict to save cookies from server
        self._cookies = dict()
        
    def getTariffsInformation(self, costsDataCachePath):
        # Execute request to get the tariffs for TE
        respText = self._executeRequest('tarifsFournisseursTotalEnergies')
        if 'ErRoR' in respText:
            myprint(1, 'Error retrieving information from prix-elec.com server')
            return -1

        # Parse returned information
        info = parseTariffsPage(respText)
        myprint(1, json.dumps(info, indent=4))

        # Update data cache
        res = dumpJsonToFile(costsDataCachePath, info)
        if res:
            myprint(1, 'Failed to update local data cache')
            return res
        return 0
        
    # Build a string containing all cookies passed as parameter in a list 
    def _buildCookieString(self, cookieList):
        cookieAsString = ''
        for c in cookieList:
            # Check if cookie exists in our dict
            if c in self._cookies:
                cookieAsString += '%s=%s; ' % (c, self._cookies[c])
            else:
                myprint(1,'Warning: Cookie %s not found.' % (c))
        return(cookieAsString)

    # Update our cookie dict
    def _updateCookies(self, cookies):
        for cookie in self._session.cookies:
            if cookie.value == 'undefined' or cookie.value == '':
                myprint(2,'Skipping cookie with undefined value %s' % (cookie.name))
                continue
            if cookie.name in self._cookies and self._cookies[cookie.name] != cookie.value:
                myprint(1,'Updating cookie:', cookie.name)
                self._cookies[cookie.name] = cookie.value
            elif not cookie.name in self._cookies:
                myprint(1,'Adding cookie:', cookie.name)
                self._cookies[cookie.name] = cookie.value
            else:
                myprint(2,'Cookie not modified:', cookie.name)                

    def _executeRequest(self, name):
        dt_now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        rqst = PRIX_ELEC_HTTP_REQUESTS[name]
        myprint(1, '%s: Executing request "%s": %s' % (dt_now, name, rqst["info"]))
        myprint(2, json.dumps(rqst, indent=4))

        hdrs = hh.HttpHeaders()

        for k,v in rqst["rqst"]["headers"].items():
            if k == "Cookie":
                if 'str' in str(type(v)):	# Cookie is a string
                    cookieAsString = v
                else:				# Cookie is a list of cookies
                    assert('list' in str(type(v)))
                    cookieAsString = self._buildCookieString(v)

                # Add extra Cookie if requested
                if "extraCookie" in rqst["rqst"]:
                    cookieAsString += rqst["rqst"]["extraCookie"]
                hdrs.setHeader('Cookie', cookieAsString)
            else:
                hdrs.setHeader(k, v)

        rqstType = rqst["rqst"]["type"]
        rqstURL  = rqst["rqst"]["url"]
        try:
            rqstStream = rqst["rqst"]["stream"]
        except:
            rqstStream = False

        try:
            csvStream = rqst["rqst"]["csv"]
        except:
            csvStream = False
            
        myprint(1,'Request type: %s, Request URL: %s' % (rqstType, rqstURL))
        myprint(2,'Request Headers:', json.dumps(hdrs.headers, indent=2))

        errFlag = False
        
        if rqstType == 'GET':
            try:
                myprint(2,'Request Stream:', rqstStream, 'CSV Stream:', csvStream)
                r = self._session.get(rqstURL, headers=hdrs.headers, stream=rqstStream)
            except requests.exceptions.RequestException as e:
                errFlag = True
                
        elif rqstType == 'POST':
            rqstPayload  = rqst["rqst"]["payload"]
            myprint(1,"payload=%s" % rqstPayload)
            try:
                r = self._session.post(rqstURL, headers=hdrs.headers, data=rqstPayload)
            except requests.exceptions.RequestException as e:
                errFlag = True
                
        else:	# OPTIONS
            assert(rqstType == 'OPTIONS')
            try:
                r = self._session.options(rqstURL, headers=hdrs.headers)
            except requests.exceptions.RequestException as e:
                errFlag = True

        if errFlag:
            errorMsg = 'ErRoR while retrieving information: %s' % (e) # Dont't change the cast for ErRoR  !!!!
            myprint(0, errorMsg)
            return errorMsg

        myprint(1,'Response Code:',r.status_code)

        if r.status_code != rqst["resp"]["code"]:
            myprint(1,'Invalid Status Code: %d (expected %d). Reason: %s' % (r.status_code, rqst["resp"]["code"], r.reason))
            if rqst["returnText"]:
                return ''
            else:
                return

        myprint(2,'Response Headers:', json.dumps(dict(r.headers), indent=2))
        
        # Optional parameter "dumpResponse"
        try:
            outputFile = os.path.join(mg.moduleDirPath, rqst["resp"]["dumpResponse"])
            if rqstStream:
                if csvStream:
                    with open(outputFile, 'wb') as f:
                        for line in r.iter_lines():
                            f.write(line+'\n'.encode())
                else:
                    r.raw.decode_content = True
                    myprint(1, "Saving raw text to %s" % outputFile)
                    with open(outputFile, 'wb') as f:
                        shutil.copyfileobj(r.raw, f)
            else:
                myprint(1, "dumpToFile(%s, r.text)" % outputFile)
                dumpToFile(outputFile, r.text)
        except:
            myprint(1, 'Error while saving response -or- No "dumpResponse" requested')
            pass
        
        # Update cookies
        if rqst["resp"]["updateCookies"]:
            self._updateCookies(r.cookies)
            
        if rqst["returnText"]:
            return r.text


####        
# Parse HTML file from prix-elec.com containing tariffs for TE
def parseTariffsPage(html):
    
    soup = BeautifulSoup(html, 'html.parser')
    
    outputDict = dict()
    
    table = soup.find('table', attrs={'class':'table'})
    table_body = table.find('tbody')

    myprint(2, 'table_body:', table_body)

    #<caption class="table__title">Tarifs du contrat Online Electricité de TotalEnergies</caption>
    #table_body_caption = table_body.find('caption')
    #myprint(2, 'table_body caption:', table_body_caption)
    
    rows = table_body.find_all('tr')
    for row in rows:
        power = row.find('th').text.strip().split()[0]
        cols = row.find_all('td')
        cols = [item.text.strip() for item in cols]
        outputDict[power] = cols

    #print(outputDict)
    return outputDict


####
# Retrieve the costs for "power" from json cache file
def getCostsFromCacheFile(power):
    costs = list()

    myprint(1, f'Using {mg.costsDataCachePath}. (power={power})')
    
    try:
        with open(mg.costsDataCachePath, 'r') as infile:
            jdata = json.load(infile)
            try:
                costs = jdata[power]
            except:
                myprint(0, f'Unable to cope with costs data')

    except Exception as error: 
        myprint(0, f'Unable to cope with costs cache file {mg.costsDataCachePath}')

    return costs


def dumpCosts(power, costs):
    # Costs Example:
    # yearly fee Base,  base,       yearly fee HC,  Cost HP,    Cost HC 
    # ['137.64€',       '0.1442€',  '145.83€',      '0.1678€',  '0.1263€']
    if len(costs) != 5:
        # Something went wrong with costs parsing            
        myprint(0, f'Unable to parse input costs')
        return
    else:
        oneDict = {
            "Yearly Fee Base":  costs[0],
            "€/kWH Base":	costs[1],
            "Yearly Fee HC":	costs[2],
            "€/kWH HP":		costs[3],
            "€/kWH HC":		costs[4],            
        }
        print(f'{color.BOLD}Meter Power: {power}{color.END} kVA')
        print(json.dumps(oneDict, ensure_ascii=False))
        

def getTariffsInfoFromPrixElecServer(costsDataCachePath):
    with requests.session() as session:
        # Create connection to Prix-Elec.com server
        tec = TotalEnergiesCosts(session)
        # Get tariffs from server
        res = tec.getTariffsInformation(costsDataCachePath)
        return res
