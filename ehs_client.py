'''
Stream data from a TCP server providing datafeed of ADS-B messages
'''

import os
import socket
import time
import datetime
import csv
import pyModeS as pms

dataroot = os.path.dirname(os.path.realpath(__file__)) + "/data/"

class Client():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/tmp/adsb-stdout.log'
        self.stderr_path = '/tmp/adsb-error.log'
        self.pidfile_path = '/tmp/sil-ehs-client.pid'
        self.pidfile_timeout = 5

    def connect(self, host, port):
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(10)    # 10 second timeout
                s.connect((host, port))
                print "Server %s connected" % host
                print "collecting EHS messages..."
                return s
            except socket.error as err:
                print "Socket connection error: %s. reconnecting..." % err
                time.sleep(3)

    def read_mode_s(self, data):
        '''
        <esc> "1" : 6 byte MLAT timestamp, 1 byte signal level,
            2 byte Mode-AC
        <esc> "2" : 6 byte MLAT timestamp, 1 byte signal level,
            7 byte Mode-S short frame
        <esc> "3" : 6 byte MLAT timestamp, 1 byte signal level,
            14 byte Mode-S long frame
        <esc> "4" : 6 byte MLAT timestamp, status data, DIP switch
            configuration settings (not on Mode-S Beast classic)
        <esc><esc>: true 0x1a
        <esc> is 0x1a, and "1", "2" and "3" are 0x31, 0x32 and 0x33

        timestamp:
        wiki.modesbeast.com/Radarcape:Firmware_Versions#The_GPS_timestamp
        '''

        # split raw data into chunks
        chunks = []
        separator = 0x1a
        piece = []
        for d in data:
            if d == separator:
                # shortest msgs are 11 chars
                if len(piece) > 10:
                    chunks.append(piece)
                piece = []
            piece.append(d)

        # extract messages
        messages = []
        for cnk in chunks:
            msgtype = cnk[1]

            # Mode-S Short Message, 7 byte
            if msgtype == 0x32:
                msg = ''.join('%02X' % i for i in cnk[9:16])

            # Mode-S Short Message, 14 byte
            elif msgtype == 0x33:
                msg = ''.join('%02X' % i for i in cnk[9:23])

            # Other message tupe
            else:
                continue

            ts = time.time()

            messages.append([msg, ts])
        return messages

    def run(self):

        host = '131.180.117.39'
        port = 30334

        # host = '127.0.0.1'
        # port = 30334

        tcp_buffer = ''

        sock = self.connect(host, port)

        while True:
            try:
                tcp_buffer += sock.recv(1024)
                # print ''.join(x.encode('hex') for x in tcp_buffer)

                # process buffer when it is longer enough
                if len(tcp_buffer) < 2048:
                    continue

                # process the buffer until the last divider <esc> 0x1a
                # then, reset the buffer with the remainder
                bfdata = [ord(i) for i in tcp_buffer]
                n = (len(bfdata) - 1) - bfdata[::-1].index(0x1a)
                data = bfdata[:n-1]
                tcp_buffer = tcp_buffer[n:]

                messages = self.read_mode_s(data)

                if not messages:
                    continue

                # get the current date file
                today = str(datetime.datetime.now().strftime("%Y%m%d"))
                csvfile = dataroot + 'EHS_RAW_%s.csv' % today

                with open(csvfile, 'a') as f:
                    writer = csv.writer(f)
                    for msg, ts in messages:
                        if len(msg) < 28:
                            continue

                        df = pms.df(msg)

                        if df not in [20, 21]:
                            continue

                        addr = pms.ehs.icao(msg)

                        line = ['%.6f'%ts, addr, msg]

                        writer.writerow(line)

                time.sleep(0.001)
            except Exception, e:
                print "Unexpected Error:", e
                pass


if __name__ == '__main__':
    client = Client()
    client.run()
