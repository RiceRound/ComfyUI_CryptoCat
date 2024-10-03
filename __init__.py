from functools import wraps
import json
from .trim_workflow import PromptTrim
from .crypto_node import SaveCryptoNode, ExcuteCryptoNode, RandomSeedNode,CryptoCatImage

NODE_CLASS_MAPPINGS = {
    "SaveCryptoNode": SaveCryptoNode,
    "ExcuteCryptoNode": ExcuteCryptoNode,
    "RandomSeedNode": RandomSeedNode,
    "CryptoCatImage":CryptoCatImage,
}
 
# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveCryptoNode": "InputCrypto",
    "ExcuteCryptoNode": "OutputCrypto",
    "RandomSeedNode": "RandomSeedNode",
    "CryptoCatImage":"CryptoCatImage",
}

WEB_DIRECTORY = "./js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAMES_MAPPINGS', 'WEB_DIRECTORY']


from server import PromptServer


method_name = "trigger_on_prompt"
original_method = getattr(PromptServer, method_name)

# 创建 hook
@wraps(original_method)
def new_trigger_on_prompt(self, json_data):
    prompt = json_data["prompt"]
    pr = PromptTrim(prompt)    
    if pr.has_crypto_node():
        print("has crypto node")
        json_data["prompt"] = pr.replace_prompt()
        # 删除 extra_data 字段
        if "extra_data" in json_data:
            json_data["extra_data"] = {}
            print("hook new_trigger_on_prompt delete extra_data")
    result = original_method(self, json_data)    
    return result

setattr(PromptServer, method_name, new_trigger_on_prompt)