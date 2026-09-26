FROM eclipse-mosquitto:2

COPY mosquitto.conf /mosquitto/config/mosquitto.conf

RUN mosquitto_passwd -b -c /mosquitto/config/passwordfile ota_server my_password \
    && chown mosquitto:mosquitto /mosquitto/config/passwordfile \
    && chmod 600 /mosquitto/config/passwordfile

EXPOSE 1883

CMD ["mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]