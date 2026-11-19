set -e                          # stop if any step fails
PI=pi@octopi.local
rsync -av pi@octopi.local:~/resonance_data/ resonance_data/