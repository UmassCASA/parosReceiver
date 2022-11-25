import pika
import json
import os
import argparse
from datetime import datetime
from pathlib import Path
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from scipy.signal import butter, lfilter, detrend, welch, spectrogram
from scipy.fft import fft, fftfreq
import numpy as np


# var to store historical data
fft_points = 128
fft_shift = 8
baro_data = {}
fs = 20

def fft_calc(json_data):
    # add point to baro list

    global fft_points
    global fft_shift
    global baro_data
    global fs
    
    dict_indx = json_data["sensor_id"]
    if dict_indx not in baro_data:
        baro_data[dict_indx] = []
    
    baro_data[dict_indx].append((json_data["value"], json_data["dev_timestamp"]))

    if len(baro_data[dict_indx]) >= fft_points + fft_shift:
        # remove the first 8 data points
        baro_data[dict_indx] = baro_data[dict_indx][fft_shift:]

        # remove dc offset
        cur_baro_data = np.array(list(zip(*baro_data[dict_indx]))[0], dtype="f")
        dc_value = np.mean(cur_baro_data)
        cur_baro_data = np.subtract(cur_baro_data, dc_value)

        cur_baro_fft = np.log10(abs(fft(cur_baro_data)))

        p_fft = Point(json_data["module_id"]) \
                .tag("dtype", "barometer") \
                .tag("sensor_id", json_data["sensor_id"]) \
                .time(baro_data[dict_indx][0][1])

        nyquist_points = int(fft_points / 2) - 1
        bin_size = fs / fft_points
        for i in range(1, nyquist_points):
            cur_freq = bin_size * i
            p_fft.field(str(cur_freq) + " Hz", cur_baro_fft[i])

        return p_fft

    return None



def main():
    parser = argparse.ArgumentParser(description='Responsible for managing the incoming rabbitmq queue')
    parser.add_argument("-i", "--influxdb",
                        help="Send data to influxdb",
                        action="store_true")
    parser.add_argument("-l", "--log",
                        help="Send data to csv output",
                        action="store_true")
    parser.add_argument("-f", "--fft", help="Also calculate and write the FFT to log", action="store_true")

    # init rmq connection
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='parosLogger')

    # init influxdb connection
    # get API key
    with open("INFLUX_APIKEY", mode='r') as f:
        api_key = f.read().strip()

    bucket = "paros"
    bucket_fft = "paros_fft"
    client = InfluxDBClient(url="http://localhost:8086", token=api_key, org="paros")
    write_api = client.write_api(write_options=SYNCHRONOUS)

    def callback(ch, method, properties, body):
        output_filename = datetime.utcnow().strftime("%Y-%m-%d-%H") + ".csv"

        cur_line = body.decode("utf-8")
        # remove unicode characters
        cur_line = cur_line.encode("ascii", "ignore")
        cur_line = cur_line.decode()

        json_data = json.loads(cur_line)

        cur_day = datetime.utcnow().strftime("%Y-%m-%d")
        data_folder = "recorded_data"

        module_folder = os.path.join(data_folder, json_data["module_id"])

        if json_data["sensor_id"] == "anemometer":
            output_folder = os.path.join(module_folder, "anemometer", cur_day)
            output_file = os.path.join(output_folder, "wind_" + output_filename)
            field_list = ["module_id", "sensor_id", "timestamp", "raw_adc", "voltage", "value"]

            # create influxdb point
            p = Point(json_data["module_id"]) \
                .tag("dtype", "anemometer") \
                .tag("sensor_id", json_data["sensor_id"]) \
                .time(json_data["timestamp"]) \
                .field("value", float(json_data["value"]))
        else:
            output_folder = os.path.join(module_folder, "baro", cur_day)
            output_file = os.path.join(output_folder, "baro_" + output_filename)
            field_list = ["module_id", "sensor_id", "timestamp", "dev_timestamp", "value"]

            # create influxdb point
            p = Point(json_data["module_id"]) \
                .tag("dtype", "barometer") \
                .tag("sensor_id", json_data["sensor_id"]) \
                .time(json_data["timestamp"]) \
                .field("value", float(json_data["value"]))

            fft_point = fft_calc(json_data)
            if fft_point is not None:
                write_api.write(bucket=bucket_fft, record=fft_point)

        # create folder if it doesn't exist
        Path(output_folder).mkdir(parents=True, exist_ok=True)

        log_list = [ str(json_data[x]) for x in field_list ]
        log_line = ",".join(log_list)

        # write to output
        with open(output_file, 'a') as f:
            f.write(log_line)
            f.write('\n')

        # add point to influxdb
        write_api.write(bucket=bucket, record=p)


    channel.basic_consume(queue='parosLogger', on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
