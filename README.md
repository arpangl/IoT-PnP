# IoT-PnP
Plug and Play on Internet of Things with LoRa wireless modulation.

---
## Device Side
In the '505_PnP' folder has a modified ardunino template code suit for infrared sensor(HC-SR505). To implement the code with different sensor, ones only need to import the needed library, modify the `doSense()` fucntion to make it send data you want(Note: 256bytes max), and **DONT FORGET** to  modify the compacted description file and device id. 

---
## Gateway Side
In the 'Gateway_pi' folder has a gateway python code that is currently running on the real enviroment, so modify it carefully. 
