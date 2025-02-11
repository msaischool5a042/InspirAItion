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
] = "a monochromatic pencil sketch of a classic car, minimalist, impressionism, negative space"
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


queue_prompt(prompt)
