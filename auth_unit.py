_G='clear_key'
_F='cryptocat_clear_user_info'
_E='long_token'
_D='user_token'
_C=None
_B='Auth'
_A='utf-8'
import base64,json,logging,os
from pathlib import Path
import time
from.url_config import CatUrlConfig
from server import PromptServer
import requests,configparser
from.utils import generate_random_string,get_local_app_setting_path,get_machine_id
CRYPT_FLAG='CAT_CRYPT'
CRYPT_FLAG_LENGTH=len(CRYPT_FLAG)
class AuthUnit:
	_instance=_C
	def __new__(A,*B,**C):
		if A._instance is _C:A._instance=super(AuthUnit,A).__new__(A)
		return A._instance
	def __init__(A):
		B=True
		if not hasattr(A,'initialized'):A.machine_id=get_machine_id();C=get_local_app_setting_path();C.mkdir(parents=B,exist_ok=B);A.config_path=C/'config.ini';A.token=A.read_user_token();A.long_token=A.read_long_token();A.client_key='';A.shift_key=sum(ord(A)for A in A.machine_id[:8])%20+1;A.last_check_time=0;A.initialized=B
	def empty_token(A,token,clear=False):
		C=clear;B=token
		if B==A.token:
			A.token=''
			if C:PromptServer.instance.send_sync(_F,{_G:_D})
		elif B==A.long_token:
			A.long_token=''
			if C:PromptServer.instance.send_sync(_F,{_G:_E})
		else:print('empty_token error',B)
	def get_user_token(B):
		A=B.token
		if not A:
			A=B.read_user_token()
			if not A:
				if B.long_token and len(B.long_token)>50:A=B.long_token
				else:return _C,'no token found'
			else:B.token=A
		if time.time()-B.last_check_time>120 and A:
			try:
				D={'Content-Type':'application/json','Authorization':f"Bearer {A}"};print('login_api_url',CatUrlConfig().login_api_url);C=requests.get(CatUrlConfig().login_api_url,headers=D)
				if C.status_code==200:B.last_check_time=time.time()
				else:print('crypto cat login result error',C);B.empty_token(A,C.status_code==401);A=_C;return _C,'login result error'
			except requests.RequestException as E:B.empty_token(A);A=_C;print('crypto cat login failed',E);return _C,'login failed'
		return A,''
	def login_dialog(A,title=''):A.client_key=generate_random_string(8);PromptServer.instance.send_sync('cryptocat_login_dialog',{'machine_id':A.machine_id,'client_key':A.client_key,'title':title})
	@staticmethod
	def _encrypt(text,shift_key):
		'Encrypt text using a simple character shift and base64 encoding.'
		if not text:return''
		try:B=CRYPT_FLAG+''.join(chr((ord(A)+shift_key)%65536)for A in text);return base64.b64encode(B.encode(_A)).decode(_A)
		except Exception as A:logging.error(f"Encryption error: {A}");raise RuntimeError(f"Encryption failed: {A}")
	@staticmethod
	def _decrypt(encoded_text,shift_key):
		'Decrypt text that was encrypted with the _encrypt method.';B=encoded_text
		try:
			A=base64.b64decode(B.encode(_A)).decode(_A)
			if not A.startswith(CRYPT_FLAG):return B
			A=A[CRYPT_FLAG_LENGTH:];return''.join(chr((ord(A)-shift_key)%65536)for A in A)
		except Exception as C:print(f"Decryption error: {C}");return B
	def read_user_token(A):
		'Retrieve and decrypt the user token.'
		if not os.path.exists(A.config_path):return''
		try:
			B=configparser.ConfigParser();B.read(A.config_path,encoding=_A);C=B.get(_B,_D,fallback='')
			if not C:return''
			return AuthUnit._decrypt(C,A.shift_key)
		except Exception as D:print(f"Error reading token: {D}");return''
	def save_user_token(A,user_token,client_key):
		'Encrypt and save the user token.';D=client_key;C=user_token
		if not C:return
		if not D or A.client_key!=D:return
		try:
			A.token=C;B=configparser.ConfigParser()
			if os.path.exists(A.config_path):B.read(A.config_path,encoding=_A)
			if _B not in B:B.add_section(_B)
			F=AuthUnit._encrypt(C,A.shift_key);B[_B][_D]=F
			with open(A.config_path,'w',encoding=_A)as G:B.write(G)
		except Exception as E:print(f"Error saving token: {E}");raise RuntimeError(f"Failed to save token: {E}")
	def save_long_token(A,long_token):
		C=long_token
		try:
			if not C or C=='null':A.long_token='';C=''
			else:A.long_token=C
			B=configparser.ConfigParser()
			if os.path.exists(A.config_path):B.read(A.config_path,encoding=_A)
			if _B not in B:B.add_section(_B)
			B[_B][_E]=A.long_token
			with open(A.config_path,'w',encoding=_A)as E:B.write(E)
		except Exception as D:print(f"Error saving long token: {D}");raise RuntimeError(f"Failed to save long token: {D}")
	def read_long_token(A):
		if not os.path.exists(A.config_path):return''
		try:B=configparser.ConfigParser();B.read(A.config_path,encoding=_A);return B.get(_B,_E,fallback='')
		except Exception as C:print(f"Error reading long token: {C}");return''
	def clear_user_token(B):
		B.token='';B.long_token='';PromptServer.instance.send_sync(_F,{_G:'all'})
		if not os.path.exists(B.config_path):return
		try:
			A=configparser.ConfigParser();A.read(B.config_path,encoding=_A)
			if _B not in A:return
			if _D not in A[_B]:return
			A[_B][_D]='';A[_B][_E]=''
			with open(B.config_path,'w',encoding=_A)as D:A.write(D)
		except Exception as C:print(f"Error clearing token: {C}");raise RuntimeError(f"Failed to clear token: {C}")