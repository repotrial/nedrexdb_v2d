FROM andimajore/mamba_mantic:latest
RUN apt-get update && apt-get upgrade -y

RUN apt-get update \
    && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    cron

RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -

RUN add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   lunar \
   stable"

RUN apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io

RUN apt-get update && apt-get install -y unzip
RUN mamba install python=3.10
RUN mamba upgrade pip tqdm cryptography

WORKDIR /data/nedrex_files/
RUN mkdir -p nedrex_api/static
RUN mkdir -p nedrex_api/data
RUN mkdir -p nedrex_data/downloads

WORKDIR /app/nedrexdb
COPY cron/cron.dev /etc/cron.d/cron-nedrex
RUN chmod 0644 /etc/cron.d/cron-nedrex
RUN crontab /etc/cron.d/cron-nedrex
RUn touch /var/log/nedrexdb.log

COPY . ./
RUN rm -rf cron
RUN pip install .

CMD cron && bash build.sh >> /var/log/nedrexdb.log 2>&1 & tail -f /var/log/nedrexdb.log

