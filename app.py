from flask import Flask, request, redirect, render_template, url_for, Response, abort
from werkzeug.utils import secure_filename
from PIL import Image
from io import BytesIO
import boto3
import uuid

app = Flask(__name__)

# S3 Configuration
BUCKET_NAME = 'your-s3-bucket-name'
S3_REGION = 'us-east-1'

# Boto3 S3 client (assumes EC2 IAM role or credentials are configured)
s3 = boto3.client('s3', region_name=S3_REGION)

@app.route('/')
def index():
    # List image keys from the bucket
    response = s3.list_objects_v2(Bucket=BUCKET_NAME)
    filenames = []
    if 'Contents' in response:
        for obj in response['Contents']:
            key = obj['Key']
            if key.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                filenames.append(key)
    return render_template('index.html', filenames=filenames)

@app.route('/upload', methods=['POST'])
def upload():
    uploaded_file = request.files['file']
    if uploaded_file and uploaded_file.filename != '':
        filename = f"{uuid.uuid4()}_{secure_filename(uploaded_file.filename)}"
        image = Image.open(uploaded_file).convert('L')

        if image.width > 800:
            height = int((800 / image.width) * image.height)
            image = image.resize((800, height))

        buffer = BytesIO()
        image_format = image.format if image.format else 'JPEG'
        image.save(buffer, format=image_format)
        buffer.seek(0)

        s3.upload_fileobj(
            buffer,
            BUCKET_NAME,
            filename,
            ExtraArgs={'ContentType': f'image/{image_format.lower()}'}
        )

        return redirect(url_for('index'))

    return redirect('/')

@app.route('/image/<filename>')
def serve_image(filename):
    try:
        s3_object = s3.get_object(Bucket=BUCKET_NAME, Key=filename)
        return Response(
            s3_object['Body'].read(),
            mimetype=s3_object['ContentType']
        )
    except s3.exceptions.NoSuchKey:
        abort(404)
