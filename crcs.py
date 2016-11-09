import pandas as pd
import csv
import logging
import re
import zlib
import time
from os3.sc import *

PATH = '/media/nekraid01/Anime'
OUTPUT = 'nekraid01.csv'

COLUMNS = ('path', 'name', 'crc')

df = pd.read_csv(OUTPUT, sep=',', usecols=COLUMNS, header=None, names=COLUMNS)

# print(df.loc[df['crc'] == '6D7'].empty)

# df.append(pd.DataFrame([['Foo', 'bar', 'AE7A59BE']], columns=COLUMNS))

# Colores
c_null = "\x1b[00;00m"
c_red = "\x1b[31;01m"
c_green = "\x1b[32;01m"
p_reset = "\x08" * 8

last_save = 0


# def add_to_csv(line, file=OUTPUT):
#     with open(file, 'a') as f:
#         c = csv.writer(f)
#         c.writerow(line)


def add_to_csv(line, file=OUTPUT):
    global df, last_save
    df = df.append(pd.DataFrame([line], columns=COLUMNS))
    if time.time() > last_save + 20:
        df.to_csv(file, index=False, header=False)
        last_save = time.time()


def crc32_checksum(filename):
    """Generador del CRC del archivo
       filename: string
                 Ruta al archivo"""

    # Variables para comprobación
    crc = 0
    file = open(filename, "rb")
    buff_size = 65536
    size = os.path.getsize(filename)
    done = 0

    if not size:
        # El archivo no tiene tamaño, salir
        logging.error('El archivo %s no tiene datos' % filename)
        return
    try:
        while True:
            # Mientras haya datos...
            data = file.read(buff_size)
            done += buff_size
            # informar de situación actual de conteo
            sys.stdout.write("%7d" % (done * 100 / size) + "%" + p_reset)
            if not data:
                # Ya no hay más datos, salir
                break
            crc = zlib.crc32(data, crc)
    except KeyboardInterrupt:
        # Detectada excepción de interrupción por teclado
        sys.stdout.write(p_reset)
        # Cerrar el archivo
        file.close()
        sys.exit(1)
    sys.stdout.write("")
    # !!!Cerrar el archivo
    file.close()
    # Cálculo
    if crc < 0:
        crc &= 2 ** 32 - 1
    return "%.8X" % (crc)


for file in ls(PATH, depth=True).filter(type='f'):
    path = file.path
    if not df.loc[df['path'] == path].empty:
        continue
    file_crc = re.findall("\[([a-fA-F0-9]{8})\]", file.name)
    if not file_crc:
        file_crc = crc32_checksum(file.path)
    else:
        file_crc = file_crc[0]
    add_to_csv((file.path, file.name, file_crc))
