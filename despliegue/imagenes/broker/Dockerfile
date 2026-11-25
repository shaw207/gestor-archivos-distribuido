# Alumno: Chengxun Wu
FROM ubuntu:20.04

RUN apt-get update && \
    apt-get install -y software-properties-common && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /

COPY brokerFileManager /brokerFileManager

RUN chmod +x /brokerFileManager

EXPOSE 32002

CMD ["/brokerFileManager"]
