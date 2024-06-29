import aws_cdk as core
import aws_cdk.assertions as assertions

from stacks.main_stack import main_stack

# example tests. To run these tests, uncomment this file along with the example
# resource in s3_file_upload_notification_system_using_aws_cdk/s3_file_upload_notification_system_using_aws_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = main_stack(app, "")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
