FROM ollama/ollama:latest
RUN ollama serve & sp=$! && \
    until ollama list >/dev/null 2>&1; do sleep 1; done && \
    ollama pull llama3.1:8b && kill $sp
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
