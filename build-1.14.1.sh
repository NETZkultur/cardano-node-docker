#!/bin/bash

docker build --build-arg CARDANO_BRANCH=tags/1.14.1 -t arrakis/cardano-node:1.14.1 .
