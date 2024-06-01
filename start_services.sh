#!/bin/bash

# Start Zap
zap.sh -daemon -host 0.0.0.0 -port 8080 -config "api.addrs.addr.name=.*" -config api.addrs.addr.regex=true -config api.key=your_api_key &

# Start the application
python3 main.py

 # Keep both processes running in the foreground to keep the Docker container open
wait -n