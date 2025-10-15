import os
from flask import Flask, render_template, request, redirect, url_for, Response, session
import boto3
from botocore.exceptions import ClientError
from werkzeug.security import generate_password_hash, check_password_hash 

app = Flask(__name__)
app.secret_key = 'uma_chave_secreta_muito_segura_e_longa_para_sessao' 

AWS_ACCESS_KEY_ID = 'test'
AWS_SECRET_ACCESS_KEY = 'test'
AWS_REGION = 'us-east-1'
LOCALSTACK_ENDPOINT_URL = 'http://localhost:4566' 

S3_BUCKET_NAME = 'arquivos-do-sistema'
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
    endpoint_url=LOCALSTACK_ENDPOINT_URL
)

DYNAMODB_TABLE_NAME = 'UserAccounts'
dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
    endpoint_url=LOCALSTACK_ENDPOINT_URL
)

user_table = None 

def create_bucket_if_not_exists():
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
        print(f"[S3] Bucket '{S3_BUCKET_NAME}' já existe.")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code in ('404', 'NoSuchBucket'):
            try:
                s3_client.create_bucket(Bucket=S3_BUCKET_NAME) 
                print(f"[S3] Bucket '{S3_BUCKET_NAME}' criado com sucesso.")
            except ClientError as ce:
                print(f"[S3] Erro ao criar bucket: {ce}")
        else:
            print(f"[S3] Erro ao verificar bucket: {e}")

def create_user_table_if_not_exists():
    global user_table
    try:
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        table.load()
        print(f"[DynamoDB] Tabela '{DYNAMODB_TABLE_NAME}' já existe.")
        user_table = table
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"[DynamoDB] Criando tabela '{DYNAMODB_TABLE_NAME}'...")
            try:
                table = dynamodb.create_table(
                    TableName=DYNAMODB_TABLE_NAME,
                    KeySchema=[
                        {'AttributeName': 'username', 'KeyType': 'HASH'}
                    ],
                    AttributeDefinitions=[
                        {'AttributeName': 'username', 'AttributeType': 'S'}
                    ],
                    ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                )
                table.wait_until_exists()
                print(f"[DynamoDB] Tabela '{DYNAMODB_TABLE_NAME}' criada com sucesso.")
                user_table = table
            except Exception as ce:
                print(f"[DynamoDB] Erro ao criar tabela: {ce}")
        else:
            print(f"[DynamoDB] Erro ao acessar tabela: {e}")

@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        hashed_password = generate_password_hash(password)
        
        try:
            response = user_table.get_item(Key={'username': username})
            if 'Item' in response:
                return render_template('signup.html', error="Nome de usuário já existe.")
            
            user_table.put_item(
                Item={
                    'username': username,
                    'password_hash': hashed_password,
                    'email': request.form['email']
                }
            )
            return redirect(url_for('login', message="Conta criada com sucesso! Faça login."))

        except Exception as e:
            return render_template('signup.html', error=f"Erro ao registrar: {e}")

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            response = user_table.get_item(Key={'username': username})
            user_item = response.get('Item')
            
            if user_item and check_password_hash(user_item['password_hash'], password):
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="Credenciais inválidas.")

        except Exception as e:
            return render_template('login.html', error=f"Erro ao fazer login: {e}")
    
    return render_template('login.html', message=request.args.get('message'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login', message="Você saiu da conta."))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        
        if file.filename:
            object_key = f"{session['username']}/{file.filename}"
            
            try:
                s3_client.upload_fileobj(
                    file,
                    S3_BUCKET_NAME,
                    object_key
                )
                print(f"[S3] Arquivo '{object_key}' enviado por {session['username']}")
            except Exception as e:
                print(f"[S3] Erro durante o upload: {e}")
            
            return redirect(url_for('dashboard'))

    files = []
    try:
        prefix = f"{session['username']}/"
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        
        if 'Contents' in response:
            files = [
                {
                    'key': obj['Key'],
                    'filename': obj['Key'].replace(prefix, '', 1) 
                } 
                for obj in response['Contents']
            ]
    except ClientError as e:
        print(f"[S3] Erro ao listar objetos: {e}")

    return render_template(
        'dashboard.html', 
        username=session['username'], 
        bucket_name=S3_BUCKET_NAME, 
        files=files
    )

@app.route('/download/<path:filename>')
def download(filename):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    full_object_key = f"{session['username']}/{filename}"
    
    try:
        file_object = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=full_object_key)
        
        return Response(
            file_object['Body'].read(),
            mimetype=file_object['ContentType'],
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
    except ClientError as e:
        return f"Erro ao baixar arquivo: Arquivo não encontrado ou permissão negada.", 404
    except Exception as e:
        return f"Erro inesperado: {str(e)}", 500

if __name__ == '__main__':
    create_bucket_if_not_exists()
    create_user_table_if_not_exists()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
