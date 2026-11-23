# CryptoCat for ComfyUI

CryptoCat 将工作流中的节点封装到 CryptoCat Server，并生成一个可用序列号运行的 ComfyUI 工作流。

## 安装

将 `ComfyUI_CryptoCat` 放到 ComfyUI 的 `custom_nodes` 目录。用启动 ComfyUI 的同一个 Python 安装 `requirements.txt`，然后重启 ComfyUI。

```sh
python -m pip install -r ComfyUI/custom_nodes/ComfyUI_CryptoCat/requirements.txt
```

在加密组件、解密组件或 ComfyUI 的扩展菜单打开「CryptoCat 设置」，可管理全局服务地址。从加密组件或扩展菜单打开时还可管理发布账号，从解密组件打开时只显示服务地址和当前工作流。插件用同一个服务地址进行发布和激活。`defaults.ini` 将新安装的默认地址设为 `https://cryptocat.riceround.online`。点击地址旁的编辑图标，在弹窗确认新地址即可生效。部署时可用环境变量 `CRYPTOCAT_API_URL` 固定服务地址，此时隐藏编辑图标。

未登录时可从加密组件或扩展菜单点击「发布者登录」，运行加密组件也会打开登录弹窗。设置面板会显示橙色登录提示，服务地址可提前配置。登录后，加密组件收起登录按钮，设置面板显示「退出发布账号」。退出会保留机器 ID 和已有激活。只有发布需要登录；解密组件只读取服务地址和序列号。

发布者可在弹窗中使用手机验证码登录，ComfyUI 会向 CryptoCat 发起请求并保存登录凭证。登录服务无法连接或返回服务异常时，可点击「改用登录 Token」，在网站的插件接入页登录后复制 Token，粘贴回弹窗并确认。验证码错误或服务明确拒绝时，弹窗会显示原来的错误提示。登录后重新排队发布。使用者在解密组件中填写序列号即可运行。

插件设置写入使用同源 JSON 请求。通过反向代理访问 ComfyUI 时，代理应保留公开的 Host。解密组件直接凭序列号访问 CryptoCat Server，只需填写服务地址，不要求登录发布账号。

从解密组件打开「CryptoCat 设置」可查看只读模板 ID，并通过旁边的复制图标将 ID 提供给开发者排查问题。

## 发布与使用

1. 在主画布放置一个「加密组件」和一个「加密结束桥接」。将使用者可修改的输入同时连接到加密组件和需要该输入的内部节点。
2. 将待封装的结果接到桥接，再从桥接连接相应的输出节点。桥接支持一路结果，可分接到接受该类型的多个输出节点。
3. 加密组件只读显示工作流名称和模板 ID。点「CryptoCat 设置」，在下半部分修改名称或模板。名称默认使用当前标题或文件名，模板 ID 由插件生成。点「↻」随机生成新 ID，或点旁边的「⇄」从当前账号最近更新的 20 个工作流中选择替换目标。已命名的目标会显示其原名称，填入自定义名称可以改名。目标失效时可重选或生成新 ID。
   「自动覆盖同 ID 模板」是此 ComfyUI 的发布偏好，沿用已有设置，初始关闭。开启后，发布时会直接覆盖当前账号同 ID 的模板。关闭时，重复发布需要确认。通过「⇄」选定的替换目标在下次发布时直接替换。
   连接仅支持 `create` 和 `upload` 的旧服务时，插件会重新确认模板仍存在且属于当前账号，再改用旧版覆盖操作。发布成功后可从网站「我的工作流」进入该模板的序列号管理。
4. 从画布排队发布。发布成功后，输出目录会保存 `cryptocat_<模板ID>.json`。成功弹窗中可复制 ComfyUI 所在设备的输出目录路径。点「前往网站生成序列号」，登录发布该工作流的账号后签发。网站「我的工作流」也为每条工作流提供发码入口。打开生成的工作流，在解密组件填入序列号并排队。

图片可接 `SaveImage` 或 `PreviewImage`。原生视频可将 `CreateVideo` 的 `VIDEO` 接入桥接，再接 `SaveVideo`。图像帧可经桥接接入 `SaveWEBM`、`SaveAnimatedWEBP` 或已安装的 Video Helper Suite `VHS_VideoCombine`。容器、编码、帧率和文件前缀仍在对应输出节点中设置。运行加密工作流需要安装原工作流使用的节点和模型。

发布支持 ComfyUI 的 0.4 数组连线和 1.0 对象连线格式。加密组件负责发布，若需预览原始工作流，可选中输出节点后使用 ComfyUI 的选定节点排队功能。公开工作流会保留可编辑的输入和输出节点及其依赖。

## 示例工作流

- [图像输出](example_workflows/simple1.json)使用采样工作流演示 `PreviewImage`。
- [MP4 视频输出](example_workflows/save_video.json)将纯色帧经 `CreateVideo` 转成 `VIDEO`，通过桥接交给 `SaveVideo`。
- [WebM 视频输出](example_workflows/save_webm.json)将缩放后的 `IMAGE` 帧通过桥接交给 `SaveWEBM`。

两个视频示例只用 ComfyUI 内置节点和 CryptoCat 节点。将 JSON 拖入画布时，插件会为留空的加密组件生成模板 ID。保存工作流可在下次打开时沿用该 ID。按上面的发布步骤生成解密工作流。

## English

Install the folder under `ComfyUI/custom_nodes` and install the requirements using ComfyUI's Python. The default server is `https://cryptocat.riceround.online`; change it in CryptoCat settings if you use a different server. To publish, open the sign-in dialog from the encryption node and sign in with your phone number. If the login service is unavailable, the dialog offers the option to paste a login token from the CryptoCat website. Running a decrypted workflow needs only the server URL and a serial number, with no account sign-in.

Keep public workflow inputs connected to the encryption node. Connect the private result to the bridge, and connect the bridge to an output such as Save Image, Save Video, or a frame-based video output. Queue the workflow to publish. ComfyUI saves the generated JSON to its output folder and links to the workflow's serial number form on the CryptoCat website. Sign in with the publishing account, issue a serial number, and enter it in the decode node.

## License

[MIT](LICENSE)
