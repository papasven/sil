import sys
import os
import ehs_client
from daemon.runner import DaemonRunner

f = open(os.devnull, 'w')
sys.stdout = f

app = ehs_client.Client()
daemon_runner = DaemonRunner(app)
daemon_runner.do_action()
