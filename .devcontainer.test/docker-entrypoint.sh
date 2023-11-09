#!/bin/sh

cd Cloud.Stream.Client 
python3 python/src/client/client.py $CCS_PARAMS & sleep 10
kill $!
cat streamclient.log
