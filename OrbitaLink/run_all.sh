#!/bin/bash

mkdir -p logs

echo "Starting main server on port 5000..."
nohup python server.py > logs/main_server.log 2>&1 &
sleep 3

echo "Starting Server 1 on port 5001..."
nohup env SERVER_NAME='Server 1' python server1.py > logs/server1.log 2>&1 &
echo "Starting Server 2 on port 5002..."
nohup env SERVER_NAME='Server 2' python server2.py > logs/server2.log 2>&1 &
# echo "Starting Server 3 on port 5003..."
# nohup env SERVER_NAME='Server 3' python server3.py > logs/server3.log 2>&1 &
sleep 3

echo "Starting Client A..."
nohup env CLIENT_NAME='Client A' python client1.py > logs/client1.log 2>&1 &
echo "Starting Client B..."
nohup env CLIENT_NAME='Client B' python client2.py > logs/client2.log 2>&1 &
# echo "Starting Client C..."
# nohup env CLIENT_NAME='Client C' python client3.py > logs/client3.log 2>&1 &

echo "✅ All servers and clients launched in background. Check 'logs/' for output."
