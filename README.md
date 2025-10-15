# ☁️ AWS-S3-Local-Dev-Sandbox

[![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-black?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![Boto3](https://img.shields.io/badge/Boto3-FF9900?style=for-the-badge&logo=amazon-aws)](https://aws.amazon.com/sdk-for-python/)
[![LocalStack](https://img.shields.io/badge/LocalStack-2c8e37?style=for-the-badge&logo=localstack)](https://www.localstack.cloud/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker)](https://www.docker.com/)

## 📜 Sobre

Ambiente local para simular **AWS S3** com **LocalStack** no **Docker**. Usa **Flask** + **Boto3** para desenvolvimento sem custos AWS.

### 🎯 Objetivos
- 🚀 Dev local zero custo
- 🧪 Testes S3
- 📚 Boto3 + LocalStack
- ⚡ Interface web

## ✨ Funcionalidades
- 📤 Upload arquivos
- 📋 Listagem objetos
- ⬇️ Download
- 🪣 Bucket auto-criado

## 🛠️ Pré-requisitos
- Docker Desktop
- Python 3.8+
- Git
- WSL2 (recomendado)

## 🚀 Setup

### 1. Clonar
```bash
git clone https://github.com/Lucas-Amaral-D/AWS-S3-Local-Dev-Sandbox.git
cd AWS-S3-Local-Dev-Sandbox
```

### 2. Python
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. LocalStack
```
docker compose up -d
sleep 30
```

### 4. App
```
python app.py
```

### 5. Acessar
```
[http](http://localhost:5000)
```

## 🧪 Teste
```
aws --endpoint-url=http://localhost:4566 s3 ls
aws --endpoint-url=http://localhost:4566 s3 ls s3://arquivos-do-sistema/
```

## ⚙️ Config
### app.py
```
S3_ENDPOINT_URL = 'http://localhost:4566'
s3_client = boto3.client('s3', endpoint_url=S3_ENDPOINT_URL,
                        aws_access_key_id='test',
                        aws_secret_access_key='test')
```

### docker-compose.yml
```
services:
  localstack:
    image: localstack/localstack
    ports: ["4566:4566"]
    environment:
      - SERVICES=s3
      - DEBUG=1
volumes:
  localstack_data:
```

## 🛑 Stop
```
docker compose down
deactivate
```

## 🔍 Debug
```
docker compose logs -f
curl http://localhost:4566/health
```

## 🔧 Custom
- Bucket: mude S3_BUCKET_NAME
- Serviços: adicione lambda,sqs no docker-compose
