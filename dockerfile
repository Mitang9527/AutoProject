FROM

LABEL version="1.0.0" maintainer="MiTang"

WORKDIR /home/lzroot/Code

COPY . .

ENV PYTHONPATH .
ENV JAVA_TOOL_OPTIONS="-Dfile.encoding=UTF8 -Dsun.jnu.encoding=UTF8"
ENV LC_ALL=C.UTF-8

RUN pip install -r requirements.txt

CMD ["python3", "./run.py","config.yaml"]
