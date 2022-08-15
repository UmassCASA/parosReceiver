import pika
import json
import time

def main():
    output_file = "recorded_data/" + time.strftime("%Y%m%d-%H%M") + ".csv"

    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='parosLogger')

    def callback(ch, method, properties, body):
        cur_line = body.decode("utf-8")
        # remove unicode characters
        cur_line = cur_line.encode("ascii", "ignore")
        cur_line = cur_line.decode()

        # write to output
        with open(output_file, 'a') as f:
            f.write(cur_line)
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
