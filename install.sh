#! /bin/bash

installSoftware() {
    apt -qq -y install python3-flask uwsgi-plugin-python3 nginx
}

installSRCE() {
    mkdir -p /var/log/uwsgi
    curl -Lo- https://github.com/sunshineplan/SimpleRemoteCommandExecution/archive/v1.0.tar.gz | tar zxC /var/www
    mv /var/www/SimpleRemoteCommandExecution* /var/www/srce
}

setupsystemd() {
    cp -s /var/www/srce/srce.service /etc/systemd/system
    systemctl enable srce
    service srce start
}

writeLogrotateScrip() {
    if [ ! -f '/etc/logrotate.d/uwsgi' ]; then
	cat >/etc/logrotate.d/uwsgi <<-EOF
		/var/log/uwsgi/*.log {
		    copytruncate
		    rotate 12
		    compress
		    delaycompress
		    missingok
		    notifempty
		}
		EOF
    fi
}

setupNGINX() {
    cp -s /var/www/srce/SRCE.conf /etc/nginx/conf.d
    sed -i "s/\$domain/$domain/" /var/www/srce/SRCE.conf
    service nginx reload
}

main() {
    read -p 'Please enter domain:' domain
    installSoftware
    installSRCE
    setupsystemd
    writeLogrotateScrip
    setupNGINX
}

main
