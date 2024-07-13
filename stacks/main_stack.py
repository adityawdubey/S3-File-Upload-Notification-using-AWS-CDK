import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_lambda,
    aws_s3_notifications as s3_notifications,
    aws_lambda_python_alpha as python_lambda,
)

from constructs import Construct


class main_stack(Stack):
    def __init__(self, scope: Construct, construct_id: str, email_subscription_endpoint: str, file_upload_bucket: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket for file uploads
        self.bucket = s3.Bucket(
            self,
            "FileUploadDestinationBucket",
            bucket_name=file_upload_bucket,
            removal_policy=cdk.RemovalPolicy.DESTROY,  #This will ensure bucket is deleted even if not empty
            auto_delete_objects=True,  # Automatically delete objects in the bucket on delete
        )

        # SNS topic for file upload notifications
        self.topic = sns.Topic(
            self,
            "S3NotificationSNSTopic",
            display_name="S3FileUploadNotificationTopic",
            topic_name="s3-file-upload-notification-topic",
        )

        # Subscribe to the SNS topic with the provided email endpoint
        sns.Subscription(
            self,
            "MySnsSubscription",
            topic=self.topic,
            protocol=sns.SubscriptionProtocol.EMAIL,
            endpoint=email_subscription_endpoint,
        )

        # Create an SQS queue for file upload notifications
        self.queue = sqs.Queue(
            self,
            "S3NotificationQueue",
            queue_name="s3-notification-queue",
            visibility_timeout=cdk.Duration.seconds(30),
            receive_message_wait_time=cdk.Duration.seconds(0),
        )

        # Create a Lambda layer with the required dependencies
        self.lambda_layer = python_lambda.PythonLayerVersion(
            self,
            "LambdaLayer",
            entry="./lambda_layer",
            compatible_runtimes=[aws_lambda.Runtime.PYTHON_3_8],
        )
        # lambda function to process S3 file upload notifications
        self.s3_file_upload_notification_processor = aws_lambda.Function(
            self,
            "s3_file_upload_notification_processor",
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            handler="handler.lambda_handler",
            code=aws_lambda.Code.from_asset(
                "./lambda_functions/s3_file_upload_notification_processor"),
            # Attach the created Lambda layer
            layers=[self.lambda_layer],
            environment={
                "SNS_TOPIC_ARN": self.topic.topic_arn,
                "SQS_QUEUE_URL": self.queue.queue_url,
            },
            timeout=cdk.Duration.seconds(10),
        )

        # Grant Lambda permissions
        self.bucket.grant_read_write(self.s3_file_upload_notification_processor)
        self.queue.grant_send_messages(self.s3_file_upload_notification_processor)
        self.topic.grant_publish(self.s3_file_upload_notification_processor)

        # Add an event notification to the S3 bucket to trigger the Lambda function on file upload
        self.bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3_notifications.LambdaDestination(
                self.s3_file_upload_notification_processor),
        )
