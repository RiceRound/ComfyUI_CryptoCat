import torch
from nodes import SaveImage
import folder_paths


class ExcuteCryptoNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "crypto_file_path": (
                    "STRING",
                    {"default": folder_paths.output_directory},
                )
            },
            "optional": {"input_anything": ("*",)},
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "excute"
    CATEGORY = "__hidden__"

    def excute(self, **kwargs):
        batch_size = 1
        height = 1024
        width = 1024
        color = 16711680
        r = torch.full([batch_size, height, width, 1], (color >> 16 & 255) / 255)
        g = torch.full([batch_size, height, width, 1], (color >> 8 & 255) / 255)
        b = torch.full([batch_size, height, width, 1], (color & 255) / 255)
        return (torch.cat((r, g, b), dim=-1),)


class CryptoCatImage(SaveImage):
    def __init__(self):
        super().__init__()

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save."}),
                "filename_prefix": (
                    "STRING",
                    {
                        "default": "ComfyUI",
                        "tooltip": "The prefix for the file to save. This may include formatting information such as %date:yyyy-MM-dd% or %Empty Latent Image.width% to include values from nodes.",
                    },
                ),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "__hidden__"
    DESCRIPTION = "Saves the input images to your ComfyUI output directory."

    def save_images(
        self, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None
    ):
        return super().save_images(images, filename_prefix, None, None)
