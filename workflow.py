from collections import defaultdict
from copy import deepcopy

from comfy_execution.graph_utils import is_link


INPUT_PREFIX = "input_anything"
SAVE = "SaveCryptoNode"
BRIDGE = "SaveCryptoBridgeNode"
DECODE = "DecodeCryptoNode"


def external_input(name):
    return name.startswith(INPUT_PREFIX) and (
        name == INPUT_PREFIX or name[len(INPUT_PREFIX):].isascii() and name[len(INPUT_PREFIX):].isdigit()
    )


def reachable(start, edges, stop=()):
    seen = set(stop)
    result = set()
    pending = list(start)
    while pending:
        node = pending.pop()
        if node in seen:
            continue
        seen.add(node)
        result.add(node)
        pending.extend(edges.get(node, ()))
    return result


def link_fields(link):
    if isinstance(link, dict):
        return link["id"], link["origin_id"], link["target_id"]
    return link[0], link[1], link[3]


def public_subgraphs(definitions, nodes):
    by_id = {str(graph["id"]): graph for graph in definitions}
    included = reachable(
        (node["type"] for node in nodes),
        {graph_id: [node["type"] for node in graph["nodes"]] for graph_id, graph in by_id.items()},
    )
    return [graph for graph_id, graph in by_id.items() if graph_id in included]


def package_workflow(workflow, prompt, save_id, template_id, *, workflow_name=""):
    if not isinstance(workflow, dict) or not isinstance(workflow.get("nodes"), list):
        raise ValueError("发布需要 ComfyUI 的画布工作流，请从画布排队")
    workflow = deepcopy(workflow)
    nodes = {str(node["id"]): node for node in workflow["nodes"]}
    save_ids = [node_id for node_id, node in nodes.items() if node["type"] == SAVE]
    bridge_ids = [node_id for node_id, node in nodes.items() if node["type"] == BRIDGE]
    save_id = str(save_id)
    if save_ids != [save_id] or len(bridge_ids) != 1:
        raise ValueError("请在主画布放置一个加密组件和一个加密结束桥接")
    bridge_id = bridge_ids[0]
    bridge_link = prompt.get(bridge_id, {}).get("inputs", {}).get("value")
    if not is_link(bridge_link) or bridge_link[0] not in prompt:
        raise ValueError("请将要封装的结果连接到加密结束桥接")

    parents = {
        node_id: [value[0] for value in node.get("inputs", {}).values() if is_link(value)]
        for node_id, node in prompt.items()
    }
    bridge_dependencies = reachable([bridge_link[0]], parents)
    external = {
        name: value for name, value in prompt[save_id]["inputs"].items()
        if external_input(name) and is_link(value)
    }
    external_links = {tuple(value) for value in external.values()}
    public_sources = reachable((link[0] for link in external.values()), parents)
    private = bridge_dependencies - public_sources
    if not private or private.intersection({save_id, bridge_id}):
        raise ValueError("桥接前需要至少一个有效的待封装节点")
    for node_id in private:
        if node_id not in prompt:
            raise ValueError("待封装工作流含有丢失的节点连接")
        for value in prompt[node_id]["inputs"].values():
            if is_link(value) and value[0] not in private and tuple(value) not in external_links:
                raise ValueError(f"节点 {node_id} 使用了未接到加密组件的公开输入，请接入对应输出端口")

    links = workflow.get("links") or []
    save = nodes[save_id]
    name_socket = next((socket for socket in save.get("inputs") or [] if socket["name"] == "workflow_name"), None)
    if name_socket is not None:
        save["inputs"].remove(name_socket)
        if name_socket.get("link") is not None:
            links = [link for link in links if str(link_fields(link)[0]) != str(name_socket["link"])]
    canvas_parents = defaultdict(list)
    canvas_children = defaultdict(list)
    for link in links:
        _, src, dst = link_fields(link)
        canvas_parents[str(dst)].append(str(src))
        canvas_children[str(src)].append(str(dst))
    downstream = reachable(canvas_children[bridge_id], canvas_children)
    if not downstream:
        raise ValueError("请将桥接输出连接到画布上的输出节点")
    public = reachable(downstream | {save_id}, canvas_parents, stop={bridge_id})
    if any(node_id.split(":", 1)[0] in public for node_id in private):
        raise ValueError("公开节点依赖了加密区，请将跨区输出统一接到加密结束桥接")

    workflow_title = (save.get("properties") or {}).get("cryptocat_workflow_title")
    save["type"] = DECODE
    save["widgets_values"] = [template_id, ""]
    save["properties"] = {"Node name for S&R": DECODE}
    save["outputs"] = nodes[bridge_id].get("outputs") or []
    workflow["nodes"] = [node for node in workflow["nodes"] if str(node["id"]) in public]
    workflow["links"] = []
    kept_links = set()
    for link in links:
        link_id, src, dst = link_fields(link)
        if str(src) not in public | {bridge_id} or str(dst) not in public:
            continue
        output_src = save["id"] if str(src) == bridge_id else src
        if isinstance(link, dict):
            link["origin_id"] = output_src
            link.pop("parentId", None)
        else:
            link[1] = output_src
        workflow["links"].append(link)
        kept_links.add(str(link_id))
    for node in workflow["nodes"]:
        for socket in node.get("inputs") or []:
            if str(socket.get("link")) not in kept_links:
                socket["link"] = None
        for socket in node.get("outputs") or []:
            socket["links"] = [link for link in socket.get("links") or [] if str(link) in kept_links]
    workflow.pop("groups", None)
    workflow.pop("reroutes", None)
    layout = (workflow.get("extra") or {}).get("ds")
    workflow["extra"] = {"ds": layout} if layout else {}
    definitions = workflow.pop("definitions", None)
    if definitions:
        subgraphs = public_subgraphs(definitions.get("subgraphs", []), workflow["nodes"])
        if subgraphs:
            workflow["definitions"] = {"subgraphs": subgraphs}

    payload = {
        "inputs": external,
        "outputs": bridge_link,
        "prompt": {node_id: prompt[node_id] for node_id in prompt if node_id in private},
    }
    if workflow_name:
        payload["workflow_name"] = workflow_name
    if workflow_title:
        payload["workflow_title"] = workflow_title
    return payload, workflow
