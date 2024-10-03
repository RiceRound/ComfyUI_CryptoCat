import json
import os
import random
import torch

from nodes import SaveImage
from .trim_workflow import PromptTrim, WorkflowTrim
from.file_compressor import FileCompressor
import folder_paths


class SaveCryptoNode():
    def __init__(self):
        pass


    @classmethod
    def INPUT_TYPES(s):
        return {
                "required": {           
                "crypto_folder": ("STRING", {"default": folder_paths.output_directory}),
                "crypto_name": ("STRING", {"default": "my_cat.json"}),    
                "output_images" : ("IMAGE",),                    
                },
                "optional": {
                    "input_anything" : ("*",),
                },
                "hidden": {
                    "unique_id": "UNIQUE_ID",
                    "prompt": "PROMPT", 
                    "extra_pnginfo": "EXTRA_PNGINFO",
                }
            }    

    # @classmethod
    # def VALIDATE_INPUTS(s, input_types):
    #     return True

 
    RETURN_TYPES = ()  #"STRING",
    OUTPUT_NODE = True
    FUNCTION = "crypto"  #这个节点中的主函数 
    CATEGORY = "advanced/CryptoCat"    
 
    def crypto(self, crypto_folder, crypto_name, output_images, **kwargs):
        if not crypto_name or len(crypto_folder) < 2 or len(crypto_name) == 0:
            raise Exception("CryptoCat folder and filename must be at least two characters long")
        
        # 从 kwargs 中提取特定参数
        unique_id = kwargs.pop('unique_id', None)
        prompt = kwargs.pop('prompt', None)
        extra_pnginfo = kwargs.pop('extra_pnginfo', None)

        # 检查必需参数是否存在
        if unique_id is None:
            raise Exception("Warning: 'unique_id' is missing.")
        if prompt is None:
            raise Exception("Warning: 'prompt' is missing.")

        # 将剩余的 kwargs 存储在 inputs 列表中
        inputs = list(kwargs.values())               

        temp_dir = os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp'
        project_temp_folder = os.path.join(temp_dir, crypto_name)
        if not os.path.exists(project_temp_folder):
            os.makedirs(project_temp_folder)


        # 保存源文件，用于调试
        with open(os.path.join(project_temp_folder, "prompt.json"), "w", encoding="utf-8") as f:            
            f.write(json.dumps(prompt, indent=4, ensure_ascii=False))
        with open(os.path.join(project_temp_folder, "workflow.json"), "w", encoding="utf-8") as f:            
            f.write(json.dumps(extra_pnginfo, indent=4, ensure_ascii=False))  

        # 保存需要的输出文件
        project_folder = os.path.join(crypto_folder, crypto_name)
        if not os.path.exists(project_folder):
            os.makedirs(project_folder)

        hide_prompt_path = os.path.join(project_folder, "prompt.dat")        
        # 解析workflow
        wt = WorkflowTrim(extra_pnginfo)
        wt.trim_workflow()
        show_workflow = wt.replace_workflow(hide_prompt_path)
        with open(os.path.join(project_folder, "workflow.json"), "w", encoding="utf-8") as f:            
            f.write(json.dumps(show_workflow, indent=4, ensure_ascii=False))

        # 拆分prompt
        pr = PromptTrim(prompt)
        show_part_prompt,  hide_part_prompt = pr.split_prompt(wt.get_remaining_node_ids())
        with open(os.path.join(project_temp_folder, "prompt_show.json"), "w", encoding="utf-8") as f:            
            f.write(json.dumps(show_part_prompt, indent=4, ensure_ascii=False))        

        FileCompressor.compress_to_json(hide_part_prompt, hide_prompt_path, "19040822")
        return (hide_part_prompt,)



class ExcuteCryptoNode():
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": { 
                "crypto_file_path": ("STRING", {"default": folder_paths.output_directory}),         
            },
            "optional": {
                "input_anything" : ("*",),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT", 
                "extra_pnginfo": "EXTRA_PNGINFO",
            }
        }
 
    RETURN_TYPES = ("IMAGE",) 
    FUNCTION = "excute"  #这个节点中的主函数 
    CATEGORY = "advanced/CryptoCat"
 
    def excute(self, **kwargs):
        batch_size = 1
        height = 1024
        width = 1024
        color = 0xFF0000        
        r = torch.full([batch_size, height, width, 1], ((color >> 16) & 0xFF) / 0xFF)
        g = torch.full([batch_size, height, width, 1], ((color >> 8) & 0xFF) / 0xFF)
        b = torch.full([batch_size, height, width, 1], ((color) & 0xFF) / 0xFF)
        return (torch.cat((r, g, b), dim=-1), )
    

# 产生随机数
class RandomSeedNode():
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {     
            },
            "optional": {
            },
            "hidden": {
            }
        }
 
    RETURN_TYPES = ("INT",) 
    FUNCTION = "random"  #这个节点中的主函数 
    CATEGORY = "advanced/CryptoCat"

    def IS_CHANGED():
        return float("NaN")
 
    def random(self):
        # 产生随机数
        return (random.randint(0, 999999), )
    

class CryptoCatImage(SaveImage):
    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save."}),
                "filename_prefix": ("STRING", {"default": "ComfyUI", "tooltip": "The prefix for the file to save. This may include formatting information such as %date:yyyy-MM-dd% or %Empty Latent Image.width% to include values from nodes."})
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"

    OUTPUT_NODE = True

    CATEGORY = "advanced/CryptoCat"
    DESCRIPTION = "Saves the input images to your ComfyUI output directory."

    def save_images(self, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None):
        return super().save_images(images, filename_prefix, None, None)