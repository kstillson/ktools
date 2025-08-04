openssl req -x509 -newkey rsa:2048 -keyout key.pem -out server-cn=localhost.pem -days 999 -nodes -subj "/CN=localhost" && \
  cat key.pem >> server-cn=localhost.pem && \
  rm key.pem 
