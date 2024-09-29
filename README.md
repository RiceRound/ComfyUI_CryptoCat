# CryptoCat: ComfyUI Compression and Encryption Node

[阅读中文版 README](CHINESE_README.md)

## Introduction
CryptoCat is a lightweight open-source node for ComfyUI, designed to simplify workflows while providing encryption protection for them.
![image](docs/image1.png)

## Use Cases
- Workflow Simplification: It can greatly simplify workflows.
- Encryption Authorization: It can protect core ideas within the workflow.

## Quick Start
You can see a simple [workflow demo](demo/demo.json) for reference:

1. Open the ComfyUI\custom_Nodes\ directory and clone the repository locally.
2. Start ComfyUI, and find the CryptoCat directory in the "Advanced" menu.
3. The InputCrypto node is used to compress the workflow, and after connecting and running it, you will get the compressed workflow in the directory.
4. You don't need to worry about the OutputCrypto node, it just automatically decompresses the workflow.
5. The RandomSeedNode generates random numbers on the server side to fix issues where the random numbers don't work after the workflow is packaged.


## Contribution Guide
Contributions to the CryptoCat project are welcome! You can submit Pull Requests or open Issues to propose new features or report bugs.

## License
This project is licensed under the MIT License. For more details, please refer to the LICENSE file.

## Contact
Email：hzxhzx321@gmail.com

![image](docs/wechat.jpg)

---
CryptoCat © 2024. All Rights Reserved.