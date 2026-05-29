```
ollama_gotty/
├── Dockerfile             # pygotty/bash base + Ollama binary
├── entrypoint.sh          # starts Ollama in background, hands off to GoTTY
├── docker-compose.yml     # local network binding, named volume for models
├── .env.example           # port, host, model volume path
├── .gitignore             # excludes .env
└── README.md              # usage, what's different from pygotty/bash
```
