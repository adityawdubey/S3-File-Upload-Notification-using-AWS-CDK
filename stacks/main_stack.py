import aws_cdk as cdk 
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_lambda as _lambda,
    aws_s3_notifications as s3_notifications,
    aws_lambda_python_alpha as _alambda
)

from constructs import Construct

class main_stack(Stack):


    def __init__(self, scope: Construct, construct_id: str, email_subscription_endpoint: str, file_upload_bucket:str, **kwargs) -> None:
            super().__init__(scope, construct_id, **kwargs)

            # S3 Bucket
            bucket = s3.Bucket(self, 'FileUploadDestinationBucket', bucket_name=file_upload_bucket,
                              )

            # SNS Topic
            topic = sns.Topic(self, 'S3NotificationSNSTopic',
                            display_name='S3FileUploadNotificationTopic',
                            topic_name='s3-file-upload-notification-topic')

            # SNS Subscription
            sns.Subscription( self, 'MySnsSubscription',
                            topic=topic,
                            protocol=sns.SubscriptionProtocol.EMAIL,
                            endpoint=email_subscription_endpoint
            )

            # Queue
            queue = sqs.Queue(self, 'S3NotificationQueue',
                            queue_name='s3-notification-queue',
                            visibility_timeout=cdk.Duration.seconds(30),
                            receive_message_wait_time=cdk.Duration.seconds(0))

            '''
            # lambda
            lambda_function = _lambda.Function(self, 'S3FileUploadNotificationProcessor',
                                            runtime=_lambda.Runtime.PYTHON_3_8,
                                            handler='handler.lambda_handler',
                                            code=_lambda.Code.from_asset('lambda/S3FileUploadNotificationProcessor'),
                                            memory_size=256,
                                            timeout=cdk.Duration.seconds(30),
                                            environment={
                                                'SNS_TOPIC_ARN': topic.topic_arn,
                                                'SQS_QUEUE_URL': queue.queue_url,
                                            })
            '''

            # lambda-python-alpha
            lambda_function = _alambda.PythonFunction(
                self, 
                id= "S3FileUploadNotificationProcessor",
                entry="lambda/S3FileUploadNotificationProcessor",
                index="handler.py",
                handler="handler",
                runtime=_lambda.Runtime.PYTHON_3_8,   
                environment= {
                    'SNS_TOPIC_ARN': topic.topic_arn,
                    'SQS_QUEUE_URL': queue.queue_url,
                }
            )

            # Grant Lambda permissions
            bucket.grant_read_write(lambda_function)
            queue.grant_send_messages(lambda_function)
            topic.grant_publish(lambda_function)

            # Add S3 event notification
            bucket.add_event_notification(s3.EventType.OBJECT_CREATED, s3_notifications.LambdaDestination(lambda_function))

