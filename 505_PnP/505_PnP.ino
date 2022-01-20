/*** Setup Before Deployment ***/
const String UID = "MALE_01_USG";


/**
 * Before deployment, please remove all 'waitPacketSent()' function in RadioHead library
 * That function could cause unusual power consumption and cause the LoRa malfunction.
 */
 
#include <SPI.h> // Import SPI library
#include <RH_RF95.h> // RF95 from RadioHead Library
#include <ArduinoJson.h> // Arduino JSON Parser
#include <avr/pgmspace.h> // Arduino PROGMEM Library

#define RFM95_CS 10 //CS if Lora connected to pin 10
#define RFM95_RST 9 //RST of Lora connected to pin 9
#define RFM95_INT 2 //INT of Lora connected to pin 2 orinally

// Change to 434.0 or other frequency, must match RX's freq!
#define RF95_FREQ 433.0

// The length of the headers we add.
// The headers are inside the LORA's payload
#define RH_RF95_HEADER_LEN 4

// The trasmit power of the LoRa -> could help saving power
#define TRANSMIT_POWER 23

// Singleton instance of the radio driver
RH_RF95 rf95(RFM95_CS, RFM95_INT);


/**
 * This file can be a LoRa PnP template.
 * Modifying the doSense() with properly imported library and setup.
 * Other things are gracefully handled :)
 */

int pre_dis = 2;

void doSense(){
  //Serial.println(RamIndicator());
  //double distance = distanceSensor.measureDistanceCm();
  int distance = 100;
  if(digitalRead(5)==HIGH) {
    distance = 1;
 }
  else {
    distance = 0;
 }
  delay(1000);
  Serial.println(distance)
  if (distance != pre_dis){
    String result = String(distance);
    UploadObs(result);
    pre_dis = distance;
  }
  
}

void setup() {
  
  Serial.begin(115200); // Initialize Serial Montitor

  while(!rf95.init()){
    Serial.println(F("LoRa radio init failed!"));
    delay(3000);
  }

  Serial.println(F("LoRa radio init OK!"));

  if (!rf95.setFrequency(RF95_FREQ)){
    Serial.println(F("Set Frequenct Failed!"));
    delay(3000);
  }

  rf95.setTxPower(TRANSMIT_POWER, false);  // Transmission Power of the LoRa module
  pinMode(5,INPUT);
  digitalWrite(5,LOW);
}


void loop() {
  doSense();
}

// For sending data, Msg should be handled as String
void sendData(String Msg){
  int n = Msg.length();
  char* toChar = new char[n+1];
  strcpy(toChar, Msg.c_str());
  rf95.send((uint8_t *) toChar, n+1);
  delete toChar;
}



// Response code: 201 Created, 404 Not Found, 504 Bad Gateway.
// If the gateway didn't response in 5 seconds, will deem as package lost.
// If received 404 Not Found, will send descrption file to the gateway.
int waitResponse(){ 
  //Serial.println(RamIndicator());
  Serial.println(F("Uploaded observation, waiting for response..."));
  int response = 0;
  unsigned int ini_time = millis();
  unsigned int cur_time;
  StaticJsonDocument<50> json_doc;
  DeserializationError json_error;

  uint8_t buf[RH_RF95_MAX_MESSAGE_LEN];
  uint8_t len = sizeof(buf);
  while(response == 0){
    cur_time = millis();
    
    if (rf95.available()){
      json_doc["results"] = "";
      json_doc["UID"] = "";

      Serial.println(F("Receiving packet..."));
      if (rf95.recv(buf, &len)){
        //RH_RF95::printBuffer("Received: ", buf, len);
        //Serial.print("Got: ");
        String decodechar = (char*)buf;
        //Serial.println(decodechar);
        json_error = deserializeJson(json_doc, decodechar);

        if (!json_error){
          String rec_UID = json_doc["UID"];
          int results = json_doc["results"];
          if (rec_UID == UID && results == 404){
            response = 404;
            Serial.println(F("404 Not Found"));
          }

          else if (rec_UID == UID && results == 201){
            response = 201;
            Serial.println(F("201 Created"));
          }
          else{
            response = 500;
            Serial.println(F("Something went wrong."));
          }
        }
        else{
          Serial.println(F("Received Error. Might be wrong data format, or missed"));
          response = 0;
          delay(500);
        }
      }
    }
    else if (((cur_time-ini_time)/1000)>1){
      Serial.println(F("504 Bad Gateway"));
      response = 504;
    }
  }
  //Serial.println(RamIndicator());
  
  return response;
}

//int freeRam () 
//{
//  extern int __heap_start, *__brkval; 
//  int v; 
//  return (int) &v - (__brkval == 0 ? (int) &__heap_start : (int) __brkval); 
//}

//String RamIndicator(){
//  String str2 = String(freeRam());
//  String str3 = " bytes.";
//  return str2 + str3;
//}

void UploadObs(String result){
  //Serial.println(RamIndicator());
  String Obs = "\"results\":" + result;
  Serial.println(Obs);
  String UploadString = "{\"operation\":\"UploadObs\",\"device_ID\":\""+ UID +"\","+ Obs +"}";
  sendData(UploadString);
 
//  Serial.println(RamIndicator());
  int response = waitResponse();
  if (response == 504){
    sendData(UploadString);
    response = waitResponse();
  }
  if (response == 504){
    sendData(UploadString);
    response = waitResponse();
  }

}
