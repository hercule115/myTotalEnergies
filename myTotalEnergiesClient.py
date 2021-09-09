from bs4 import BeautifulSoup
from csv import reader
from datetime import datetime
import json
import os
import requests
import shutil
import sys
import unicodedata

from common.utils import myprint, dumpToFile, findBetween, lastLineFromConsumptionFile, parseConsumptionData, diff_month, parseRow
import httpHeaders as hh
import myGlobals as mg
import authinfo
import config

# Dictionary containing the HTTP requests to send to the server
TE_HTTP_REQUESTS = {
    "initialPage" : {
        "info" : "Connect to www.totalenergies.fr and get index page",
        "rqst" : {
            "type" : 'GET',
            "url"  : 'https://www.totalenergies.fr/clients/connexion',
            "headers" : {
                "Host"   : 'www.totalenergies.fr',
                "Upgrade-Insecure-Requests" : "1",
            },
        },
        "resp" : {
            "code" : 200,
            #"dumpResponse" : 'www.totalenergies.fr.html',
            "updateCookies" : True,
        },
        "returnText" : True,
    },

    "logo-te-verti" : {
        "info" : "Get TotalEnergies Logo",
        "rqst" : {
            "type"    : 'GET',
            "url"     : 'https://www.totalenergies.fr/fileadmin/mails/te/logo-te-verti.png',
            "stream"  : True,
            "headers" : {
                "Accept" : 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                "Host"   : 'www.totalenergies.fr',
                "Referer": 'https://www.totalenergies.fr/',
                "Sec-Fetch-Mode" : 'no-cors',
                "Sec-Fetch-Site" : 'cross-site',
                "Sec-Fetch-Dest" : 'image',
                "Cookie" : [],	# updated dynamically
           },
        },
        "resp" : {
            "code" : 200,
            "dumpResponse" : 'logo-te-verti.png',
            "updateCookies" : True,
        },
        "returnText" : False,
    },

    "login" : {
        "info" : 'Initiate login process, update some cookies',
        "rqst" : {
            "type" : 'POST',
            "url"  : '',	# Updated dynamically
            "payload" : '',     # Updated dynamically {"password":"put-password-here","remember":true}',            
            "headers" : {
                "Accept" : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                "Host"   : 'www.totalenergies.fr',
                "Origin" : 'https://www.totalenergies.fr',
                "Referer": 'https://www.totalenergies.fr/clients/connexion',
                "Upgrade-Insecure-Requests" : '1',
                "Content-Type" : 'application/x-www-form-urlencoded',
                "Sec-Fetch-Mode" : 'navigate',
                "Sec-Fetch-Site" : 'same-origin',
                "Sec-Fetch-Dest" : 'document',
                "Cookie" : ['TS0195a14f', 'TS8919be72027']                
            },
        },
        "resp" : {
            "code" : 200,
            "updateCookies" : True,
            #"dumpResponse" : 'login.totalenergies.fr.html',            
        },
        "returnText" : True,
    },

    "logout" : {
        "info" : "Logout from TotalEnergies server",
        "rqst" : {
            "type"    : 'GET',
            "url"     : '',	# Updated dynamically
            "headers" : {
                "Accept" : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                "Host"   : 'www.totalenergies.fr',
                "Referer": 'https://www.totalenergies.fr/clients/accueil',
                "Sec-Fetch-Mode" : 'navigate',
                "Sec-Fetch-Site" : 'same-origin',
                "Sec-Fetch-Dest" : 'document',
                "Upgrade-Insecure-Requests" : '1',
                "Cookie" : ['TS0195a14f', 'TS8919be72027']
           },
        },
        "resp" : {
            "code" : 200,
            "updateCookies" : False,
        },
        "returnText" : False,
    },

    "ma-conso-elec" : {
        "info" : "Get Electricity consumption",
        "rqst" : {
            "type" : 'GET',
            "url"  : 'https://www.totalenergies.fr/clients/ma-conso/ma-conso-elec',
            "headers" : {
                "Accept" : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                "Host"   : 'www.totalenergies.fr',
                "Referer": 'https://www.totalenergies.fr/clients/accueil',
                "Upgrade-Insecure-Requests" : "1",
                "Sec-Fetch-Mode" : 'navigate',
                "Sec-Fetch-Site" : 'same-origin',
                "Sec-Fetch-Dest" : 'document',
                "Cookie" : ['TS0195a14f', 'TS8919be72027']
            },
        },
        "resp" : {
            "code" : 200,
            #"dumpResponse" : 'ma-conso-elec.totalenergies.fr.html',
            "updateCookies" : True,
        },
        "returnText" : False,
    },

    "mon-historique-conso-electricite" : {
        "info" : "Get Electricity consumption history",
        "rqst" : {
            "type" : 'GET',
            "url"  : 'https://www.totalenergies.fr/clients/ma-conso/ma-conso-elec/mon-historique-de-conso-electricite',
            "headers" : {
                "Accept" : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                "Host"   : 'www.totalenergies.fr',
                "Referer": 'https://www.totalenergies.fr/clients/ma-conso/ma-conso-elec',
                "Upgrade-Insecure-Requests" : "1",
                "Sec-Fetch-Mode" : 'navigate',
                "Sec-Fetch-Site" : 'same-origin',
                "Sec-Fetch-Dest" : 'document',
                "Cookie" : ['TS0195a14f', 'TS8919be72027']
            },
        },
        "resp" : {
            "code" : 200,
            #"dumpResponse" : 'mon-historique-conso-elec.totalenergies.fr.html',
            "updateCookies" : True,
        },
        "returnText" : True,
    },

    "mon-historique-conso-electricite-dataconsommation-par-interval" : {
        "info" : "Get Electricity consumption history by given interval",
        "interval" : '', # Updated dynamically
        "rqst" : {
            "type" : 'GET',
            "url"  : '', # Updated dynamically
            "stream"  : True,
            "csv"     : True,
            "headers" : {
                "Accept" : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                "Host"   : 'www.totalenergies.fr',
                "Referer": 'https://www.totalenergies.fr/clients/ma-conso/ma-conso-elec/mon-historique-de-conso-electricite',
                "Upgrade-Insecure-Requests" : "1",
                "Sec-Fetch-Mode" : 'navigate',
                "Sec-Fetch-Site" : 'same-origin',
                "Sec-Fetch-Dest" : 'document',
                "Cookie" : ['TS0195a14f', 'TS8919be72027', 'TS0195a14f030', 'fe_typo_user_sunshine_Production']
            },
        },
        "resp" : {
            "code" : 200,
            "dumpResponse" : '', # Updated dynamically
            "updateCookies" : True,
        },
        "returnText" : False,
    },
}

####
class TotalEnergies:
    def __init__(self, userName, userPassword, session):
        self._hostName = 'www.totalenergies.fr'
        self._username = userName
        self._password = userPassword
        self._session  = session
        
        # Dict to save cookies from server
        self._cookies = dict()
        
    @property
    def hostname(self):
        return self._hostName

    @property
    def headers(self):
        return self._headers.headers

    def getContractsInformation(self):
        assert(self._hostName)
        assert(self._session)
        assert(self._username)
        assert(self._password)

        # Execute "initialPage" request
        respText = self._executeRequest('initialPage')
        if 'ErRoR' in respText:
            myprint(1, "Error when executing 'initialPage' request")
            return respText

        # Parse output text to build 'login' request
        loginUrl, loginFormData = self._parseInitialPage(respText)

        # Set login request Url
        myprint(1, 'Login URL:', loginUrl)
        TE_HTTP_REQUESTS["login"]["rqst"]["url"] = '%s%s' % ('https://www.totalenergies.fr',loginUrl)
        
        # Set Form Data parameter
        payload = dict()
        for x in loginFormData:
            #myprint(0, x[0], x[1])
            payload[x[0]] = x[1]
        TE_HTTP_REQUESTS["login"]["rqst"]["payload"] = payload

        # Execute "logo-te-verti" request
        #self._executeRequest('logo-te-verti')

        # Execute "login" request
        respText = self._executeRequest('login')

        # Output dictionary
        outputDict = dict()
        
        # Parse output text to build 'logout' request
        info = self._parseLoginPage(respText)
        try:
            logoutUrl = '%s%s' % ('https://www.totalenergies.fr', info['logoutUrl'])
            # Set logout request Url
            myprint(1, 'Logout URL:', logoutUrl)
            TE_HTTP_REQUESTS["logout"]["rqst"]["url"] = logoutUrl
        except:
            myprint(1, 'Logout URL not found in Login page')

        # Save 'consumption' information
        outputDict["powerCons"] = info["powerCons"]

        # Save 'dataLayer' misc information
        outputDict["dataLayer"] = info["dataLayer"]
        
        self._executeRequest('ma-conso-elec') # Required ???

        respText = self._executeRequest('mon-historique-conso-electricite')
        # Parse output text to get all URLS to download history files
        info = self._parseMonHistoriqueConsoElecPage(respText)

        for interval in info['DataConsommation']:
            # Check if this interval is requested
            if not interval in mg.consumptionFilesDict:
                myprint(1, 'Skipping interval %s' % (interval))
                continue

            myprint(1, 'Downloading consumption for interval: %s' % (interval))
            url = info['DataConsommation'][interval]
            #myprint(1, 'URL info["DataConsommation"][%s] = %s' % (interval, url))

            # Set URL to get consumption history in a file
            TE_HTTP_REQUESTS["mon-historique-conso-electricite-dataconsommation-par-interval"]["interval"] = interval
            TE_HTTP_REQUESTS["mon-historique-conso-electricite-dataconsommation-par-interval"]["rqst"]["url"] = url

            # Set output file
            TE_HTTP_REQUESTS["mon-historique-conso-electricite-dataconsommation-par-interval"]["resp"]["dumpResponse"] = mg.consumptionFilesDict[interval]

            # Get consumption history in a file
            self._executeRequest('mon-historique-conso-electricite-dataconsommation-par-interval')

        myprint(1, 'Computing day by day consumption')
        outputDict["consByDays"] = self._buildConsByDays()

        myprint(1, 'Computing month by month consumption')        
        outputDict["consByMonths"] = self._buildConsByMonths()
        
        # Return normalized JSON data
        return outputDict

    def _buildConsByDays(self):
        # Parse .consumption-by-JOUR.csv data file and compute
        #consumption for each and every *complete* day (48 measurements)
        #Électricité;01/07/2021;"2.4 kWh"

        inputFile = mg.consumptionFilesDict['JOUR']
        if not os.path.isfile(inputFile):
            myprint(0, '%s consumption file does not exist' % (inputFile))
            return {}

        myprint(1, f'Parsing file: {inputFile}')

        outputDict = dict()
        
        try:
            with open(inputFile, 'r') as f:
                csvReader = reader(f)
                next(csvReader) # Discard 1st line

                # Iterate over each row in the csv using reader object
                for row in csvReader:
                    resource,date,rawCons = row[0].split(';')

                    cons = float(rawCons.replace('"','').split(' ')[0]) # Keep numeric value only
                    unit = rawCons.replace('"','').split(' ')[1] # Keep unit only                    

                    try:
                        dts = datetime.strptime(date, '%d/%m/%Y').strftime('%Y-%m-%d')
                        # Build a long date to be used as name (Thursday, April 4 2030)
                        longDate = datetime.strptime(date, '%d/%m/%Y').strftime('%A, %B %d %Y')
                        # Get month name
                        #monthName = datetime.strptime(date, '%d/%m/%Y').strftime('%B')
                        # Get year
                        #year = datetime.strptime(date, '%d/%m/%Y').strftime('%Y')

                    except:
                        myprint(1, 'ERROR while parsing date: %s' % date)

                    if dts in outputDict:
                        myprint(1, 'Skipping duplicate line for date %s' % (dts))
                        continue

                    # Add this record to output dict
                    outputDict[dts] = (cons, unit, longDate)
        except:
            myprint(0, 'ERROR while parsing input file')
            return {} # Empty dict
        
        #print(json.dumps(outputDict, indent=4))
        return outputDict


    def _buildConsByMonths(self):
        # Parse .consumption-by-MOIS.csv data file

        inputFile = mg.consumptionFilesDict['MOIS']
        if not os.path.isfile(inputFile):
            myprint(0, f'{inputFile} consumption file does not exist')
            return {}

        myprint(1, f'Parsing file: {inputFile}')
        
        try:
            with open(inputFile, 'r') as f:
                csvReader = reader(f)
                next(csvReader) # Discard 1st line

                months = dict()

                hack = None	# Used to store invalid input row
                
                # Iterate over each row in the csv using reader object
                # Example: Électricité;09/2018;09/2018;"101 kWh"
                for row in csvReader:
                    isError, records = parseRow(row, hack)
                    if isError == True:
                        hack = records[0]	# Save our hack record to be used in the next loop
                        continue

                    # rowAsList = row[0].split(';')

                    # resource     = rowAsList[0]
                    # fullDate0AsString = rowAsList[1] #.replace('"','')
                    # fullDate1AsString = rowAsList[2] #.replace('"','')
                    # if fullDate0AsString != fullDate1AsString:
                    #     #dts0 = datetime.strptime(fullDate0AsString, '%m/%Y').strftime('%Y-%m-%d')
                    #     dts0 = datetime.strptime(fullDate0AsString, '%m/%Y')
                    #     dts1 = datetime.strptime(fullDate1AsString, '%m/%Y')
                    #     if diff_month(dts1, dts0) > 1:
                    #         myprint(1, 'Skipping malformed input: %s' % (row))
                    #         continue
                    # dateAsString = fullDate0AsString[:7]
                    # consAsString = rowAsList[3].replace('"','')
                    # cons = int(consAsString.split(' ')[0])
                    # unit = consAsString.split(' ')[1]

                    # try:
                    #     dts = datetime.strptime(dateAsString, '%m/%Y').strftime('%Y-%m-%d')
                    #     # Build a long date to be used as name (ex: April 2030)
                    #     longDate = datetime.strptime(dateAsString, '%m/%Y').strftime('%B %Y')
                    # except:
                    #     myprint(1, 'ERROR while parsing date: %s' % dateAsString)

                    # if dts in months:
                    #     myprint(1, 'Skipping duplicate line for date %s' % (dts))
                    #     continue

                    # Update list of records
                    for item in records:
                        dateAsString = item[0]
                        month        = item[1]
                        year         = item[2]
                        #longDate     = item[3]
                        cons         = item[4]
                        unit         = item[5]

                        try:
                            dts = datetime.strptime(dateAsString, '%m/%Y').strftime('%Y-%m-%d')
                            # Build a long date to be used as name (ex: April 2030)
                            longDate = datetime.strptime(dateAsString, '%m/%Y').strftime('%B %Y')
                        except:
                            myprint(1, f'ERROR while parsing date: {dateAsString}')
                            continue
                        
                        myprint(2, f'Adding: {dateAsString} {month} {year} {longDate} {cons} {unit}')
                    
                        # Add this record to output dict
                        months[dts] = (cons, unit, longDate)

                    hack = None
        except:
            myprint(0, 'ERROR while parsing input file')
            return None

        return months

    
    # Logout from server
    def logout(self):
        #myprint(0, 'Bye Bye')
        # Execute "logout" request
        self._executeRequest('logout')


    def _parseInitialPage(self, text):
        formData = list()
    
        soup = BeautifulSoup(text, 'html.parser')

        #<div class="action__display-zone--1">
        div0 = soup.find("div", {"class": "action__display-zone--1"})

        form0 = div0.find("form", {"name": "authentificationForm"})
        url = form0.attrs['action'].strip('#fz-authentificationForm')
    
        div1 = div0.find("div", {"id": "c61360"})
        inputs = div1.find_all("input", {"type": "hidden"})
        for i in inputs:
            formData.append((i.attrs['name'], i.attrs['value']))

        inputs = form0.find_all("input", {"type": "hidden"})
        for i in inputs:
            formData.append((i.attrs['name'], i.attrs['value']))
        
        #<div fz-field-container="login" class="layout-fz--centrer fz-errors-fz-formulaire_erreur fz-valid-fz-formulaire_valide">
        div2 = div0.find("div", {"fz-field-container": "login"})
        inputs = div2.find_all("input", {"type": "text"})
        for i in inputs:
            formData.append((i.attrs['name'], self._username))
        
        #<div fz-field-container="password" class="layout-fz--centrer fz-errors-fz-formulaire_erreur fz-valid-fz-formulaire_valide">
        div3 = div0.find("div", {"fz-field-container": "password"})
        inputs = div3.find_all("input", {"id": "formz-authentification-form-password"})
        for i in inputs:
            formData.append((i.attrs['name'], self._password))

        return url,set(formData) # Keep unique values
        
    
    def _parseLoginPage(self, text):
        oInfo = dict()

        soup = BeautifulSoup(text, 'html.parser')
    
        a0 = soup.find("a", {"class": "btn--espace-client"})
        oInfo["logoutUrl"] = a0['href']

        # Get Misc. information
        head0 = soup.find("head")
        scripts = head0.find_all("script", {"type": "text/javascript"})
        for s in scripts:
            if 'dataLayer' in str(s.text):
                jsonValue = "{%s}" % (s.text.partition('[ {')[2].rpartition('} ]')[0],)
                value = json.loads(jsonValue)        
                oInfo["dataLayer"] = value

        # Get Power consumption from login page
        powerCons = dict()
    
        #<div class="cadre var--x var--blanc flex-child-grow text-center">
        div0 = soup.find("div", {"class": "cadre var--x var--blanc flex-child-grow text-center"})

        sps = div0.find_all("span")
        totalConsumptionDate = sps[0].contents[0]

        ps = div0.find_all("p")
        totalConsumption = ps[0].contents[0].split()
        totalConsumptionVol  = totalConsumption[0]
        totalConsumptionUnit = totalConsumption[1]

        # Add total cons to the powerCons dict
        powerCons["totalConsumptionDate"] = totalConsumptionDate
        powerCons["totalConsumptionVol"]  = totalConsumptionVol
        powerCons["totalConsumptionUnit"] = totalConsumptionUnit

        # Remove span and br tags in place
        for match in ps[1].findAll('span'):
            match.unwrap()
        for match in ps[1].findAll('br'):
            match.unwrap()
            
        l1 = list(map(lambda x:x.strip(),ps[1].contents))
        l1[:] = [x for x in l1 if x]

        lastMeasurementDate = l1[1].split()[1]

        lastMeasurement = l1[2].split()
        lastMeasurementVol  = lastMeasurement[0]
        lastMeasurementUnit = lastMeasurement[1]

        # Add measurement to the powerCons dict
        powerCons["lastMeasurementDate"] = lastMeasurementDate
        powerCons["lastMeasurementVol"] = lastMeasurementVol
        powerCons["lastMeasurementUnit"] = lastMeasurementUnit
    
        oInfo["powerCons"] = powerCons
        print(json.dumps(oInfo, indent=4))
        return oInfo
    

    def _parseMaConsoElecPage(self, text):
        return None


    def _parseMonHistoriqueConsoElecPage(self, text):
        monHistoUrls = dict()
    
        #<a class="btn--telecharger" href="/clients/ma-conso/ma-conso-elec/mon-historique-de-conso-electricite?tx_demmconso_dataconsommation%5Baction%5D=telechargerConsommations&amp;tx_demmconso_dataconsommation%5Bcontroller%5D=DataConsommation&amp;tx_demmconso_dataconsommation%5Btype%5D=30MIN&amp;cHash=502ba46e18a093cdbc1d5fdea0e4b768"> Télécharger mes consommations </a>

        HOST = 'https://www.totalenergies.fr'
    
        soup = BeautifulSoup(text, 'html.parser')
    
        atags = soup.find_all("a", {"class": "btn--telecharger"})
        for a in atags:
            # Build full URL
            url = '%s%s' % (HOST, a['href'])
            # Create controller in monHistoUrls{} if needed
            controller = findBetween(url, '%5Bcontroller%5D=', '&tx')
            if not controller in monHistoUrls:
                monHistoUrls[controller] = dict()
            # Find type
            type = findBetween(url, '%5Btype%5D=', '&cHash')
            #print(controller, type, url)
            # Add this URL to monHistoUrls
            monHistoUrls[controller][type] = url

        return monHistoUrls

    
    def _executeRequest(self, name):
        dt_now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        rqst = TE_HTTP_REQUESTS[name]
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
            myprint(1, 'Error while saving response / No "dumpResponse" requested')
            pass
        
        # Update cookies
        if rqst["resp"]["updateCookies"]:
            self._updateCookies(r.cookies)
            
        if rqst["returnText"]:
            return r.text

        
    def _findListResources (self, tag, attribute, soup):
        l = []
        for x in soup.findAll(tag):
            try:
                l.append(x[attribute])
            except KeyError:
                pass
        return(l)


    def _getScriptUrl(self, text, scriptName):
        scriptPath = ''
        
        soup = BeautifulSoup(text, 'html.parser')
        
        scripts_src = self._findListResources('script', 'src', soup)
        scriptUrl = [s for s in scripts_src if scriptName in s][0]
        return(scriptUrl)


    # Update our cookie dict
    def _updateCookies(self, cookies):
        #print(requests.utils.dict_from_cookiejar(self._session.cookies))
        for cookie in self._session.cookies:
            #print(cookie.name, cookie.value, cookie.domain)
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

#### Class Headers
class Headers():
    def __init__(self):

        # Request header prototype. Updated with specific request
        self._protoHeaders = {
            'Accept': 		'*/*',
            'Accept-Encoding': 	'gzip, deflate, br',
            'Accept-Language': 	'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 	'no-cache',
            'Connection': 	'keep-alive',
            'Pragma': 		'no-cache',
            'User-Agent': 	'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.67 Safari/537.36'
        }

        self._h = self._protoHeaders

    @property
    def headers(self):
        return self._h

    def setHeader(self, hdr, val):
        self._h[hdr] = val

    # Return header value if found
    def getHeader(self, hdr):
        try:
            val = self._h[hdr]
        except:
            return None
        return val
    
    def getCookie(self, cookie):
        for k,v in self._h.items():
            if k == 'Set-Cookie':
                cookies = v.split(';')
                for c in cookies:
                    try:
                        cc = c.split('=')
                    except:
                        myprint(1,'Skipping %s' % cc)
                        continue
                    if cc[0] == cookie:
                        return cc[1]
        return None
