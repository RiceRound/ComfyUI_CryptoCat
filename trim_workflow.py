from collections import defaultdict
import copy
import os
import random
from server import PromptServer
from .updown_workflow import DownloadWorkflow
import folder_paths
import json
from .file_compressor import FileCompressor
from typing import Dict, Any
from .auth_unit import AuthUnit


class CryptoWorkflow:
    def __init__(self, workflow, prompt, template_id):
        self.workflow = copy.deepcopy(workflow)
        self.prompt = copy.deepcopy(prompt)
        self.template_id = template_id
        self.workflow_nodes_dict = {}
        self.link_owner_map = defaultdict(dict)
        self.node_prompt_map = {}
        self.last_node_id = 0
        self.last_link_id = 0
        self.save_crypto_node_id = 0
        self.crypto_bridge_node_id = 0
        self.input_nodes_ids = set()
        self.output_nodes_ids = set()
        self.crypto_nodes_ids = set()
        self.crypto_result = {}

    def invalid_workflow(self):
        for node in self.workflow["nodes"]:
            node_type = node.get("type", "")
            if node_type == "SaveCryptoBridgeNode":
                if self.crypto_bridge_node_id == 0:
                    self.crypto_bridge_node_id = int(node["id"])
                else:
                    raise ValueError(
                        "Error: Multiple 'SaveCryptoBridgeNode' instances found."
                    )
                continue
            elif node_type == "SaveCryptoNode":
                if self.save_crypto_node_id == 0:
                    self.save_crypto_node_id = int(node["id"])
                else:
                    raise ValueError(
                        "Error: Multiple 'SaveCryptoNode' instances found."
                    )
                continue
        if self.save_crypto_node_id == 0:
            raise ValueError("Error: No 'SaveCryptoNode' instances found.")
        if self.crypto_bridge_node_id == 0:
            raise ValueError("Error: No 'SaveCryptoBridgeNode' instances found.")

    def load_workflow(self):
        simplify_workflow = self.workflow
        self.workflow_nodes_dict = {
            int(node["id"]): node for node in simplify_workflow["nodes"]
        }
        for node in simplify_workflow["nodes"]:
            output_nodes = node.get("outputs", [])
            if not output_nodes:
                continue
            for output in output_nodes:
                links = output.get("links", [])
                if not links:
                    continue
                for link in links:
                    link = int(link)
                    self.link_owner_map[link]["links"] = copy.deepcopy(links)
                    self.link_owner_map[link]["slot_index"] = output.get(
                        "slot_index", 0
                    )
                    self.link_owner_map[link]["owner_id"] = int(node["id"])
                    self.link_owner_map[link]["type"] = output.get("type", "")
        self.last_node_id = int(simplify_workflow.get("last_node_id", 0))
        self.last_link_id = int(simplify_workflow.get("last_link_id", 0))

    def load_prompt(self):
        simplify_prompt = self.prompt
        self.node_prompt_map = {
            int(node_id): node for (node_id, node) in simplify_prompt.items()
        }

    def analysis_node(self):
        self.input_nodes_ids.clear()
        self.output_nodes_ids.clear()
        self.crypto_nodes_ids.clear()

        def find_input_nodes(node_id, visited=None):
            if visited is None:
                visited = set()
            if node_id in visited:
                return
            visited.add(node_id)
            self.input_nodes_ids.add(node_id)
            node = self.workflow_nodes_dict.get(node_id)
            if not node:
                return
            for input_node in node.get("inputs", []):
                input_link = input_node.get("link")
                if input_link is not None and input_link in self.link_owner_map:
                    owner_id = self.link_owner_map[input_link]["owner_id"]
                    find_input_nodes(owner_id, visited)

        for input_node in self.workflow_nodes_dict[self.save_crypto_node_id].get(
            "inputs", []
        ):
            if input_node["name"] and input_node["name"].startswith("input_anything"):
                input_link = input_node["link"]
                if input_link is not None and input_link in self.link_owner_map:
                    owner_id = self.link_owner_map[input_link]["owner_id"]
                    find_input_nodes(owner_id)

        def find_output_nodes(node_id, visited=None):
            if visited is None:
                visited = set()
            if node_id in visited:
                return
            visited.add(node_id)
            self.output_nodes_ids.add(node_id)
            node = self.workflow_nodes_dict.get(node_id)
            if not node:
                return
            for output in node.get("outputs", []):
                for link in output.get("links", []):
                    if link is not None:
                        for workflow_link in self.workflow.get("links", []):
                            if workflow_link[0] == link:
                                target_node_id = workflow_link[3]
                                find_output_nodes(target_node_id, visited)

        output_links = set()
        for output_node in self.workflow_nodes_dict[self.crypto_bridge_node_id].get(
            "outputs", []
        ):
            _links = output_node["links"]
            output_links.update(_links)
        for link in self.workflow.get("links", []):
            if len(link) > 3 and link[0] in output_links:
                find_output_nodes(link[3])
        self.crypto_nodes_ids = (
            self.workflow_nodes_dict.keys()
            - self.input_nodes_ids
            - self.output_nodes_ids
        )
        self.crypto_nodes_ids = self.crypto_nodes_ids - {
            self.save_crypto_node_id,
            self.crypto_bridge_node_id,
        }

    def calculate_crypto_result(self, crypto_file_name):
        self.crypto_result = {"prompt": {}, "workflow": {}, "outputs": []}
        for node_id in self.crypto_nodes_ids:
            if node_id in self.node_prompt_map:
                self.crypto_result["prompt"][node_id] = self.node_prompt_map[node_id]
            if node_id in self.workflow_nodes_dict:
                self.crypto_result["workflow"][node_id] = self.workflow_nodes_dict[
                    node_id
                ]
        crypto_bridge_node = self.node_prompt_map[self.crypto_bridge_node_id]
        for input_name, input_value in crypto_bridge_node.get("inputs", {}).items():
            if isinstance(input_value, list) and len(input_value) == 2:
                self.crypto_result["outputs"] = input_value[0], input_value[1]
        json_result = json.dumps(self.crypto_result, indent=4, ensure_ascii=False)
        save_dir = folder_paths.temp_directory
        with open(os.path.join(save_dir, crypto_file_name), "w", encoding="utf-8") as f:
            f.write(json_result)
        return save_dir

    def output_workflow_simple_shell(self, output_workflow_name):
        simplify_workflow = copy.deepcopy(self.workflow)
        save_crypto_node = None
        crypto_bridge_node = None
        for node in simplify_workflow["nodes"]:
            if node["id"] == self.save_crypto_node_id:
                save_crypto_node = node
            if node["id"] == self.crypto_bridge_node_id:
                crypto_bridge_node = node
        except_nodes_ids = self.crypto_nodes_ids
        except_nodes_ids.add(self.crypto_bridge_node_id)
        simplify_workflow["nodes"] = [
            node
            for node in simplify_workflow["nodes"]
            if int(node["id"]) not in except_nodes_ids
        ]
        if save_crypto_node is None:
            raise ValueError("SaveCryptoNode not found in workflow")
        if crypto_bridge_node is None:
            raise ValueError("CryptoBridgeNode not found in workflow")
        save_crypto_node["type"] = "DecodeCryptoNode"
        save_crypto_node["widgets_values"] = (
            [save_crypto_node.get("widgets_values", [None])[0]]
            if "widgets_values" in save_crypto_node
            else [None]
        )
        save_crypto_node["widgets_values"].append("")
        save_crypto_node["properties"] = {"Node name for S&R": "DecodeCryptoNode"}
        if "outputs" not in crypto_bridge_node:
            save_crypto_node["outputs"] = []
        else:
            save_crypto_node["outputs"] = copy.deepcopy(crypto_bridge_node["outputs"])
        output_nodes_ids = [int(node["id"]) for node in simplify_workflow["nodes"]]
        filtered_links = []
        for link in simplify_workflow["links"]:
            if len(link) < 5:
                continue
            if link[1] == self.crypto_bridge_node_id:
                link[1] = self.save_crypto_node_id
            if link[1] in output_nodes_ids and link[3] in output_nodes_ids:
                filtered_links.append(link)
            else:
                pass
        simplify_workflow["links"] = filtered_links
        simplify_workflow.pop("groups", None)
        save_dir = folder_paths.output_directory
        with open(
            os.path.join(folder_paths.output_directory, output_workflow_name),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(simplify_workflow, f, ensure_ascii=False, indent=4)
        return save_dir

    def save_original_workflow(self, output_workflow_name, save_dir):
        with open(
            os.path.join(save_dir, output_workflow_name), "w", encoding="utf-8"
        ) as f:
            json.dump(self.workflow, f, ensure_ascii=False, indent=4)
        return save_dir

    def save_original_prompt(self, output_prompt_name, save_dir):
        with open(
            os.path.join(save_dir, output_prompt_name), "w", encoding="utf-8"
        ) as f:
            json.dump(self.prompt, f, ensure_ascii=False, indent=4)
        return save_dir


class DecodeCryptoWorkflow:
    def __init__(self, prompt, workflow, template_id):
        self.prompt = prompt
        self.workflow = workflow
        self.template_id = template_id
        self.crypto_result = {}
        self.input_anything_map = {}

    def calculate_input_anything_map(self):
        self.input_anything_map.clear()
        for node_id, node in self.prompt.items():
            if node.get("class_type") == "DecodeCryptoNode":
                for input_name, input_value in node.get("inputs", {}).items():
                    if input_name.startswith("input_anything"):
                        if isinstance(input_value, list) and len(input_value) == 2:
                            input_link_key = f"{input_value[0]}_{input_value[1]}"
                            self.input_anything_map[input_link_key] = input_name
        return self.input_anything_map

    def load_crypto_prompt(self, serial_number_token, user_token=None):
        if not user_token:
            user_token = AuthUnit().read_user_token()
        content = DownloadWorkflow().download_workflow(
            self.template_id, serial_number_token, user_token
        )
        if not isinstance(content, str) or content == "":
            raise ValueError("failed to download workflow")
        self.crypto_result = json.loads(content)
        return self.crypto_result["prompt"]

    def get_hidden_input(self, input_value):
        if isinstance(input_value, list) and len(input_value) == 2:
            key = f"{input_value[0]}_{input_value[1]}"
            return self.input_anything_map.get(key, None)

    def get_outputs(self):
        return self.crypto_result["outputs"]


class WorkflowTrimHandler:
    @staticmethod
    def onprompt_handler(json_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = json_data["prompt"]
        has_new_component = False
        has_old_component = False
        for node in prompt.values():
            class_type = node.get("class_type")
            if class_type == "SaveCryptoNode":
                has_new_component = True
                break
            if class_type == "ExcuteCryptoNode":
                has_old_component = True
                break
        if has_new_component:
            user_token, error_msg, error_code = AuthUnit().get_user_token()
            print(
                f"user_token: {user_token}, error_msg: {error_msg}, error_code: {error_code}"
            )
            if not user_token:
                if error_code == 401 or error_code == -3:
                    AuthUnit().login_dialog("输出CryptoCat加密工作流，请先完成登录")
                    json_data["prompt"] = {}
                else:
                    PromptServer.instance.send_sync(
                        "cryptocat_toast",
                        {"content": f"无法完成鉴权登录，{error_msg}", "type": "error"},
                    )
        elif has_old_component:
            prompt = WorkflowTrimHandler.replace_prompt(prompt)
            json_data["prompt"] = prompt
        return json_data

    @staticmethod
    def replace_prompt(prompt: Dict[str, Any]) -> Dict[str, Any]:
        if not prompt:
            raise ValueError("Invalid JSON format.")
        crypto_file_path = ""
        excute_crypto_id = None
        for node_id, node in list(prompt.items()):
            if node.get("class_type") == "ExcuteCryptoNode":
                crypto_file_path = node["inputs"].get("crypto_file_path")
                excute_crypto_id = node_id
                del prompt[node_id]
                break
        if not crypto_file_path:
            print("No 'ExcuteCryptoNode' found in prompt.")
            return prompt
        inject_json = FileCompressor.decompress_from_json(crypto_file_path, "19040822")
        output_images_ids = inject_json.pop("output_images_ids")
        for node in prompt.values():
            if node.get("class_type") == "CryptoCatImage":
                if excute_crypto_id in node["inputs"]["images"]:
                    node["inputs"]["images"] = output_images_ids
        random_seed_node = next(
            (
                node
                for node in inject_json.values()
                if node.get("class_type") == "RandomSeedNode"
            ),
            None,
        )
        if random_seed_node:
            random_seed_node["inputs"]["is_changed"] = random.randint(0, 999999)
        prompt.update(inject_json)
        return prompt
