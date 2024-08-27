FROM

LABEL version="1.0.0" maintainer="镜像名称"

WORKDIR /proj

COPY . .

ENV PYTHONPATH .
ENV JAVA_TOOL_OPTIONS="-Dfile.encoding=UTF8 -Dsun.jnu.encoding=UTF8"
ENV LC_ALL=C.UTF-8

RUN pip install -r requirements.txt && \
    python3 utils/read_files_tools/case_automatic_control.py

CMD ["python3", "./run.py","config.yaml"]
