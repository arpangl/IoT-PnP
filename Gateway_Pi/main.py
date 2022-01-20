import requests
import csv
from datetime import datetime as dt
import json
import board
import busio
import digitalio
import adafruit_rfm9x
import os

# Define Service URL
Service_URL = "220.133.40.181:8080"

# Define radio parameters.
RADIO_FREQ_MHZ = 433.0

# Define CS/RST port
CS = digitalio.DigitalInOut(board.CE1)
RESET = digitalio.DigitalInOut(board.D25)

# Initialize SPI bus.
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# Initialze RFM radio
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ, baudrate=115200)

# You can however adjust the transmit power (in dB).  The default is 13 dB but
# high power radios like the RFM95 can go up to 23 dB:
rfm9x.tx_power = 23

# Get current file path
curPath = os.path.abspath(__file__)
curDir = os.path.dirname(curPath)
os.chdir(curDir)



# To avoid IO delay, we keep a copy of database in memory 
LocalDatabase = {'Device_ID':[], 'Datastream_ID':[]}
def updateDataFromFile():
    with open('lookuptable.csv', 'r', newline='') as csvfile:
        rows = csv.DictReader(csvfile)
        for row in rows:
            LocalDatabase.get('Device_ID').append(row['Device_ID'])
            LocalDatabase.get('Datastream_ID').append(row['Datastream_ID'])

# acquire data from local file
updateDataFromFile()

# send/get info from service
def requestOperationsSTA(Opt, Url, Data):
    if Opt == 'postJson':
        try:
            response = requests.post(Url, json = Data)
        except:
            printLog('Unexcepted error when uploading.')
            return 
        else:
            return response
    elif Opt == 'postRaw':
        try:
            headers = {'content-type': 'application/json'}
            response = requests.post(Url, data = Data, headers = headers)
        except:
            printLog('Unexcepted error when uploading.')
            return 0
        else:
            return response
    elif Opt == 'get':
        try:
            response = requests.get(Url)
            response = response.json()['value']
        except:
            printLog('Unexcepted error when getting.')
        else:
            return response



# inquiry Device ID from Service. If no found, return 404, else, return Thing_ID, Datastream_ID
def inquiryThingIDFromService(Device_ID):
    response = requestOperationsSTA('get', "http://"+Service_URL+"/FROST-Server/v1.0/Things?$filter=properties/UID eq '"+ Device_ID +"'&$select=@iot.id", 1)
    if len(response) == 0:
        return 'Not Found', 'Not Found'
    else:
        Thing_ID = str(response[0].get('@iot.id'))
        response = requestOperationsSTA('get', "http://"+Service_URL+"/FROST-Server/v1.0/Things("+Thing_ID+")/Datastreams", 1)
        return Thing_ID, response[0].get('@iot.id')

# inquiry Thing ID from LookUp table. If no found, return 404, if found, return Datastream_ID
def inquiryThingIDFromLocal(Device_ID):
    foundStatus = False
    for i in range(len(LocalDatabase.get('Device_ID'))):
        if LocalDatabase.get('Device_ID')[i] == Device_ID:
            foundStatus = True
            Datastream_ID = LocalDatabase.get('Datastream_ID')[i]
            
    # if device doesn't exist on local database, inquire from service. otherwise, request the desc file.
    if foundStatus == False:
        printLog("["+Device_ID+"] "+"Device hasn't registered on local database, inquiring from service server")
        Thing_ID, Datastream_ID = inquiryThingIDFromService(Device_ID)
        if (Datastream_ID == 'Not Found'):
            printLog("["+Device_ID+"] "+"Device hasn't registered on remote service, requesting description file")
        else:
            printLog("["+Device_ID+"] "+"Device is registered on remote service, updating local database")
            updateLocalFile(Device_ID, Thing_ID, Datastream_ID)
            printLog("["+Device_ID+"] "+"Done.")
        return Datastream_ID
        
    else:
        return Datastream_ID

# upload observation to service, return 201 if successfully created data
def uploadObsToService(Datastream_ID, Results):
    data = {'result':Results}
    response = requestOperationsSTA('postJson',"http://"+Service_URL+"/FROST-Server/v1.0/Datastreams("+str(Datastream_ID)+")/Observations", data)
    return response

# when new thing registered, upload the locale database file
def updateLocalFile(Device_ID, Thing_ID, Datastream_ID):
    Last_seen = str(dt.now().strftime("%m-%d%H:%M:%S"))
    with open('lookuptable.csv', 'a+', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([Device_ID, Thing_ID, Datastream_ID, Last_seen])
    updateDataFromFile()



# if the device isn't registered either in Local or in Service, request the description file.
def regProcess(Device_ID, rawData):
    # Structure: "UID, name, LocName, LocCor_X, LocCor_Y, DatastreamName, UOM_Name, UOM_Symbol, ObservedProperty_Name, Sensor_Name"
    DataList = rawData.split(',')
    DescriptionFile = f'{{"name":"{DataList[1]}", \
    "description":"{DataList[1]}", \
    "properties":{{ \
        "UID":"{DataList[0]}" \
    }}, \
    "Locations":[ \
        {{ \
            "name":"{DataList[2]}", \
            "description":"{DataList[2]}", \
            "encodingType":"application/vnd.geo+json", \
            "location":{{ \
                "type":"Point", \
                "coordinates":[{DataList[3]}, {DataList[4]}] \
            }} \
        }} \
    ], \
    "Datastreams":[{{ \
        "name":"{DataList[5]}", \
        "description":"{DataList[5]}", \
        "observationType":"www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement", \
        "unitOfMeasurement":{{ \
            "name":"{DataList[6]}", \
            "symbol":"{DataList[7]}", \
            "definition":"{DataList[6]}" \
        }}, \
        "ObservedProperty":{{ \
            "name":"{DataList[8]}", \
            "description":"{DataList[8]}", \
            "definition":"None" \
        }}, \
        "Sensor":{{ \
            "name":"{DataList[9]}", \
            "description":"{DataList[9]}", \
            "encodingType":"None", \
            "metadata":"None" \
        }} \
    }} \
    ] \
}}'
    printLog('['+ Device_ID +'] Created descritpion file.')
    response = requestOperationsSTA('postRaw','http://'+Service_URL+'/FROST-Server/v1.0/Things', DescriptionFile)
    printLog('['+ Device_ID +'] Created a new thing on service by the descritpion file.')

    # getting the new Thing_ID, Datastream_ID from service
    response = requestOperationsSTA('get', "http://"+Service_URL+"/FROST-Server/v1.0/Things?$filter=properties/UID eq '"+ Device_ID +"'&$select=@iot.id", 1)
    Thing_ID = str(response[0].get('@iot.id'))
    response = requestOperationsSTA('get', "http://"+Service_URL+"/FROST-Server/v1.0/Things("+Thing_ID+")/Datastreams", 1)
    Datastream_ID = str(response[0].get('@iot.id'))
    
    # import the Thing_ID and Datastream_ID to local database file
    updateLocalFile(Device_ID, Thing_ID, Datastream_ID)
    printLog('['+ Device_ID +'] Updating locale datebase...Done')
    
# Log System
def printLog(msg):
    msg = str(dt.now().strftime("%Y-%m-%d %H:%M:%S")) +' ' +str(msg)
    print(msg)
    with open('Gateway.log', 'a+') as file:
        file.write(msg+'\n')

# using LoRa module to send data
def sendData(msg):
    msg += '\0' # ending char needed
    rfm9x.send(bytes(msg, "utf-8"))
    

def processHandler(Device_ID, Result):

    Datastream_ID = inquiryThingIDFromLocal(Device_ID)

    # Situation 1: Device is registered in local database or only in service
    if (Datastream_ID != 'Not Found'):
        printLog("["+Device_ID+"] "+"Device is registered on local database, uploading observation: "+str(Result))
        uploadObsToService(Datastream_ID, Result)
        sendData(f'{{"UID":"{Device_ID}", "results":"201"}}')
    # Situation 2: Device is not registered in service
    else:
        sendData(f'{{"UID":"{Device_ID}", "results":"404"}}')


def main():
    packet = rfm9x.receive()
    # If no packet was received during the timeout then None is returned.
    if packet != None:
        try:
            packet_text = str(packet, "utf-8")
        except:
            printLog("Recived some noice, has dumped.")
        else:
            #printLog("Recived: " + packet_text[:-1])  # Note: to communicate with RH_RF95 module, the last char need to be dumped. (it's a '\0')
            try:                                       #       also, when we send data, it is needed to add '\0' to the end.
                receivedMsg = json.loads(packet_text[:-1])
            except:
                printLog("JSON parse error, might be wrong data format.")
            else:
                if receivedMsg.get('operation') == "UploadObs":
                    Device_ID = receivedMsg.get('device_ID')
                    Result = receivedMsg.get('results')
                    processHandler(Device_ID, Result)
                elif receivedMsg.get('operation') == "SendDesc":
                    Device_ID = receivedMsg.get('device_ID')
                    rawData = receivedMsg.get('msg_body')
                    regProcess(Device_ID, rawData)
                else:
                    printLog("This JSON might not be the wanted.")




print('\n\n    ******                         *******                          ')
print('      **              ******       **    **               *******    ')
print('      **      *****     **         **     **              **    **   ')
print('      **     **   **    **         ********               **     **  ')
print('      **     **   **    **         **         ** ****     ********   ')
print('    ******    *****     **         **         ***   **    **         ')
print('                                   **         **    **    **         ')
print('                                              **    **    **         ')

print('******************************************')
print('**         IoT PnP Gateway v1.0         **')
print('******************************************')

printLog('System Initialized!')

while True:
    main()
    

