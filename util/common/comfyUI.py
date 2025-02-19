import json
import os
from urllib import request

# Load workflow prompt from workflow.json
workflow_path = os.path.join(os.path.dirname(__file__), "workflow.json")
with open(workflow_path, "r", encoding="utf-8") as f:
    prompt = json.load(f)


# set the text prompt for our positive CLIPTextEncode node
prompt["6"]["inputs"][
    "text"
] = "a dog sitting on a couch with a smile on its face, looking at the camera"
# set the seed for our KSampler node
prompt["3"]["inputs"]["seed"] = 1


def queue_prompt(prompt):
    # 수정: prompt를 문자열로 변환하지 않고 그대로 전송
    p = {"prompt": prompt}
    data = json.dumps(p).encode("utf-8")
    req = request.Request("http://comfyui.inspiraition.net:8188/prompt", data=data)
    try:
        response = request.urlopen(req)
        print("Response:", response.read().decode("utf-8"))
    except Exception as e:
        print("Error when sending prompt:", e)


# res = queue_prompt(prompt)
# print("Prompt ID:", res.prompt_id)


def get_image_info(prompt_id):
    url = f"http://comfyui.inspiraition.net:8188/history/{prompt_id}"
    try:
        response = request.urlopen(url)
        image_info = json.loads(response.read().decode("utf-8"))
        return image_info
    except request.HTTPError as e:
        if e.code == 404:
            print(
                f"Error: Image info with prompt_id '{prompt_id}' not found. Check the prompt_id or endpoint."
            )
        else:
            print("HTTP Error when retrieving image info:", e)
        return None
    except Exception as e:
        print("Error when retrieving image info:", e)
        return None


# Example usage
prompt_id = "d74327e8-29d0-4f80-8b6c-30b0c86f7a94"
image_info = get_image_info(prompt_id)
if image_info:
    # print("Image Info:", image_info)
    file_name = image_info[prompt_id]["outputs"]["9"]["images"][0]["filename"]
    img_url = f"http://comfyui.inspiraition.net:8188/api/view?filename={file_name}"
    print("Image URL:", img_url)
