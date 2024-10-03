import copy
import os
import random
import sys
import folder_paths
import json
from.file_compressor import FileCompressor

class WorkflowTrim():
    def __init__(self, workflow):
        if 'workflow' in workflow :
            self.workflow = copy.deepcopy(workflow['workflow'])
        else:
            self.workflow = copy.deepcopy(workflow)

        self.output_images_link = 0

        nodes_dict = {node['id']: node for node in self.workflow['nodes']}
        self.max_id_index = max(nodes_dict.keys()) + 1


    @staticmethod
    def find_workflow_related_nodes(nodes, input_ids):
        found_ids = set()
        stack = list(input_ids)
        while stack:
            link_id = stack.pop()
            for node_id, node in nodes.items():
                outputs = node.get('outputs', None)
                if not outputs:
                    continue
                for output in outputs:
                    links = output.get('links', None)
                    if not links:
                        continue
                    if link_id in links:
                        if node_id not in found_ids:
                            found_ids.add(node_id)
                            inputs = node.get('inputs', [])
                            for input_node in inputs:
                                link_id = input_node.get('link')
                                if link_id is not None:
                                    stack.append(link_id)
                        break
        return found_ids

    def trim_workflow(self):   
        if not self.workflow:
            raise ValueError("Invalid JSON format.")
                
        nodes_dict = {node['id']: node for node in self.workflow['nodes']}
        save_crypto_node_ids = [node_id for node_id, details in nodes_dict.items() if details.get('type') == 'SaveCryptoNode']
        if len(save_crypto_node_ids) == 1:
            save_crypto_node_id = save_crypto_node_ids[0]

            # 获取所有以 'input_anything' 开头的输入链接
            input_ids = set()
            for input_node in nodes_dict[save_crypto_node_id].get('inputs', []):
                if input_node['name'] and input_node['name'].startswith('input_anything'):
                    input_ids.add(input_node['link'])
                if input_node['name'] and input_node['name'] == "output_images":
                    self.output_images_link = input_node['link']

            # 只处理有效的链接 ID
            input_ids = {link_id for link_id in input_ids if link_id is not None}

            # 找到与输入链接相关的节点
            related_node_ids = self.find_workflow_related_nodes(nodes_dict, input_ids)

            # 添加 SaveCryptoNode 本身
            related_node_ids.add(save_crypto_node_id)

            # # 打印和删除不相关的节点
            # for node_id in nodes_dict.keys():
            #     if node_id not in related_node_ids:
            #         print(f"Removing node ID: {node_id} - {nodes_dict[node_id]}")

            # 更新节点和链接
            self.workflow['nodes'] = [details for node_id, details in nodes_dict.items() if node_id in related_node_ids]
            remaining_node_ids = {node['id'] for node in self.workflow['nodes']}
            self.workflow.pop('groups', None)
            self.workflow['output_images_id'] = self.output_images_link       

            
            # 保留包含任一节点 ID 的链接
            self.workflow['links'] = [
                link for link in self.workflow['links']
                if link[1] in remaining_node_ids and link[3] in remaining_node_ids
            ]

            return self.workflow
        
        elif len(save_crypto_node_ids) > 1:
            raise ValueError("Error: Multiple 'SaveCryptoNode' instances found.")
        else:
            raise ValueError("Error: No 'SaveCryptoNode' instances found.")
        
    
        

    def replace_workflow(self,hide_prompt_path):
        if not self.workflow:
            raise ValueError("Invalid JSON format.")

        nodes_dict = {node['id']: node for node in self.workflow['nodes']}
        output_images_link = None

        # 替换 SaveCryptoNode 为 ExcuteCryptoNode
        for node in self.workflow['nodes']:
            if node.get('type') == 'SaveCryptoNode':
                node['type'] = 'ExcuteCryptoNode'
                node['properties']['Node name for S&R'] = 'ExcuteCryptoNode'
                
                # 移除 output_images 输入并获取 link
                for inp in node['inputs']:
                    if inp['name'] == 'output_images':
                        output_images_link = inp.get('link')
                node['inputs'] = [inp for inp in node['inputs'] if inp['name'] != 'output_images']
                node['widgets_values'] = [hide_prompt_path]

        # 找到 ExcuteCryptoNode 的位置
        execute_node = next((node for node in self.workflow['nodes'] if node.get('type') == 'ExcuteCryptoNode'), None)

        if not execute_node:
            raise ValueError("No 'ExcuteCryptoNode' instance found.")        

        # 创建新的 CryptoCatImage 节点
        execute_node_pos = execute_node['pos']
        self.max_id_index = max(max(nodes_dict.keys()) + 1, self.max_id_index)
        new_save_image_node = {
            "id": self.max_id_index,  # 新节点 ID，确保唯一
            "type": "CryptoCatImage",
            "pos": {
                "0": execute_node_pos['0'] + 200,  # 设置位置在 ExcuteCryptoNode 右边 20 像素
                "1": execute_node_pos['1'] 
            },
            "size": {
                "0": 210,
                "1": 162
            },
            "flags": {},
            "order": 50,
            "mode": 0,
            "inputs": [
                {
                    "name": "images",
                    "type": "IMAGE",
                    "link": output_images_link,  # 使用获取的 link
                    "label": "images"
                }
            ],
            "outputs": [],  # 新节点没有输出
            "properties": {
                "Node name for S&R": "CryptoCatImage"
            }
        }
        # 将新节点添加到节点列表
        self.workflow['nodes'].append(new_save_image_node)

        # 删除原有的链接以避免冲突
        self.workflow['links'] = [
            link for link in self.workflow['links'] if link[0] != output_images_link
        ]

        # 用新的 outputs 替换 ExcuteCryptoNode 的 outputs
        execute_node['outputs'] = [
            {
                "name": "IMAGE",
                "type": "IMAGE",
                "links": [output_images_link],  # 连接到新节点
                "shape": 3,
                "label": "IMAGE",
                "slot_index": 0
            }
        ]

        # 添加链接信息
        self.workflow['links'].append([
            output_images_link,  # ExcuteCryptoNode 的输出 ID
                execute_node['id'],  # 新节点 ID
            0,  # 新节点的输入索引
            new_save_image_node['id'],    # ExcuteCryptoNode ID（旧节点 ID）
            0,  # 旧节点的输出索引
            "IMAGE"  # 数据类型
        ])

        return self.workflow
    

    def set_excute_crypto_node_path(self, path):
        if not self.workflow:
            raise ValueError("Invalid JSON format.")
        for node in self.workflow['nodes']:
            if node.get('type') == 'ExcuteCryptoNode':
                node['properties']['Path to executable file'] = path
    

    def get_remaining_node_ids(self):
        if not self.workflow:
            raise ValueError("Invalid JSON format.")
        remaining_node_ids = {node['id'] for node in self.workflow['nodes']}
        return remaining_node_ids
   


class PromptTrim():
    def __init__(self, prompt):
        self.prompt = prompt
        self.debug = True
        self.hide_part_prompt = {}
        self.show_part_prompt = {}

    def split_prompt(self, related_node_ids):
        if not self.prompt:
            raise ValueError("Invalid JSON format.")
        
        # 查找第一个 'SaveCryptoNode' 实例并转换为 int
        # save_crypto_node_id = next((int(node_id) for node_id, details in self.prompt.items() if details['class_type'] == 'SaveCryptoNode'), None)
        save_crypto_node_id = None
        output_images_ids = []
        for node_id, details in self.prompt.items():
            if details['class_type'] == 'SaveCryptoNode':
                output_images_ids = details['inputs'].get('output_images')
                save_crypto_node_id = int(node_id)
                break

        if save_crypto_node_id is None:
            raise ValueError("Error: No 'SaveCryptoNode' instances found.")

        if save_crypto_node_id not in related_node_ids:
            raise AssertionError("SaveCryptoNode not found in related node list.")

        self.hide_part_prompt = {}
        self.show_part_prompt = {}

        # 输出不在链中的节点
        for node_id in self.prompt.keys():
            node_id_int = int(node_id)  # 转换为 int 类型
            if node_id_int not in related_node_ids:
                self.hide_part_prompt[node_id_int] = self.prompt[node_id]
            else:
                self.show_part_prompt[node_id_int] = self.prompt[node_id]

        self.hide_part_prompt['output_images_ids'] = output_images_ids
        return self.show_part_prompt, self.hide_part_prompt
    

    def replace_prompt(self):
        if not self.prompt:
            raise ValueError("Invalid JSON format.")

        crypto_file_path = ''
        excute_crypto_id = None

        # 查找 ExcuteCryptoNode 并获取路径，同时构建需要删除的节点
        for node_id, node in list(self.prompt.items()):
            if node.get('class_type') == 'ExcuteCryptoNode':
                crypto_file_path = node['inputs'].get('crypto_file_path')
                excute_crypto_id = node_id
                # 删除当前节点
                del self.prompt[node_id]
                break   

        if not crypto_file_path:
            print("No 'ExcuteCryptoNode' found in prompt.")
            return self.prompt
        
        # print(f"{crypto_file_path=}")

        inject_json = FileCompressor.decompress_from_json(crypto_file_path, "19040822")        
        output_images_ids = inject_json['output_images_ids'] 
        inject_json.pop('output_images_ids', None)
        for node_id, node in list(self.prompt.items()):
            if node.get('class_type') == 'CryptoCatImage':
                ids = node['inputs']['images'] #input_images
                if excute_crypto_id in ids:
                    node['inputs']['images'] = output_images_ids   

        # 随机生成一个种子，避免缓存问题
        random_seed_node = next((node for node in inject_json.values() if node.get('class_type') == 'RandomSeedNode'), None)
        if random_seed_node:
            random_seed_node["inputs"]["is_changed"] = random.randint(0, 999999)              
                    

        # 将 inject_json 的节点合并到当前 prompt
        # for node in inject_json.get('nodes', []):
        #     self.prompt[node['id']] = node  # 使用 ID 添加或更新节点
        self.prompt.update(inject_json)

        if self.debug == True:
            temp_dir = os.environ.get('TEMP') or os.environ.get('TMP') or '/tmp' 
            filename = os.path.basename(crypto_file_path) + "_prompt.json"       
            with open(os.path.join(temp_dir, filename), "w", encoding="utf-8") as f:
                json.dump(self.prompt, f, indent=4)     
            print(f"prompt len = {len(self.prompt)}")       

        return self.prompt
    
    def has_crypto_node(self):
        if not self.prompt:
            return False
        return any(node.get('class_type') == 'ExcuteCryptoNode' for node in self.prompt.values())
        





            





if __name__ == "__main__":
    

    current_dir = os.path.dirname(os.path.abspath(__file__)) 
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    sys.path.append(parent_dir) 
    import folder_paths

    with open("D:\\work\\ComfyUI\\temp\\flux+lora简单版_original_workflow.json", "r", encoding="utf-8") as f:
        workflow = json.load(f)

    wt = WorkflowTrim(workflow)
    wt.trim_workflow()
    replace_json = wt.replace_workflow('')

    with open("D:\\work\\ComfyUI\\temp\\flux+lora简单版_trim.json", "w", encoding="utf-8") as f:
        json.dump(replace_json, f, indent=4)


 ######################################################
    with open("D:\\work\\ComfyUI\\temp\\flux+lora简单版.txt", "r", encoding="utf-8") as f:
        prompt = json.load(f)
    
    pt = PromptTrim(prompt)
    show_part_prompt, hide_part_prompt = pt.split_prompt(wt.get_remaining_node_ids())

    with open("D:\\work\\ComfyUI\\temp\\flux+lora简单版_show_part_prompt.json", "w", encoding="utf-8") as f:
        json.dump(show_part_prompt, f, indent=4)

    with open("D:\\work\\ComfyUI\\temp\\flux+lora简单版_hide_part_prompt.json", "w", encoding="utf-8") as f:
        json.dump(hide_part_prompt, f, indent=4)

    



    

