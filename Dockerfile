FROM mambaorg/micromamba:0.15.3
USER root
RUN mkdir /opt/routeplanning
RUN chmod -R 777 /opt/routeplanning
WORKDIR /opt/routeplanning
USER micromamba
COPY environment.yml environment.yml
RUN micromamba install -y -n base -f environment.yml && \
   micromamba clean --all --yes
COPY run.sh run.sh
COPY app app
USER root
RUN chmod a+x run.sh
EXPOSE 80
CMD ["./run.sh"]