_E='template_id'
_D='message'
_C='code'
_B='Authorization'
_A=False
from enum import IntEnum
import json,os
from PIL import Image
from io import BytesIO
import numpy as np,requests,pyzipper
from requests.exceptions import RequestException,Timeout,HTTPError
from urllib.parse import urljoin
from.utils import get_local_app_setting_path
DEFAULT_SUBDOMAIN='api'if os.getenv('DEBUG')!='true'else'test'
DEFAULT_URL_PREFIX=f"https://{DEFAULT_SUBDOMAIN}.riceround.online"
DEFAULT_WS_PREFIX=f"wss://{DEFAULT_SUBDOMAIN}.riceround.online"
class UploadType(IntEnum):TEMPLATE_PUBLISH_IMAGE=1;USER_UPLOAD_TASK_IMAGE=2;MACHINE_TASK_RESULT=1000
class CatUrlConfig:
	_instance=None;_initialized=_A
	def __new__(A,*B,**C):
		if A._instance is None:A._instance=super(CatUrlConfig,A).__new__(A)
		return A._instance
	def __init__(A):
		if not A._initialized:A._initialized=True
	def get_server_url(A,url_path):return urljoin(A.url_prefix,url_path)
	def get_ws_url(A,url_path):return urljoin(A.ws_prefix,url_path)
	@property
	def ws_prefix(self):return DEFAULT_WS_PREFIX
	@property
	def url_prefix(self):return DEFAULT_URL_PREFIX
	@property
	def login_api_url(self):return self.get_server_url('/api/workflow/get_info')
	@property
	def workflow_url(self):return self.get_server_url(f"/api/cryptocat/workflow")
	@property
	def serial_number_url(self):return self.get_server_url(f"/api/cryptocat/serial_number")
	@property
	def user_client_workflow(self):return self.get_server_url(f"/api/cryptocat/client_workflow")
def user_upload_image(image,user_token):
	H='data';G='image/png';D=CatUrlConfig().user_upload_sign_url;I={_B:f"Bearer {user_token}"};J={'upload_type':UploadType.USER_UPLOAD_TASK_IMAGE.value,'file_type':G};A=requests.get(D,headers=I,params=J);E='';B=''
	if A.status_code==200:
		C=A.json()
		if C.get(_C)==0:E=C.get(H,{}).get('upload_sign_url','');B=C.get(H,{}).get('download_url','')
	else:raise ValueError(f"failed to upload image. Status code: {A.status_code}")
	if not E or not B:raise ValueError(f"failed to upload image. upload_sign_url is empty")
	K=255.*image.cpu().numpy();L=Image.fromarray(np.clip(K,0,255).astype(np.uint8));F=BytesIO();L.save(F,format='PNG',quality=95,compress_level=1);M=F.getvalue();A=requests.put(D,data=M,headers={'Content-Type':G})
	if A.status_code==200:return B
	else:print(f"failed to upload image. Status code: {A.status_code}");raise ValueError(f"failed to upload image. Status code: {A.status_code}")
def user_upload_workflow(template_id,workflow_path,user_token,timeout=30):
	'\n    用户上传工作流文件到服务器。\n\n    :param workflow_id: 工作流的模板ID\n    :param workflow_path: 工作流文件的本地路径\n    :param user_token: 用户的认证Token\n    :param timeout: 请求超时时间（秒）\n    :return: (bool, str) 成功与否及相关消息\n    ';K='An unknown error occurred';J='Request timed out';I='Workflow uploaded successfully';A=workflow_path;B=CatUrlConfig().workflow_url;L={_B:f"Bearer {user_token}"};C=os.path.basename(A)
	if not os.path.isfile(A):print(f"File does not exist: {A}");return _A,'File does not exist'
	try:
		with open(A,'rb')as M:N=M.read()
		O={'file':(C,N,'application/octet-stream')};P={_E:template_id,'action':'upload'};print(f"Uploading file: {C} to {B}");D=requests.put(B,headers=L,files=O,data=P,timeout=timeout);D.raise_for_status()
		try:E=D.json()
		except ValueError:print('Response content is not valid JSON');return _A,'Server returned invalid response'
		if E.get(_C)==0:print(I);return True,I
		else:F=E.get(_D,'Upload failed');print(f"Upload failed: {F}");return _A,F
	except FileNotFoundError:print(f"File not found: {A}");return _A,'File not found'
	except Timeout:print(J);return _A,J
	except HTTPError as G:print(f"HTTP error occurred: {G}");return _A,f"HTTP error: {G}"
	except RequestException as H:print(f"Request exception occurred: {H}");return _A,f"Request exception: {H}"
	except Exception as Q:print(K);return _A,K
def download_crypto_workflow(template_id,hardware_id,serial_number,user_token=None):
	'\n    下载并解密工作流的函数\n\n    :param template_id: 模板ID\n    :param hardware_id: 硬件ID\n    :param serial_number: 序列号\n    :param user_token: 用户凭证 (可选)\n    :return: (status, content)\n        - status: bool, 表示操作是否成功\n        - content: 当status为True时，返回工作流内容；否则返回错误信息\n    ';M='utf-8';H=user_token;G=serial_number
	if not G:raise ValueError('serial_number (序列号) 参数不能为空')
	N=CatUrlConfig();O=N.user_client_workflow;I={}
	if H:I[_B]=f"Bearer {H}"
	P={_E:template_id,'hardware_id':hardware_id,'serial_number':G}
	try:B=requests.post(O,data=P,headers=I)
	except requests.RequestException as D:A=f"网络请求出现异常: {str(D)}";print(A);return _A,A
	if B.status_code!=200:
		if B.status_code==500:
			try:C=B.json();A=C.get(_D,f"未知错误 (status_code={B.status_code})")
			except Exception:A=f"服务器内部错误 (status_code={B.status_code})"
		else:A=f"下载工作流失败: status_code={B.status_code}"
		print(A);return _A,A
	try:C=B.json()
	except ValueError:A='无法解析返回的 JSON 数据';print(A);return _A,A
	J=C.get(_C,-1)
	if J!=0:A=C.get(_D,f"未知错误 code={J}");print(A);return _A,A
	K=C.get('workflow_url','');L=C.get('password','')
	if not K or not L:A='下载工作流失败: workflow_url 或 password 缺失';print(A);return _A,A
	try:E=requests.get(K)
	except requests.RequestException as D:A=f"下载工作流内容出现异常: {str(D)}";print(A);return _A,A
	if E.status_code!=200:A=f"下载工作流失败: status_code={E.status_code}";print(A);return _A,A
	try:
		Q=BytesIO(E.content)
		with pyzipper.AESZipFile(Q)as F:F.setpassword(L.encode(M));R=F.namelist()[0];S=F.read(R);return True,S.decode(M)
	except Exception as D:A=f"解密工作流失败: {str(D)}";print(A);return _A,A