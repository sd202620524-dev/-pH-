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
-----------------------------------------------------------------
# ph_led.py
# Grove - PH Sensor Kit (E-201C-Blue), SKU 110020291
# Raspberry Pi Pico / MicroPython
# 센서 보드: VCC=3.3V, GND=GND, 아날로그 SIG=GP26
# 공통 캐소드 RGB LED: R/G/B 각각 330옴을 거쳐 GP16/17/18
from machine import ADC, Pin
import time

ADC_REF = 3.3
BUFFER_ACID = 4.00
BUFFER_ALKALI = 9.18  # 표준용액 병에 표시된 값에 맞게 수정

# 아래는 프로젝트용 구간이며 화학적 산/염기 강도 분류가 아닙니다.
ACID_MIN = 4.5
NEUTRAL_MIN = 6.5
NEUTRAL_MAX = 7.5
ALKALI_MAX = 9.0

adc = ADC(Pin(26))
red = Pin(16, Pin.OUT)
green = Pin(17, Pin.OUT)
blue = Pin(18, Pin.OUT)

def led(r, g, b):
    red.value(r)
    green.value(g)
    blue.value(b)

def voltage():
    values = []
    for _ in range(25):
        values.append(adc.read_u16())
        time.sleep_ms(20)
    values.sort()
    return sum(values[5:-5]) / 15 * ADC_REF / 65535

def calibrate(buffer_ph):
    input("pH %.2f 표준용액에 담가 값이 안정된 뒤 Enter: " % buffer_ph)
    v = voltage()
    if not 0.03 < v < ADC_REF - 0.03:
        raise ValueError("입력 전압 한계 근처입니다. 배선과 전원을 확인하세요.")
    print("보정 전압: %.4f V" % v)
    return v

def ph_from_voltage(v, va, vb):
    # 제조사의 두 표준용액 선형 보정 방식
    return BUFFER_ACID + (v-va) * (BUFFER_ALKALI-BUFFER_ACID) / (vb-va)

def classify(ph):
    if ACID_MIN <= ph <= NEUTRAL_MIN:
        return (0, 1, 0), "약산성 구간"
    if NEUTRAL_MIN < ph <= NEUTRAL_MAX:
        return (0, 0, 0), "중성 부근: 판정 제외"
    if NEUTRAL_MAX < ph < ALKALI_MAX:
        return (0, 0, 1), "약알칼리성 구간"
    return (1, 0, 0), "설정한 두 구간 밖"

def main():
    led(0, 0, 0)
    try:
        print("Grove E-201C-Blue / 110020291 / 3.3V 전원")
        print("용액을 바꿀 때 전극을 헹구세요. 보정값은 종료 시 사라집니다.")
        va = calibrate(BUFFER_ACID)
        vb = calibrate(BUFFER_ALKALI)
        if abs(vb-va) < 0.05:
            raise ValueError("보정 전압 차이가 너무 작습니다. 용액/연결을 확인하세요.")

        input("전극을 헹구고 세안제 시료에 담가 안정된 뒤 Enter: ")
        while True:
            v = voltage()
            ph = ph_from_voltage(v, va, vb)
            if not 0.03 < v < ADC_REF - 0.03 or not 0 <= ph <= 14:
                led(1, 0, 1)
                print("측정 오류: 배선/전원/보정 확인 / %.4f V" % v)
            else:
                color, label = classify(ph)
                led(*color)
                suffix = ""
                if not BUFFER_ACID <= ph <= BUFFER_ALKALI:
                    suffix = " [보정 범위 밖 추정값]"
                print("pH %.2f / %s%s" % (ph, label, suffix))
            time.sleep(1)
    finally:
        led(0, 0, 0)

if __name__ == "__main__":
    main()

