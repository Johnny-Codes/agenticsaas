Working on my Ph.D.

## Requirements
- Ollama
- Docker

## Installation

1. Clone the repository
2. Start Docker Desktop
3. Open a terminal and go to the directory
4. `docker compose build`
5. Make sure Ollama is running
6. `docker compose up`
7. Frontend on `localhost:3000`, backend on `localhost:8000` and docs at `localhost:8000/docs`

## Ollama

Current models being used from Ollama are:
- llama3.2:latest
- phi3:14b

1. Install Ollama
2. In a terminal run the following command for each model listed above: `ollama pull <model>`