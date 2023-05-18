#!/bin/bash
cd ..
ls | grep ^[0-9][0-9]: | xargs -d'\n' rm
ls | grep ^MISSED* | xargs -d'\n' rm
ls | grep ^URL_LIST* | xargs -d'\n' rm