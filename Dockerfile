FROM centos:7

RUN yum install -y unzip vim curl
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install
RUN curl "https://files.pythonhosted.org/packages/4e/5f/528232275f6509b1fff703c9280e58951a81abe24640905de621c9f81839/pip-20.2.3-py2.py3-none-any.whl" \
    -o /pip-20.2.2-py2.py3-none-any.whl
RUN python /pip-20.2.2-py2.py3-none-any.whl/pip install --no-index pip-20.2.2-py2.py3-none-any.whl \
    && rm /pip-20.2.2-py2.py3-none-any.whl 
RUN pip install -U setuptools
RUN pip install boto3 yum

RUN rm -f /etc/yum.repos.d/*
COPY s3.repo /etc/yum.repos.d/
COPY s3.conf /etc/yum/pluginconf.d/
COPY s3.py /usr/lib/yum-plugins

ENTRYPOINT ["/bin/bash"]
