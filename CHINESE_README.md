
# CryptoCat: ComfyUI压缩加密节点

## 简介
CryptoCat是一个小巧的ComfyUI开源节点，它的作用在于简化工作流，同时给工作流提供加密保护。

![image](docs/image1.png)

## 应用场景
- 流程简化：可以大幅度简化工作流。
- 加密授权：可以保护工作流里的一些核心思路。

## 快速开始
你可以在这里看到一个简单的 [Workflow Demo](demo/demo.json)

1. 打开ComfyUI\custom_ Nodes\目录，克隆仓库到本地。
2. 启动ComfyUI，菜单“高级”（advance）中找到CryptoCat目录。
3. InputCrypto节点用于压缩工作流，连线运行之后会在目录下得到压缩后的工作流
4. OutputCrypto节点不用管，它只是用于自动解压工作流
5. RandomSeedNode会在服务端生成随机数，用于修补工作流封装后随机数不起效的情况

  

## 贡献指南
欢迎对CryptoCat项目做出贡献！你可以通过提交Pull Request或开设Issue来提出新功能建议或报告问题。

## 许可证
本项目遵循MIT许可证。有关详细信息，请参阅LICENSE文件。

## 联系方式
Email：<hzxhzx321@gmail.com>

![image](docs/wechat.jpg)

---
CryptoCat © 2024. All Rights Reserved.
