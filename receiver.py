import pika
import json
import time
from pathlib import Path

def main():

    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='parosLogger')

    def callback(ch, method, properties, body):
        output_filename = time.strftime("%Y-%m-%d-%H") + ".csv"

        cur_line = body.decode("utf-8")
        # remove unicode characters
        cur_line = cur_line.encode("ascii", "ignore")
        cur_line = cur_line.decode()

        json_data = json.loads(cur_line)

        cur_day = time.strftime("%Y-%m-%d")
        data_folder = "recorded_data"

        if json_data["sensor_id"] == "anemometer":
            output_folder = data_folder + "/anemometer/" + cur_day
            output_file = output_folder + "/wind_" + output_filename
            field_list = ["module_id", "sensor_id", "timestamp", "raw_adc", "voltage", "value"]
        else:
            output_folder = data_folder + "/baro/" + cur_day
            output_file = output_folder + "/baro_" + output_filename
            field_list = ["module_id", "sensor_id", "timestamp", "dev_timestamp", "value"]

        # create folder if it doesn't exist
        Path(output_folder).mkdir(parents=True, exist_ok=True)

        log_list = [ str(json_data[x]) for x in field_list ]
        log_line = ",".join(log_list)

        # write to output
        with open(output_file, 'a') as f:
            f.write(log_line)
            f.write('\n')

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
