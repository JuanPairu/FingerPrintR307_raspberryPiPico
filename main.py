from machine import UART, Pin,I2C
import urequests
import time
from wlan import do_connect
import json
from ssd1306 import SSD1306_I2C

do_connect()


# Configuración de I2C y pantalla OLED
i2c = I2C(1, scl=Pin(19), sda=Pin(18))
oled = SSD1306_I2C(128, 64, i2c)

def mostrar(text1,text2):
    oled.fill(0)
    oled.text(text1,22,22)
    oled.text(text2,22,42)
    oled.show()


fingerPrint = UART(0, baudrate=57600, tx=Pin(0), rx=Pin(1))
sensor_dedo = Pin(10,Pin.IN,Pin.PULL_UP)
boton = Pin(11,Pin.IN,Pin.PULL_DOWN)
led = Pin(12,Pin.OUT)
estado = True
ultimo_estado_boton = 0
reset = Pin(13,Pin.IN,Pin.PULL_DOWN)
#constantes

#fingerprint
genImg = b'\xEF\x01\xFF\xFF\xFF\xFF\x01\x00\x03\x01\x00\x05'
im2Tz =  b'\xEF\x01\xFF\xFF\xFF\xFF\x01\x00\x04\x02\x01\x00\x08'
search =  b'\xEF\x01\xFF\xFF\xFF\xFF\x01\x00\x08\x04\x01\x00\x00\x03\xE8\x00\xF9'
templeteNum = b'\xEF\x01\xFF\xFF\xFF\xFF\x01\x00\x03\x1D\x00\x21'
deleteAll = b'\xEF\x01\xFF\xFF\xFF\xFF\x01\x00\x07\x0C\x00\x00\x03\xE8\x00\xFF' # eliminar todas las huellas
#consulta a fireStore
url = "https://us-central1-appinvitados.cloudfunctions.net/api"
headers = {'Content-Type': 'application/json'}


#verifica la cantidad de huellas dactilares en la memoria interna del sensor
def num_finger():
    fingerPrint.write(templeteNum)
    while fingerPrint.any() == 0: pass
    resp = fingerPrint.read()
    return resp[10]*16*16 + resp[11]

#toma la imagen de la huella del sensor 
#convierte la imagen del sensor en caracteres binarios para almacenarlo en la biblioteca o comparar con la biblioteca
def generar_caracter():
    gen = True
    while gen:
        fingerPrint.write(genImg)
        while fingerPrint.any() == 0: pass
        resp = fingerPrint.read()
        if (resp[9] == 0):
            gen = False
        time.sleep(.3)
            
    fingerPrint.write(im2Tz)
    while fingerPrint.any() == 0: pass
    resp = fingerPrint.read()
    mostrar("caracter","generado")

#con la imagen en binario alamcena en la biblioteca en un espacio de memoria (0 - 999)

def registrar(id_page):
    b_low = id_page%256
    b_high = int(id_page/256)
    sumTotal = 14 + b_high + b_low
    b_sum0 = sumTotal%256
    b_sum1 = int(sumTotal/256)
    store = b'\xEF\x01\xFF\xFF\xFF\xFF\x01\x00\x06\x06\x01'+ bytes([b_high,b_low,b_sum1,b_sum0])
    generar_caracter()
    
    fingerPrint.write(store)
    while fingerPrint.any() == 0: pass
    resp = fingerPrint.read()
    print('huella registrada con exito\n ID: ',id_page)
    mostrar("huella registrada", str(id_page))

#Con la imagen en binario compara con la memoria desde el ID 0  al 999
def buscar():
    generar_caracter()
    
    fingerPrint.write(search)
    while fingerPrint.any() == 0: pass
    resp = fingerPrint.read()
    if (resp[9] == 0):
        ID = resp[10]*16*16 + resp[11]
        print('ID: ',ID)
        mostrar("ID",str(ID))
        return (ID)
    else :
        print('no se encontro la huella')
        mostrar("No se encontro", "huella")
        return None 

if reset.value():
    fingerPrint.write(deleteAll)
    time.sleep(.1)
    while fingerPrint.any() == 0: pass
    com =fingerPrint.read()
    if (com[9] == 0):
        for _ in range(3):
            led.toggle()
            time.sleep(.5)

numPlantilla = num_finger() + 1


while True:
    estado_boton = boton.value()
    if estado_boton == 1 and ultimo_estado_boton == 0:
        estado = not estado  # Cambiar el estado
        time.sleep(0.1)  # Debounce manual
    ultimo_estado_boton = estado_boton

    if estado:
        # Comparación con biblioteca
        led.value(1)
        if sensor_dedo.value() == 0:
            ID = buscar()
            if ID != None:
                while sensor_dedo.value() == 0: pass
                try:                    
                    data = json.dumps({"id": ID}) #plantilla desfasadoen uno
                    response = urequests.post(url + "/buscar", data=data, headers=headers,timeout = 10)
                    print(response.status_code)
                    print(response.text)
                    response.close()
                except:
                    print('error verificar')
            
            time.sleep(.5)
    else:
        # Cargar biblioteca
        led.value(0)
        if sensor_dedo.value() ==0:
            registrar(numPlantilla)
            while sensor_dedo.value() == 0: pass
            
            try:                    
                data = json.dumps({"id": numPlantilla}) #plantilla desfasadoen uno
                numPlantilla += 1
                response = urequests.post(url + "/crear", data=data, headers=headers,timeout = 10)
                print(response.status_code)
                print(response.text)
                response.close()
            except:
                numPlantilla -= 1
                print('huella no almacenada')
                mostrar("huella no","almacenada")

            time.sleep(.5)

    time.sleep(0.1)  # Tiempo base del bucle
    