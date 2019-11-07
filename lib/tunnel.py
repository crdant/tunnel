import os
import sys
import subprocess
import re
import tempfile
import logging
import hashlib

logging.basicConfig()
LOGGER = logging.getLogger(__name__)

class TunnelManager:

  def __init__(self, host, port = 8080, log_level = None):
    self.host = host
    self.port = port
    self.tempdir = "/tmp" # tempfile.gettempdir()
    self.socket = os.path.join(self.tempdir, '{}.sock'.format(self.host))
    if log_level is not None:
      LOGGER.setLevel(log_level)

  def establish(self,user,credential):
    ssh_cmd = [
        'ssh',
        '-q',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ServerAliveInterval=60',
        '-M',
        '-S', self.socket,
        '-D', str(self.port),
        '-NCf',
        '-l', user,
        self.host
    ]

    private_key = os.path.join(self.tempdir, "{}.pem".format(self.host))
    if self.__is_key(credential):
      private_key_fd = os.open(private_key, os.O_CREAT | os.O_WRONLY, 0o600)
      with os.fdopen(private_key_fd, 'w') as private_key_file:
        private_key_file.write("{}\n".format(credential))
      ssh_cmd += [ '-i', private_key ]
    else:
      ssh_cmd = [ 'sshpass', '-p', credential ] + ssh_cmd

    LOGGER.debug(ssh_cmd)
    try:
      subprocess.check_call(ssh_cmd)
      self.proxy_url = 'socks5://localhost:{}'.format(self.port)
    except subprocess.CalledProcessError:
      LOGGER.fatal('Unable to establish SSH tunnel')
      sys.exit(1)
    finally:
      if os.path.exists(private_key):
        os.remove(private_key)

  def teardown(self):
    ssh_cmd = [
        'ssh',
        '-S', self.socket,
        '-O', 'exit',
        self.host
    ]
    LOGGER.debug(ssh_cmd)
    try:
        subprocess.check_call(ssh_cmd)
        self.proxy_url = None
    except subprocess.CalledProcessError:
        LOGGER.fatal('Unable to teardown SSH tunnel')
        sys.exit(1)

  def __is_key(self,credential):
      checker = re.compile("-----BEGIN.*PRIVATE KEY-----")
      return checker.match(credential)
