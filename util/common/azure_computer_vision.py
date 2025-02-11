import os
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials

# ...existing code...


def get_image_caption_and_tags(image_url):
    AZURE_COMPUTER_VISION_API_KEY = os.getenv("AZURE_COMPUTER_VISION_API_KEY")
    AZURE_COMPUTER_VISION_ENDPOINT = os.getenv("AZURE_COMPUTER_VISION_ENDPOINT")

    computervision_client = ComputerVisionClient(
        AZURE_COMPUTER_VISION_ENDPOINT,
        CognitiveServicesCredentials(AZURE_COMPUTER_VISION_API_KEY),
    )

    # Analyze the image using the Dense Caption feature
    analysis = computervision_client.describe_image(image_url)

    # Extract the caption information
    captions = []
    if analysis.captions:
        for caption in analysis.captions:
            print("Caption: ", caption.text)
            captions.append(caption.text)
    else:
        captions.append("No caption detected.")

    # Extract the tag information
    tags_result = computervision_client.tag_image(image_url)
    tags = [tag.name for tag in tags_result.tags]
    print("Tags: ", tags)

    return captions, tags


# ...existing code...
image_url = "https://imgnews.pstatic.net/image/011/2025/02/05/0004447162_001_20250205215010307.png?type=w860"
image_url = "https://img1.daumcdn.net/thumb/R1280x0.fjpg/?fname=http://t1.daumcdn.net/brunch/service/user/aZCw/image/eeJn2IfiJW6Jmmu4mXFVBGcNcxs.jpg"
image_url = "https://flexible.img.hani.co.kr/flexible/normal/860/484/imgdb/original/2025/0206/20250206503901.webp"
image_url = "https://flexible.img.hani.co.kr/flexible/normal/968/645/imgdb/original/2025/0205/20250205503135.webp"
get_image_caption_and_tags(image_url)
