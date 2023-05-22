# ------------------------------------------------------------------------------
## Carga de módulos
# ------------------------------------------------------------------------------
import json
from machine import Pin, PWM, ADC, SPI, Timer
import math
import cmath
import time
import sys
import uselect
# ------------------------------------------------------------------------------
SOURCE = 'Procesamiento de Señales'
# ------------------------------------------------------------------------------
# Configuración de entrada/salida &
# ------------------------------------------------------------------------------
led = PWM(Pin(14))
signal_in = ADC(26)
signal_out = PWM(Pin(14))
signal_out.freq(10000)

# ------------------------------------------------------------------------------
# ADC
# ------------------------------------------------------------------------------
def readInput():
    return signal_in.read_u16()
# ------------------------------------------------------------------------------
# DAC
# ------------------------------------------------------------------------------
def writeOutput(value: int):
    '''Write output to DAC '''
    signal_out.duty_u16(value)
    
# ------------------------------------------------------------------------------
# Comunicación serie
# ------------------------------------------------------------------------------
def parse_command(cmd):
    global params
    try:
        command = json.loads(cmd)
        # Escribe aquí el código para interpretar las órdenes recibidas
    except Exception as e:
        print('{"result":"unknown or malformed command"}')
        
# -------------------------------------------------------------------------------
# Implementación de algoritmo de la FFT
# -------------------------------------------------------------------------------
        
def diezmado_en_base_2(buffer):
    N = len(buffer)   # Sacamos longitud del buffer
    if N <= 1:
        return buffer # Comprobación de error (se corta si N <= 1)
    else:
        # Dividimos en dos subsecuencias pares e impares:
        par = buffer[0::2]      # Devuelve los elementos pares de buffer
        impar = buffer[1::2]    # Devuelve los elementos impares de buffer
        
        # Definimos Wkn de tal manera que pasándole los parámetros k, n y N, te devuelve el valor de la Wkn correspondiente
        def Wkn(k,n,N):
            return cmath.exp(-1j*2*math.pi/N*n*k)
        
        # Calculamos el vector de muestras F[k], de tamaño N/2, siendo cada uno de los F[k] el sumatorio con que va desde 0 hasta N/2 -1, y k a su vez va de 0 hasta N/2 -1
        F = [0 for k in range(int(N/2))] # Defino valores iniciales 0 para F
        
        for k in range(N/2):
            for n in range(N/2):
                F[k] = par[n]*Wkn(k,n,N/2) + F[k]
                
        # Lo mismo para el vector de muestras G[k]
        G = [0 for k in range(int(N/2))] # Defino valores iniciales 0 para G
        
        for k in range(N/2):
            for n in range(N/2):
                G[k] = impar[n]*Wkn(k,n,N/2) + G[k]
        
        # Ahora combinamos las subsecuencias con parte par sumando, y parte impar restando, para obtener X[k], yendo k desde 0 hasta N
        X = [0 for k in range(int(N))] # Defino valores iniciales 0 para X
        
        for k in range(N):
            if k < N/2:
                X[k] = F[k] + Wkn(k,1,N)*G[k]
            else:
                X[k] = F[k - int(N/2)] - Wkn(k,1,N)*G[k - int(N/2)]
        
        return X
        
# ------------------------------------------------------------------------------
# Bucle principal
# ------------------------------------------------------------------------------
#   1. Espera hasta el siguiente periodo de muestreo (PERIOD_US).
#   2. Genera la siguiente muestra de la señal y la envía a la salida (PWM).
#   3. Lee el valor de la entrada analógica (ADC).
# ------------------------------------------------------------------------------

def waitNextPeriod(previous):
    lapsed = time.ticks_us() - previous
    offset = -60
    remaining = PERIOD_US - lapsed + offset
    if 0 < lapsed <= PERIOD_US:
        time.sleep_us(remaining)
    return time.ticks_us()

def loop():
    state = []
    tLast = time.ticks_us()
    t0 = tLast
    spoll = uselect.poll()
    spoll.register(sys.stdin, uselect.POLLIN)
    while True:
        data = []
        for i in range(BUFFER_SIZE):
            try:
                t = waitNextPeriod(tLast)
                u = signal((t - t0) * 1e-6)
                y = readInput()
                buff[i] = y
                writeOutput(u) 

            except ValueError:
                pass
            data.append([(t - t0) * 1e-6, u, y])
            tLast = t
            
        # Transformada de Fourier discreta usando el algoritmo de diezmado temporal en base 2
        FFT = diezmado_en_base_2(buff)
                
        # Calculamos el módulo de la FFT
        absFFT = [0 for k in range(BUFFER_SIZE)]
        for j in range(BUFFER_SIZE):
            absFFT[j] = abs(FFT[j])
                
        print(f'Señal: {u} - Entrada: {y}\nEntradas de la FFT: {buff}\nFFT: {absFFT}\n')
        
        if spoll.poll(0):
            cmd = str(sys.stdin.readline())
            parse_command(cmd)    
            
# ------------------------------------------------------------------------------
# INSTRUCCIONES
# ------------------------------------------------------------------------------
PERIOD_US = 1000            # Periodo de muestreo en microsegundos
BUFFER_SIZE = 10            # Muestras en el buffer
buff = [0]*BUFFER_SIZE      # Inicializo el buffer a 0

def signal(t):
  # Pon aquí el código necesario para generar tu señal.
  
  T = 5
  w = 2*math.pi/T           # Valor de w = 2pi/T
  yt = math.cos(w*t)*65025  # Señal sinuoidal con valores que van de 0 (min) a 65025 (máx)
  return int(math.fabs(yt))

# ------------------------------------------------------------------------------
# Comienza la ejecución
# ------------------------------------------------------------------------------
loop()
