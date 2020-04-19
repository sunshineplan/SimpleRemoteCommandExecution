#!/usr/bin/python3
# -*- coding: utf-8 -*-

from datetime import datetime
from email.message import EmailMessage
from secrets import token_bytes
from smtplib import SMTP
from subprocess import Popen, TimeoutExpired

from flask import Flask, Response, request

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

PATH = '/path/'

SUBSCRIBE = {
    'sender': '',  # sender mail address
    'smtp_server': '',  # sender smtp server
    'smtp_server_port': 587,  # sender smtp server port
    'password': '',  # sender auth password
    'subscriber': ''  # subscriber mail address
}


def emailNotify(user, ip, cmd):
    try:
        from metadata import metadata
        SUBSCRIBE = metadata('srce_subscribe', ERROR_IF_NONE=True)
    except:
        pass
    msg = EmailMessage()
    msg['Subject'] = f"SRCE Notification - {datetime.now().strftime('%Y%m%d %H:%M:%S')}"
    msg['From'] = SUBSCRIBE['sender']
    msg['To'] = SUBSCRIBE['subscriber']
    if isinstance(cmd, list):
        cmd = ' '.join(cmd)
    msg.set_content(
        f"{datetime.now().strftime('%Y/%m/%d-%H:%M:%S')}\nUser: {user}\nIP: {ip}\n\nCommand: {cmd}")
    with SMTP(SUBSCRIBE['smtp_server'], SUBSCRIBE['smtp_server_port']) as s:
        s.starttls()
        s.login(SUBSCRIBE['sender'], SUBSCRIBE['password'])
        s.send_message(msg)


app = Flask(__name__)
app.config['SECRET_KEY'] = token_bytes(16)
auth = HTTPDigestAuth()


@auth.get_password
def get_pw(username):
    try:
        from metadata import metadata
        ALLOW_USERS = metadata('srce_user', ERROR_IF_NONE=True)
    except:
        pass
    if username in ALLOW_USERS:
        return ALLOW_USERS[username]
    return None


@app.route('/')
@app.route('/<path:unknow>')
def main(unknow=None):
    return '', 403


@app.route('/bash/<string:cmd>')
@app.route('/bash/<string:cmd>/')
@app.route('/bash/<string:cmd>/<string:arg>')
@auth.login_required
def bash(cmd, arg=None):
    try:
        from metadata import metadata
        ALLOW_COMMAND = metadata('srce_command', ERROR_IF_NONE=True)
        PATH = metadata('srce_path', ERROR_IF_NONE=True)
    except:
        pass
    if cmd not in ALLOW_COMMAND.keys():
        return '', 403
    if arg:
        if arg not in ALLOW_COMMAND[cmd]:
            return '', 403
        command = [f'{PATH}{cmd}', arg]
    else:
        command = f'{PATH}{cmd}'
    emailNotify(auth.username, request.remote_addr, command)
    proc = Popen(command, stdout=-1, stderr=-1)
    try:
        outs, errs = proc.communicate(timeout=30)
    except TimeoutExpired:
        return 'Process still running.'
    return Response(f'Output:\n{outs.decode()}\n\nError:\n{errs.decode()}', mimetype='text/plain')


if __name__ == '__main__':
    app.run()
