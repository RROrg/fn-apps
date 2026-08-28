# Attention:
# 1. This script is from AI, please do more research for BSD installation script before use it.
# 2. Please use DVD iso file for test (e.g. FreeBSD-15.0-RELEASE-amd64-dvd1.iso), do not use disc or bootonly iso file.
# 


DISTRIBUTIONS="kernel.txz base.txz"
PARTITIONS=nda0


# ========== 2. Post script (run after chroot ) ==========
#!/bin/sh

sysrc hostname="fbsd-auto-node"
sysrc ifconfig_DEFAULT="DHCP"


sysrc sshd_enable="YES"
sysrc dumpdev="AUTO"


echo "PermitRootLogin yes" >> /etc/ssh/sshd_config

echo "123456" | pw usermod root -h 0

env ASSUME_ALWAYS_YES=YES pkg bootstrap -f
env ASSUME_ALWAYS_YES=YES pkg install -y curl tmux sudo


reboot

