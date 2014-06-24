#!/bin/bash
openssl req -batch -x509 -nodes -days 365 \
    -subj '${ssl_subject}' \
    -newkey rsa:1024 \
    -keyout ${prefix}/etc/nginx/phoenix.cert \
    -out ${prefix}/etc/nginx/phoenix.cert