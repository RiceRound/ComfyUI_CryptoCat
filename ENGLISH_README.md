# CryptoCat: ComfyUI Compression and Encryption Node

## Introduction
CryptoCat is a lightweight open-source node for ComfyUI that simplifies workflows while providing encryption protection.

![image](docs/image1.png)

## Use Cases
- Workflow Simplification: Significantly simplifies complex workflows.
- Encryption Authorization: Protects core concepts within your workflows.

## Quick Start
You can view a simple [Workflow Demo](demo/original.json)

### Installation and Usage
1. **Install the Node**
   - Open ComfyUI\custom_Nodes\ directory and clone the repository
   - Or install "ComfyUI Compression and Encryption Node" through ComfyUI-Manager

2. **Launch and Configure**
   - Start ComfyUI
   - Find the CryptoCat directory in the "Advanced" menu

3. **🔐 How to Use**
   - Use encryption component and encryption end bridge as start and end points to control the encrypted workflow section
   - Random seeds will generate random numbers on the server side to fix issues with randomization after workflow encapsulation

> ⚠️ Decryption component doesn't need to be added manually - after encryption, the system will automatically generate a workflow with decryption components in the output folder
> 
> ⚠️ During encryption, 10 serial numbers will be automatically generated. When users first use it, it will be bound to their hardware information, and subsequent use will verify the consistency between the serial number and hardware information

## Contributing
Contributions to CryptoCat are welcome! You can contribute by submitting Pull Requests or opening Issues to suggest new features or report problems.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Contact
Email: <hzxhzx321@gmail.com>

![image](docs/wechat.jpg)

---
CryptoCat © 2024. All Rights Reserved.