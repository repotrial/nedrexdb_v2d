FROM andimajore/miniconda3_mantic:latest
RUN apt-get update && apt-get dist-upgrade -y

RUN apt-get update \
    && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common

RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -

RUN add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   lunar \
   stable"

RUN apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io

RUN apt-get update && apt-get install -y unzip
RUN conda install python=3.10
RUN pip install --upgrade pip

WORKDIR /data/nedrex_files/
RUN mkdir -p nedrex_api/static
RUN mkdir -p nedrex_api/data
RUN mkdir -p nedrex_data/downloads

WORKDIR /app/nedrexdb
COPY . ./

RUN pip install .
RUN pip install rdkit

