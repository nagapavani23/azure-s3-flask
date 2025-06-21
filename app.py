from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Access them like normal env vars
access_key = os.getenv('AWS_ACCESS_KEY_ID')
secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
region = os.getenv('AWS_DEFAULT_REGION')

print(f"AWS Access Key: {access_key}")

import boto3
import botocore.exceptions

app = Flask(__name__, template_folder="template")

s3 = boto3.client("s3")


@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html")


@app.route("/list")
def list_files():
    """List all files in a specified S3 bucket."""
    bucket_name = request.args.get("bucket_name")

    if not bucket_name:
        return jsonify({"error": "Bucket name is required"}), 400

    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        objects = response.get("Contents", [])

        if not objects:
            return jsonify({"message": "No files found in the bucket"}), 404

        files = [obj["Key"] for obj in objects]
        return jsonify(files)

    except botocore.exceptions.NoCredentialsError:
        return jsonify({"error": "AWS credentials not found"}), 401

    except botocore.exceptions.ParamValidationError:
        return jsonify({"error": "Invalid parameters provided"}), 400

    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500

@app.route("/create_folder", methods=["POST"])
def create_folder():
    """Create a folder in an S3 bucket."""
    try:
        bucket_name = request.form.get("bucket_name")
        folder_name = request.form.get("folder_name")

        if not bucket_name or not folder_name:
            return jsonify({"error": "Bucket name and folder name are required"}), 400

        # Ensure folder name ends with a slash to be treated as a folder
        if not folder_name.endswith("/"):
            folder_name += "/"

        # Upload an empty file to create the folder
        s3.put_object(Bucket=bucket_name, Key=folder_name)
        return jsonify({"message": f"Folder '{folder_name}' created successfully in bucket '{bucket_name}'"})

    except botocore.exceptions.NoCredentialsError:
        return jsonify({"error": "AWS credentials not found"}), 401

    except botocore.exceptions.BotoCoreError as e:
        return jsonify({"error": f"AWS Error: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500

        

@app.route("/delete_folder", methods=["POST"])
def delete_folder():
    """Delete a folder and all its contents from an S3 bucket."""
    try:
        bucket_name = request.form.get("bucket_name")
        folder_name = request.form.get("folder_name")

        if not bucket_name or not folder_name:
            return jsonify({"error": "Bucket name and folder name are required"}), 400

        # Ensure the folder name ends with a slash
        if not folder_name.endswith("/"):
            folder_name += "/"

        # List all objects within the folder
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_name)
        objects = response.get("Contents", [])

        if not objects:
            return jsonify({"message": f"Folder '{folder_name}' not found or already empty in bucket '{bucket_name}'"}), 404

        # Collect all object keys to delete
        keys = [{"Key": obj["Key"]} for obj in objects]

        # Delete all the objects within the folder
        delete_response = s3.delete_objects(
            Bucket=bucket_name,
            Delete={"Objects": keys}
        )

        return jsonify({"message": f"Folder '{folder_name}' and its contents deleted successfully from '{bucket_name}'"})

    except botocore.exceptions.NoCredentialsError:
        return jsonify({"error": "AWS credentials not found"}), 401

    except botocore.exceptions.BotoCoreError as e:
        return jsonify({"error": f"AWS Error: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500


@app.route("/upload", methods=["POST"])
def upload_file():
    """Upload a file to a specified S3 bucket."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        bucket_name = request.form.get("bucket_name")
        file = request.files["file"]

        if not bucket_name:
            return jsonify({"error": "Bucket name is required"}), 400

        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        s3.upload_fileobj(file, bucket_name, file.filename)
        return jsonify({"message": f"File '{file.filename}' uploaded successfully to '{bucket_name}'"})

    except botocore.exceptions.NoCredentialsError:
        return jsonify({"error": "AWS credentials not found"}), 401

    except botocore.exceptions.BotoCoreError as e:
        return jsonify({"error": f"AWS Error: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500


@app.route("/delete", methods=["POST"])
def delete_file():
    """Delete a file from a specified S3 bucket."""
    try:
        bucket_name = request.form.get("bucket_name")
        file_name = request.form.get("file_name")

        if not bucket_name or not file_name:
            return jsonify({"error": "Bucket name and file name are required"}), 400

        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=file_name)
        if "Contents" not in response:
            return jsonify({"error": "File not found"}), 404

        s3.delete_object(Bucket=bucket_name, Key=file_name)
        return jsonify({"message": f"File '{file_name}' deleted successfully from '{bucket_name}'"})

    except botocore.exceptions.NoCredentialsError:
        return jsonify({"error": "AWS credentials not found"}), 401

    except botocore.exceptions.BotoCoreError as e:
        return jsonify({"error": f"AWS Error: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500

@app.route("/copy_file", methods=["POST"])
def copy_file():
    """Copy a file within S3 from one bucket to another."""
    try:
        source_bucket = request.form.get("source_bucket")
        source_key = request.form.get("source_key")
        destination_bucket = request.form.get("destination_bucket")
        destination_key = request.form.get("destination_key")

        if not source_bucket or not source_key or not destination_bucket or not destination_key:
            return jsonify({"error": "All fields (source and destination) are required"}), 400

        copy_source = {"Bucket": source_bucket, "Key": source_key}

        # Copy the file to the destination bucket and key
        s3.copy_object(
            CopySource=copy_source,
            Bucket=destination_bucket,
            Key=destination_key
        )

        return jsonify({"message": f"File '{source_key}' successfully copied from '{source_bucket}' to '{destination_bucket}/{destination_key}'"})

    except botocore.exceptions.NoCredentialsError:
        return jsonify({"error": "AWS credentials not found"}), 401

    except botocore.exceptions.BotoCoreError as e:
        return jsonify({"error": f"AWS Error: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500


@app.route("/create_bucket", methods=["POST"])
def create_bucket():
    """Create a new S3 bucket."""
    try:
        bucket_name = request.form.get("bucket_name")
        region = request.form.get("region", "eu-north-1")

        if not bucket_name:
            return jsonify({"error": "Bucket name is required"}), 400

        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        return jsonify({"message": f"Bucket '{bucket_name}' created successfully"})

    except botocore.exceptions.BotoCoreError as e:
        return jsonify({"error": f"AWS Error: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500



@app.route("/delete_bucket", methods=["POST"])
def delete_bucket():
    """Delete an S3 bucket."""
    try:
        bucket_name = request.form.get("bucket_name")

        if not bucket_name:
            return jsonify({"error": "Bucket name is required"}), 400

        s3.delete_bucket(Bucket=bucket_name)
        return jsonify({"message": f"Bucket '{bucket_name}' deleted successfully"})

    except botocore.exceptions.BotoCoreError as e:
        return jsonify({"error": f"AWS Error: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
