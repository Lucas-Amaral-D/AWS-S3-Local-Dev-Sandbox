import os
from flask import Flask, render_template, request, redirect, url_for, Response
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)

# --- CONFIGURAÇÃO DO LOCALSTACK/S3 ---
AWS_ACCESS_KEY_ID = 'test'
AWS_SECRET_ACCESS_KEY = 'test'
AWS_REGION = 'us-east-1'
S3_ENDPOINT_URL = 'http://localhost:4566' # Aponta para o container LocalStack
S3_BUCKET_NAME = 'arquivos-do-sistema'  # Nome do bucket

# Inicializa o cliente S3 do Boto3
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
    endpoint_url=S3_ENDPOINT_URL
)

def create_bucket_if_not_exists():
    """Tenta criar o bucket se ele ainda não existir no LocalStack."""
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
        print(f"Bucket '{S3_BUCKET_NAME}' já existe.")
    except ClientError as e:
        # Se o erro for 404 Not Found, o bucket precisa ser criado
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == '404' or error_code == 'NoSuchBucket':
            try:
                # O LocalStack é mais flexível, mas o CreateBucket pode exigir LocationConstraint
                s3_client.create_bucket(Bucket=S3_BUCKET_NAME) 
                print(f"Bucket '{S3_BUCKET_NAME}' criado com sucesso.")
            except ClientError as ce:
                print(f"Erro ao criar bucket: {ce}")
        else:
            print(f"Erro ao verificar bucket: {e}")

# Executa a criação do bucket ao iniciar o Flask
create_bucket_if_not_exists()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # --- Lógica de UPLOAD de Arquivo ---
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        
        if file.filename == '':
            return redirect(request.url)

        if file:
            object_key = file.filename
            
            try:
                # upload_fileobj é a maneira eficiente de fazer upload com Boto3
                s3_client.upload_fileobj(
                    file,
                    S3_BUCKET_NAME,
                    object_key
                )
                print(f"Arquivo '{object_key}' enviado com sucesso.")
            except Exception as e:
                print(f"Erro durante o upload: {e}")
            
            return redirect(url_for('index'))

    # --- Lógica de LISTAGEM de Arquivos ---
    files = []
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME)
        # Extrai o nome (Key) dos objetos no bucket
        if 'Contents' in response:
            files = [obj['Key'] for obj in response['Contents']]
    except ClientError as e:
        print(f"Erro ao listar objetos: {e}")

    return render_template('index.html', files=files, bucket_name=S3_BUCKET_NAME)


@app.route('/download/<filename>')
def download(filename):
    # --- Lógica de DOWNLOAD de Arquivo ---
    try:
        # Pega o objeto do S3
        file_object = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=filename)
        
        # Cria uma resposta de streaming para o download
        return Response(
            file_object['Body'].read(),
            mimetype=file_object['ContentType'],
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
    except ClientError as e:
        # Retorna erro 404 se o arquivo não for encontrado
        return f"Erro ao baixar arquivo: Arquivo não encontrado.", 404
    except Exception as e:
        return f"Erro inesperado: {str(e)}", 500


if __name__ == '__main__':
    # Roda o Flask, permitindo acesso de fora do container (necessário no WSL/Docker)
    app.run(debug=True, host='0.0.0.0')
