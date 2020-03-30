#!/usr/bin/python3
# -*- coding: utf-8 -*-

from datetime import datetime
from email.message import EmailMessage
from secrets import token_bytes
from smtplib import SMTP
from subprocess import Popen, TimeoutExpired

from flask import Flask, Response, abort, request

from flask_httpauth import HTTPDigestAuth

ALLOW_COMMAND = {
    'command1': ['arg1', 'arg2', 'arg3'],
    'command2': ['arg1'],
    'command3': []
}
ALLOW_USERS = {
    'user1': 'password',
    'user2': 'password'
}
DIR = '/dir/'

SENDER = ''  # sender mail address
SMTP_SERVER = ''  # sender smtp server
SMTP_SERVER_PORT = 587  # sender smtp server port
PWD = ''  # sender auth password
SUBSCRIBER = ''  # subscriber mail address


def emailNotify(user, ip, cmd):
    msg = EmailMessage()
    msg['Subject'] = f"Notification - {datetime.now().strftime('%Y%m%d %H:%M:%S')}"
    msg['From'] = SENDER
    msg['To'] = SUBSCRIBER
    if isinstance(cmd, list):
        cmd = ' '.join(cmd)
    msg.set_content(
        f"{datetime.now().strftime('%Y/%m/%d-%H:%M:%S')}\nUser: {user}\nIP: {ip}\n\nCommand: {cmd}")
    with SMTP(SMTP_SERVER, SMTP_SERVER_PORT) as s:
        s.starttls()
        s.login(SENDER, PWD)
        s.send_message(msg)


app = Flask(__name__)
app.config['SECRET_KEY'] = token_bytes(16)
auth = HTTPDigestAuth()


@auth.get_password
def get_pw(username):
    if username in ALLOW_USERS:
        return ALLOW_USERS[username]
    return None


@app.route('/')
@app.route('/<path:unknow>')
def main(unknow=None):
    abort(403)


@app.route('/bash/<string:cmd>')
@app.route('/bash/<string:cmd>/')
@app.route('/bash/<string:cmd>/<string:arg>')
@auth.login_required
def bash(cmd, arg=None):
    if cmd not in ALLOW_COMMAND.keys():
        abort(403)
    if arg:
        if arg not in ALLOW_COMMAND[cmd]:
            abort(403)
        command = [f'{DIR}{cmd}', arg]
    else:
        command = f'{DIR}{cmd}'
    emailNotify(auth.username, request.remote_addr, command)
    proc = Popen(command, stdout=-1, stderr=-1)
    try:
        outs, errs = proc.communicate(timeout=30)
    except TimeoutExpired:
        return 'Process still running.'
    return Response(f'Output:\n{outs.decode()}\n\nError:\n{errs.decode()}', mimetype='text/plain')


if __name__ == '__main__':
    app.run()
