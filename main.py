# skin_temperature.py - GY-906 / MLX90614 / Pico / MicroPython
from machine import Pin, SoftI2C
import time

# SDA=GP4, SCL=GP5. 신호선 풀업 전압은 3.3V여야 합니다.
i2c = SoftI2C(sda=Pin(4), scl=Pin(5), freq=100000)
ADDRESS = 0x5A

def crc8(data):
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc

def object_temperature():
    # 0x07: 대상 표면 온도. 마지막 바이트는 통신 오류 검사값(PEC)
    data = i2c.readfrom_mem(ADDRESS, 0x07, 3)
    packet = bytes([ADDRESS << 1, 0x07, (ADDRESS << 1) | 1, data[0], data[1]])
    if crc8(packet) != data[2]:
        raise OSError("PEC 통신 오류")
    raw = data[0] | (data[1] << 8)
    if raw & 0x8000:
        raise OSError("센서 측정 오류")
    return raw * 0.02 - 273.15

def measure(label):
    while True:
        input(label + ": 같은 피부 부위에 센서를 고정하고 Enter: ")
        try:
            values = []
            for _ in range(10):
                values.append(object_temperature())
                time.sleep_ms(200)
            result = sum(values) / len(values)
            print("%s: %.2f 도C (10회 평균)" % (label, result))
            return result
        except OSError as error:
            print("측정 실패:", error, "/ 배선과 위치를 확인하고 재시도하세요.")

time.sleep(1)
if ADDRESS not in i2c.scan():
    raise RuntimeError("MLX90614(0x5A)가 없습니다. 전원/SDA/SCL을 확인하세요.")

before = None
print("1: 세안 전 / 2: 세안 후 / r: 초기화 / q: 종료")
while True:
    command = input("명령: ").strip().lower()
    if command == "1":
        before = measure("세안 전")
    elif command == "2":
        if before is None:
            print("먼저 1을 입력하여 세안 전 온도를 측정하세요.")
            continue
        after = measure("세안 후")
        print("세안 전 %.2f / 세안 후 %.2f 도C" % (before, after))
        print("변화(후-전): %+.2f 도C" % (after-before))
    elif command == "r":
        before = None
        print("저장된 세안 전 값을 지웠습니다.")
    elif command == "q":
        break
    else:
        print("1, 2, r, q 중 하나를 입력하세요.")
