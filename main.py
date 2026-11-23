pH 센서-LED 센서 코드

# ph_led.py
# Grove - PH Sensor Kit (E-201C-Blue), SKU 110020291
# Raspberry Pi Pico / MicroPython
# 센서 보드: VCC=3.3V, GND=GND, 아날로그 SIG=GP26
# 공통 캐소드 RGB LED: R/G/B 각각 330옴을 거쳐 GP16/17/18
from machine import ADC, Pin
import time

ADC_REF = 3.3
BUFFER_ACID = 4.00
BUFFER_ALKALI = 10.00  # 표준용액 병에 표시된 값에 맞게 수정

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


*********온습도 센서 연결 코드
from machine import Pin, I2C

i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=100000)
print("발견된 주소:", [hex(addr) for addr in i2c.scan()])


------------------------------------------------------------------
피부온습도 측정 코드

from machine import Pin, SoftI2C
import time

ADDRESS = 0x44

MIN_TEMP = 31.0
MAX_TEMP = 32.0


def crc8(data):
    """수신 데이터 오류 검사"""
    crc = 0xFF

    for value in data:
        crc ^= value

        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x31) & 0xFF
            else:
                crc = (crc << 1) & 0xFF

    return crc


def read_sht40(i2c):
    # SHT40 고정밀 온습도 측정 시작
    i2c.writeto(ADDRESS, bytes([0xFD]))
    time.sleep_ms(20)

    data = i2c.readfrom(ADDRESS, 6)

    if (crc8(data[:2]) != data[2]
            or crc8(data[3:5]) != data[5]):
        raise ValueError("CRC error")

    raw_t = (data[0] << 8) | data[1]
    raw_h = (data[3] << 8) | data[4]

    temperature = -45 + 175 * raw_t / 65535
    humidity = -6 + 125 * raw_h / 65535
    humidity = max(0.0, min(100.0, humidity))

    return temperature, humidity


def format_reading(temperature, humidity):
    text = "측정 온도: {:.2f}℃ | 상대습도: {:.2f}%RH".format(
        temperature, humidity
    )

    if MIN_TEMP <= temperature <= MAX_TEMP:
        text += " | 이상적인 피부 온도에 도달했습니다!"

    return text


def main():
    i2c = SoftI2C(
    sda=Pin(8),
    scl=Pin(9),
    freq=50000,
    timeout=100000
)
    time.sleep_ms(100)

    while True:
        try:
            temperature, humidity = read_sht40(i2c)
            print(format_reading(temperature, humidity))

        except (OSError, ValueError) as error:
            print("측정 오류: {}".format(error))

        time.sleep_ms(1000)


if __name__ == "__main__":
    main()


------------------------------------------
웹앱 대시보드로 확인하는 피부 온습도 측정(최종 코드)
#1
WIFI_SSID = "senWiFi_Free_sky"
WIFI_PASSWORD ="sudo25sky@"

#2 main.py
"""Pico W / Pico 2 W + Grove Shield I2C0 + SHT40.
Copy main.py, wifi_config.py and dashboard.html to the Pico root.
Only local-network HTTP is used. No external packages or cloud service.
"""
from machine import Pin, SoftI2C
import network
import time
import json
import urandom
import uasyncio as asyncio
from wifi_config import WIFI_SSID, WIFI_PASSWORD

ADDRESS = 0x44
MIN_TEMP = 31.0
MAX_TEMP = 32.0
INTERVAL_MS = 1000
HISTORY_LIMIT = 20
ALERT_TEXT = "이상적인 피부 온도에 도달했습니다!"

state = {
    "session": "%08x" % urandom.getrandbits(32),
    "sequence": 0,
    "latest": None,
    "history": [],
    "min_temp": MIN_TEMP,
    "max_temp": MAX_TEMP,
    "interval_ms": INTERVAL_MS,
}


def crc8(data):
    crc = 0xFF
    for value in data:
        crc ^= value
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x31) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


async def read_sht40(i2c):
    # Same software-I2C and SHT40 command as the working sensor code.
    i2c.writeto(ADDRESS, bytes([0xFD]))
    await asyncio.sleep_ms(20)
    data = i2c.readfrom(ADDRESS, 6)
    if crc8(data[:2]) != data[2] or crc8(data[3:5]) != data[5]:
        raise ValueError("CRC error")
    raw_t = (data[0] << 8) | data[1]
    raw_h = (data[3] << 8) | data[4]
    temperature = -45 + 175 * raw_t / 65535
    humidity = max(0.0, min(100.0, -6 + 125 * raw_h / 65535))
    return temperature, humidity


def record_sample(temperature=None, humidity=None, error=None):
    state["sequence"] += 1
    ok = error is None
    # Decide on the unrounded sensor reading, including both endpoints.
    ideal = ok and MIN_TEMP <= temperature <= MAX_TEMP
    sample = {
        "id": state["sequence"],
        "ok": ok,
        "temperature": temperature if ok else None,
        "humidity": humidity if ok else None,
        "ideal": bool(ideal),
        "message": ALERT_TEXT if ideal else "",
        "error": error,
    }
    state["latest"] = sample
    state["history"].append(sample)
    if len(state["history"]) > HISTORY_LIMIT:
        state["history"].pop(0)
    return sample


async def measure_loop(i2c):
    while True:
        started = time.ticks_ms()
        try:
            temperature, humidity = await read_sht40(i2c)
            sample = record_sample(temperature, humidity)
            text = "측정 온도: {:.2f}℃ | 상대습도: {:.2f}%RH".format(
                temperature, humidity
            )
            if sample["ideal"]:
                text += " | " + sample["message"]
            print(text)
        except (OSError, ValueError) as error:
            record_sample(error=str(error))
            print("측정 오류:", error)
        elapsed = time.ticks_diff(time.ticks_ms(), started)
        await asyncio.sleep_ms(max(10, INTERVAL_MS - elapsed))


async def connect_wifi():
    if not WIFI_SSID or WIFI_SSID == "와이파이_이름":
        raise ValueError("wifi_config.py에 Wi-Fi 이름과 비밀번호를 입력하세요.")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Wi-Fi 연결 중...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(60):
            if wlan.isconnected():
                break
            await asyncio.sleep_ms(500)
    if not wlan.isconnected():
        raise OSError("Wi-Fi 연결 실패: 이름/비밀번호/2.4GHz 설정을 확인하세요.")
    return wlan


async def keep_wifi(wlan):
    last_ip = wlan.ifconfig()[0]
    while True:
        await asyncio.sleep(10)
        if not wlan.isconnected():
            print("Wi-Fi 연결 끊김. 재연결 중...")
            try:
                wlan.disconnect()
                wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            except OSError:
                pass
        else:
            new_ip = wlan.ifconfig()[0]
            if new_ip != last_ip:
                print("대시보드 주소: http://" + new_ip)
                last_ip = new_ip


async def send_response(writer, status, content_type, body):
    if isinstance(body, str):
        body = body.encode("utf-8")
    header = (
        "HTTP/1.1 {}\r\nContent-Type: {}\r\nContent-Length: {}\r\n"
        "Cache-Control: no-store\r\nConnection: close\r\n\r\n"
    ).format(status, content_type, len(body))
    writer.write(header.encode())
    writer.write(body)
    await writer.drain()


async def serve_dashboard(writer):
    # Stream the HTML in chunks instead of keeping the whole page in RAM.
    with open("dashboard.html", "rb") as page:
        writer.write(
            b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
            b"Cache-Control: no-store\r\nConnection: close\r\n\r\n"
        )
        while True:
            chunk = page.read(1024)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()


async def handle_client(reader, writer):
    try:
        line = await asyncio.wait_for(reader.readline(), 3)
        if len(line) > 1024:
            return
        parts = line.split()
        if len(parts) != 3:
            return
        method, path = parts[0], parts[1].split(b"?", 1)[0]
        total = len(line)
        for _ in range(40):
            header = await asyncio.wait_for(reader.readline(), 3)
            total += len(header)
            if total > 4096:
                return
            if header in (b"\r\n", b"\n", b""):
                break
        else:
            return
        if method != b"GET":
            await send_response(writer, "405 Method Not Allowed", "text/plain", "GET only")
        elif path in (b"/", b"/dashboard.html"):
            await serve_dashboard(writer)
        elif path == b"/api/readings":
            # Serialization is synchronous: a complete, consistent sample snapshot.
            await send_response(writer, "200 OK", "application/json; charset=utf-8", json.dumps(state))
        elif path == b"/favicon.ico":
            await send_response(writer, "204 No Content", "text/plain", b"")
        else:
            # Configuration and arbitrary files are never served.
            await send_response(writer, "404 Not Found", "text/plain", "Not found")
    except OSError as error:
        print("웹 연결 오류:", error)
    except asyncio.TimeoutError:
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass


async def main():
    # Fail early if the page was not copied to the Pico root.
    with open("dashboard.html", "rb") as page:
        page.read(1)
    i2c = SoftI2C(sda=Pin(8), scl=Pin(9), freq=50000, timeout=100000)
    await asyncio.sleep_ms(100)
    print("발견된 주소:", [hex(address) for address in i2c.scan()])
    wlan = await connect_wifi()
    server = await asyncio.start_server(handle_client, "0.0.0.0", 80)
    print("대시보드 주소: http://" + wlan.ifconfig()[0])
    print("같은 Wi-Fi에 연결한 기기의 브라우저에서 위 주소를 여세요.")
    sensor_task = asyncio.create_task(measure_loop(i2c))
    wifi_task = asyncio.create_task(keep_wifi(wlan))
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        sensor_task.cancel()
        wifi_task.cancel()
        server.close()
        await server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        asyncio.new_event_loop()
#3
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#146b59">
<title>SHT40 · 세안 전후 온습도</title>
<style>
:root{--ink:#173c35;--muted:#667c76;--line:#dce7e1;--green:#18715b;--mint:#e8f5ef;--blue:#3f78ae;--paper:#f5f8f4}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1120px;margin:auto;padding:38px 26px 28px}.top{display:flex;justify-content:space-between;align-items:center;gap:16px}.brand{font-size:12px;letter-spacing:.14em;font-weight:750;color:var(--green)}.status{border:1px solid var(--line);background:white;border-radius:30px;padding:7px 13px;font-size:12px;white-space:nowrap}.dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#a4b5ae;margin-right:7px}.status.live .dot{background:#21946e}.status.bad .dot{background:#c16a3e}
h1{font-size:clamp(25px,4vw,37px);letter-spacing:-.055em;line-height:1.3;margin:26px 0 10px}.intro{color:var(--muted);margin:0;max-width:730px}.meta{display:flex;gap:22px;flex-wrap:wrap;color:var(--muted);font-size:12px;margin:18px 0 23px}.meta b{font-weight:600;color:var(--ink)}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card{background:#fff;border:1px solid var(--line);border-radius:19px;padding:23px 26px}.card.blue{background:#f3f7fc}.card.green{background:#edf6f0}.cardhead{display:flex;justify-content:space-between;align-items:center}.label{font-size:14px;font-weight:650}.tag{font-size:10px;letter-spacing:.08em;color:var(--muted)}.reading{font-size:clamp(43px,6.5vw,64px);font-weight:650;line-height:1.2;letter-spacing:-.06em;font-variant-numeric:tabular-nums;margin-top:15px}.reading small{font-size:20px;font-weight:500;letter-spacing:0;margin-left:7px;color:var(--muted)}.blue .reading{color:var(--blue)}.cardfoot{font-size:12px;color:var(--muted);margin-top:12px}
.alert{margin-top:16px;padding:15px 20px;border-radius:13px;background:#d9efdf;color:#215c3c;font-weight:650;border:1px solid #b5dac0}.alert[hidden]{display:none}.issue{margin-top:16px;border-left:3px solid #bb754c;background:#fff2e7;padding:12px 16px;color:#7b482d;font-size:13px}.issue[hidden]{display:none}
.charts{margin-top:26px;display:grid;grid-template-columns:1fr 1fr;gap:18px}.chartcard{background:white;border:1px solid var(--line);border-radius:18px;padding:22px 18px 14px}.charthead{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:0 5px}.charthead h2{font-size:15px;margin:0;font-weight:650}.legend{display:flex;align-items:center;gap:5px;color:var(--muted);font-size:10px}.key{width:9px;height:9px;border-radius:2px;background:#d1ead7;border:1px solid #9ec9a8}.chart{display:block;width:100%;height:auto;margin-top:12px}.chart text{font-family:inherit;fill:#71857f;font-size:12px}.chart .grid{stroke:#e8eeea;stroke-width:1}.chart .axis{stroke:#cbd8d1;stroke-width:1}.chart .band{fill:#e4f1e6}.chart .bandline{stroke:#83b693;stroke-width:1;stroke-dasharray:4 4}.chartfoot{display:flex;justify-content:space-between;color:var(--muted);font-size:10px;padding:0 5px;gap:8px}.empty{fill:#7b8d87!important;font-size:16px!important}.bottom{display:flex;justify-content:space-between;gap:20px;align-items:center;margin-top:19px}.note{color:var(--muted);font-size:11px;max-width:780px;margin:0}.retry{border:1px solid #bfcec5;border-radius:9px;background:white;color:var(--ink);padding:9px 12px;font:inherit;font-size:12px;cursor:pointer;white-space:nowrap}.retry:focus-visible{outline:3px solid #79bba4;outline-offset:3px}footer{margin-top:28px;border-top:1px solid var(--line);padding-top:12px;display:flex;justify-content:space-between;color:#82928a;font-size:10px;letter-spacing:.04em}
@media(max-width:720px){main{padding:23px 16px}.cards,.charts{gap:12px}.charts{grid-template-columns:1fr}.card{padding:18px}.tag{display:none}.reading small{font-size:16px}.meta{gap:12px}.bottom{align-items:flex-start}.chartcard{padding:18px 12px 12px}}
@media(max-width:380px){.cards{grid-template-columns:1fr}.status{font-size:10px}.top{gap:8px}}
</style>
</head>
<body>
<main>
  <div class="top"><div class="brand">PICO / SHT40 MONITOR</div><div id="connection" class="status" role="status"><span class="dot"></span><span id="connectionText">연결 확인 중</span></div></div>
  <h1>세안 전후, 온습도 기록</h1>
  <p class="intro">온도와 상대습도의 변화를 실시간으로 확인하세요. 최근 20개 측정값이 막대그래프로 쌓입니다.</p>
  <div class="meta"><span>측정 간격 <b>약 1초</b></span><span>알림 기준 <b id="rangeText">31.00–32.00℃</b></span><span>마지막 수신 <b id="updated">—</b></span></div>
  <section class="cards" aria-label="현재 측정값">
    <article class="card green"><div class="cardhead"><span class="label">측정 온도</span><span class="tag">TEMPERATURE</span></div><div class="reading"><span id="temperature">—</span><small>℃</small></div><div class="cardfoot">SHT40 센서 주변의 온도</div></article>
    <article class="card blue"><div class="cardhead"><span class="label">상대습도</span><span class="tag">RELATIVE HUMIDITY</span></div><div class="reading"><span id="humidity">—</span><small>%RH</small></div><div class="cardfoot">SHT40 센서 주변 공기의 상대습도</div></article>
  </section>
  <div id="idealAlert" class="alert" role="status" aria-live="polite" hidden>이상적인 피부 온도에 도달했습니다!</div>
  <div id="issue" class="issue" role="status" hidden></div>
  <section class="charts" aria-label="최근 20개 측정값 막대그래프">
    <article class="chartcard"><div class="charthead"><h2>온도 변화 <span style="color:#81948b;font-size:12px">℃</span></h2><span class="legend"><span class="key"></span>설정 범위 31–32℃</span></div><svg id="tempChart" class="chart" viewBox="0 0 720 280" role="img" aria-label="온도 막대그래프, 측정 대기 중"></svg><div class="chartfoot"><span>가로축: 피코 측정 번호</span><span>최신 측정 →</span></div></article>
    <article class="chartcard"><div class="charthead"><h2>상대습도 변화 <span style="color:#81948b;font-size:12px">%RH</span></h2><span class="legend">최근 20개</span></div><svg id="humChart" class="chart" viewBox="0 0 720 280" role="img" aria-label="상대습도 막대그래프, 측정 대기 중"></svg><div class="chartfoot"><span>가로축: 피코 측정 번호</span><span>최신 측정 →</span></div></article>
  </section>
  <div class="bottom"><p class="note">SHT40은 주변 온도·상대습도를 측정합니다. 피부 표면 온도나 피부 수분량의 직접 측정값이 아닙니다. 31–32℃는 이 프로젝트의 설정 기준이며 피부 상태를 판정하지 않습니다. 기록은 피코 메모리에 최근 20개만 유지되며 전원을 끄면 사라집니다.</p><button id="retry" class="retry" type="button">지금 새로 받기</button></div>
  <footer><span>FACIAL CLEANSER PROJECT</span><span>같은 Wi-Fi · 피코 웹서버</span></footer>
</main>
<script>
'use strict';
const byId = id => document.getElementById(id);
let busy = false;
let timer = null;
let lastSample = '';
let lastAdvance = 0;
let hadValid = false;
const NS = 'http://www.w3.org/2000/svg';

function svgNode(tag, attrs, text) {
  const el = document.createElementNS(NS, tag);
  Object.entries(attrs || {}).forEach(([key, value]) => el.setAttribute(key, value));
  if (text !== undefined) el.textContent = text;
  return el;
}

function drawChart(id, history, key, low, high, range) {
  const svg = byId(id);
  svg.replaceChildren();
  const x0 = 48, y0 = 17, width = 656, height = 214;
  const y = value => y0 + (high - value) * height / (high - low);
  const baseline = y(0);
  if (range) {
    svg.append(svgNode('rect', {x:x0, y:y(range[1]), width:width, height:y(range[0])-y(range[1]), class:'band'}));
    range.forEach(value => svg.append(svgNode('line', {x1:x0, x2:x0+width, y1:y(value), y2:y(value), class:'bandline'})));
  }
  for (let i = 0; i <= 5; i++) {
    const value = low + (high - low) * i / 5;
    svg.append(svgNode('line', {x1:x0,x2:x0+width,y1:y(value),y2:y(value),class:'grid'}));
    svg.append(svgNode('text', {x:x0-9,y:y(value)+4,'text-anchor':'end'}, Number(value.toFixed(1))));
  }
  svg.append(svgNode('line', {x1:x0,x2:x0+width,y1:baseline,y2:baseline,class:'axis'}));
  const slot = width / 20;
  history.slice(-20).forEach((sample, index) => {
    const x = x0 + index * slot + 4;
    if (sample.ok && Number.isFinite(sample[key])) {
      const value = sample[key];
      const bar = svgNode('rect', {x:x,y:Math.min(y(value),baseline),width:slot-8,height:Math.max(1,Math.abs(baseline-y(value))),rx:3,fill:key==='temperature'?(sample.ideal?'#2c9364':'#79a995'):'#6696c0'});
      bar.append(svgNode('title', {}, '#' + sample.id + ': ' + value.toFixed(2) + (key==='temperature'?'℃':'%RH')));
      svg.append(bar);
    } else {
      svg.append(svgNode('text', {x:x+slot/2-4,y:y0+height-5,'text-anchor':'middle',fill:'#a66845'}, '×'));
    }
    if (index===0 || index===history.length-1 || (index+1)%5===0) {
      svg.append(svgNode('text', {x:x+slot/2-4,y:255,'text-anchor':'middle'}, '#' + sample.id));
    }
  });
  if (!history.length) svg.append(svgNode('text', {x:376,y:124,'text-anchor':'middle',class:'empty'}, '첫 측정값을 기다리고 있어요'));
  svg.setAttribute('aria-label', (key==='temperature'?'온도':'상대습도') + ' 막대그래프, 최근 ' + history.length + '개 측정. 세로축 ' + low + '에서 ' + high + '.');
}

function connection(text, kind) {
  byId('connectionText').textContent = text;
  byId('connection').className = 'status ' + kind;
}

function unavailable(message, label) {
  byId('temperature').textContent = '—';
  byId('humidity').textContent = '—';
  byId('idealAlert').hidden = true;
  byId('issue').textContent = message;
  byId('issue').hidden = false;
  connection(label, 'bad');
}

function render(data) {
  const history = data.history.slice(-20);
  const temps = history.filter(s => s.ok).map(s => s.temperature);
  const low = Math.min(0, ...temps.map(v => Math.floor(v/10)*10));
  const high = Math.max(50, ...temps.map(v => Math.ceil(v/10)*10));
  drawChart('tempChart', history, 'temperature', low, high, [data.min_temp,data.max_temp]);
  drawChart('humChart', history, 'humidity', 0, 100, null);
  byId('rangeText').textContent = data.min_temp.toFixed(2)+'–'+data.max_temp.toFixed(2)+'℃';
  byId('updated').textContent = new Date().toLocaleTimeString('ko-KR',{hour12:false});
  const sample = data.latest;
  if (!sample) {
    unavailable('센서의 첫 측정값을 기다리고 있습니다.', '측정 대기');
    return;
  }
  const token = data.session + ':' + sample.id;
  if (token !== lastSample) {
    lastSample = token;
    lastAdvance = Date.now();
  }
  if (Date.now() - lastAdvance > 6000) {
    unavailable('새 측정값이 도착하지 않습니다. 피코의 실행 상태를 확인하세요.', '측정 지연');
    return;
  }
  if (!sample.ok) {
    unavailable('센서 측정 오류: '+(sample.error || '알 수 없는 오류')+'. 케이블과 Thonny 셸을 확인하세요.', '센서 오류');
    return;
  }
  if (!Number.isFinite(sample.temperature) || !Number.isFinite(sample.humidity)) throw new Error('잘못된 측정값');
  byId('temperature').textContent = sample.temperature.toFixed(2);
  byId('humidity').textContent = sample.humidity.toFixed(2);
  byId('idealAlert').hidden = !sample.ideal;
  byId('idealAlert').textContent = '이상적인 피부 온도에 도달했습니다!';
  byId('issue').hidden = true;
  connection('실시간 측정 중', 'live');
}

async function update() {
  if (busy) return;
  busy = true;
  clearTimeout(timer);
  const controller = new AbortController();
  const deadline = setTimeout(() => controller.abort(), 3000);
  try {
    const response = await fetch('/api/readings', {cache:'no-store',signal:controller.signal});
    if (!response.ok) throw new Error('HTTP '+response.status);
    const data = await response.json();
    if (!Array.isArray(data.history) || typeof data.session !== 'string') throw new Error('잘못된 응답');
    render(data);
    hadValid = true;
  } catch (error) {
    unavailable(hadValid?'피코와 연결이 끊겼습니다. 그래프는 이전 기록이며, 연결되면 자동 갱신됩니다.':'피코에 연결할 수 없습니다. 피코가 출력한 http:// 주소로 접속했는지, 같은 Wi-Fi인지 확인하세요.', '연결 끊김');
  } finally {
    clearTimeout(deadline);
    busy = false;
    timer = setTimeout(update, 1000);
  }
}
byId('retry').addEventListener('click', update);
drawChart('tempChart', [], 'temperature', 0, 50, [31,32]);
drawChart('humChart', [], 'humidity', 0, 100, null);
update();
</script>
</body>
</html>
