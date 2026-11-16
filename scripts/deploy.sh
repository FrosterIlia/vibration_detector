#!/bin/bash
set -e                          # stop if any step fails
PI=pi@octopi.local
rsync -av --delete --exclude '__pycache__' klipper_module/ $PI:~/fabric-printer/klipper_module/
ssh -t $PI 'sudo systemctl restart klipper'
ssh $PI 'tail -f /tmp/klippy.log'