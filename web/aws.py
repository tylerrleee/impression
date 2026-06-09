# web/aws.py

import os, json, boto3

S3_BUCKET   = os.environ["S3_BUCKET"]
SQS_URL     = os.environ["SQS_QUEUE_URL"]
REGION      = os.environ.get("AWS_REGION", "us-east-1")

_s3  = boto3.client("s3", region_name = REGION)
_sqs = boto3.client("sqs", region_name = REGION) 

def put_audio(key: str, data: bytes, content_type: str) -> None:
    _s3.put_object(Bucket = S3_BUCKET, Key = key, Body = data, ContentType = content_type)

def enqueue_job(job_id: str, s3_key: str) -> None:
    _sqs.send_message(QueueUrl = SQS_URL,
                      MessageBody = json.dumps({"job_id" : job_id, 
                                                "s3_key": s3_key}
                                                )
                                                    )