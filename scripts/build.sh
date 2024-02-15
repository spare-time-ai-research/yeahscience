#!/bin/bash

docker build --target app -t yeahscience-app .
docker build --target web-server -t yeahscience-web-server .
