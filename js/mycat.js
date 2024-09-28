import { ComfyApp, app } from "../../../scripts/app.js";

app.registerExtension({
    name: "cryptocat.mycat",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {

        if (nodeData.name === 'SaveCryptoNode') {
            const input_name = "input_anything";

            const onConnectionsChange = nodeType.prototype.onConnectionsChange;
            nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
                if (!link_info) return;
                // 更新输入名称
                let slot_i = 1;
                for (let i = 1; i < this.inputs.length; i++) {
                    let input_i = this.inputs[i];
                    if (input_i.name !== 'select' && input_i.name !== 'sel_mode') {
                        input_i.name = `${input_name}${slot_i}`;
                        slot_i++;
                    }
                }

                // 处理断开连接后的输入移除逻辑
                if (!connected && (this.inputs.length > 2)) {
                    const stackTrace = new Error().stack;

                    if (
                        !stackTrace.includes('LGraphNode.prototype.connect') && // for touch device
                        !stackTrace.includes('LGraphNode.connect') && // for mouse device
                        !stackTrace.includes('loadGraphData') &&
                        this.inputs[index].name != 'select') {
                        this.removeInput(index);
                    }

                    let slot_i = 1;
                    for (let i = 1; i < this.inputs.length; i++) {
                        let input_i = this.inputs[i];
                        if (input_i.name != 'select' && input_i.name != 'sel_mode') {
                            input_i.name = `${input_name}${slot_i}`
                            slot_i++;
                        }
                    }
                }

                // 动态添加输入
                let last_slot = this.inputs[this.inputs.length - 1];
                if (
                    (last_slot.name == 'select' && last_slot.name != 'sel_mode' && this.inputs[this.inputs.length - 2].link != undefined)
                    || (last_slot.name != 'select' && last_slot.name != 'sel_mode' && last_slot.link != undefined)) {
                    this.addInput(`${input_name}${slot_i}`, "*");
                }

            };
        }
    },

    nodeCreated(node, app) {
        if (node.comfyClass == "SaveCryptoNode") {
            if (node.widgets && node.widgets.length > 1 && app.workflowManager) {
                node.widgets[1].value = app.workflowManager.activeWorkflow.name;
            }
        }
    },

    // async setup(app) {
    //     console.log(app.workflowManager.activeWorkflow.name)
    //     if (this.widgets) {
    //         this.widgets[1].value = app.workflowManager.activeWorkflow.name;
    //     }
    // },

    // },
});