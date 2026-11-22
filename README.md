# CryptoCat for ComfyUI

CryptoCat 将工作流中的节点封装到 CryptoCat Server，并生成一个可用序列号运行的 ComfyUI 工作流。

## 安装

将 `ComfyUI_CryptoCat` 放到 ComfyUI 的 `custom_nodes` 目录。用启动 ComfyUI 的同一个 Python 安装 `requirements.txt`，然后重启 ComfyUI。

```sh
python -m pip install -r ComfyUI/custom_nodes/ComfyUI_CryptoCat/requirements.txt
```

在加密组件或解密组件上点击「CryptoCat 设置」，填写你的 CryptoCat Server 地址，例如 `https://cryptocat.example.com`。也可通过 ComfyUI 的扩展菜单打开面板。部署时可用环境变量 `CRYPTOCAT_API_URL` 固定服务地址。公开发行包需要自行填写服务地址。

发布者在服务端的「插件接入」页使用手机验证码登录并生成发布 Token，然后粘贴到插件面板。使用者填写服务地址和解密组件中的序列号即可运行。移除发布 Token 会保留机器 ID 和已有激活。

## 发布与使用

1. 在主画布放置一个「加密组件」和一个「加密结束桥接」。将使用者可修改的输入同时连接到加密组件和需要该输入的内部节点。
2. 将待封装的结果接到桥接，再从桥接连接相应的输出节点。桥接支持一路结果，可分接到接受该类型的多个输出节点。
3. 从画布排队发布。同 ID 模板可在弹窗确认覆盖，也可以在设置里启用自动覆盖。
4. ComfyUI 输出目录会生成 `cryptocat_<模板ID>.json` 和 `serial_numbers_<模板ID>.txt`。打开生成的工作流，在解密组件填写序列号并排队。也可在面板按模板 ID 补发序列号。

图片可接 `SaveImage` 或 `PreviewImage`。原生视频可将 `CreateVideo` 的 `VIDEO` 接入桥接，再接 `SaveVideo`。图像帧可经桥接接入 `SaveWEBM`、`SaveAnimatedWEBP` 或已安装的 Video Helper Suite `VHS_VideoCombine`。容器、编码、帧率和文件前缀仍在对应输出节点中设置。运行加密工作流需要安装原工作流使用的节点和模型。

发布支持 ComfyUI 的 0.4 数组连线和 1.0 对象连线格式。加密组件负责发布，若需预览原始工作流，可选中输出节点后使用 ComfyUI 的选定节点排队功能。公开工作流会保留可编辑的输入和输出节点及其依赖。

[图像工作流示例](example_workflows/simple1.json)

## English

Install the folder under `ComfyUI/custom_nodes` and install the requirements using ComfyUI's Python. Open the CryptoCat settings from a CryptoCat node or the Extensions menu. Set your CryptoCat Server URL and, to publish, paste a publisher token from the server's plugin page.

Keep public workflow inputs connected to the encryption node. Connect the private result to the bridge, and connect the bridge to an output such as Save Image, Save Video, or a frame-based video output. Queue the workflow to publish, then open the generated JSON and enter a serial number in the decode node. ComfyUI writes the generated workflow and serial numbers to its output folder.

## License

[MIT](LICENSE)
