import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

endpoint = "https://models.inference.ai.azure.com"
model_name = "DeepSeek-V3"
token = "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"

client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(token),
)

response = client.complete(
    messages=[
        UserMessage("What is the capital of France?"),
    ],
    max_tokens=1000,
    model=model_name
)

print(response.choices[0].message.content)