# Alumno: Chengxun Wu
FROM ubuntu:20.04

RUN apt-get update && \
    apt-get install -y software-properties-common && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /

COPY serverFileManager /serverFileManager
COPY FileManagerDir /FileManagerDir

RUN chmod +x /serverFileManager

EXPOSE 32001

ENTRYPOINT ["/serverFileManager"]
