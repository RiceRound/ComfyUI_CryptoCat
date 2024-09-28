import json
import zlib
import os

class FileCompressor:

    @staticmethod
    def obfuscate(data, password):
        return bytes([b ^ ord(password[i % len(password)]) for i, b in enumerate(data)])

    @staticmethod
    def compress_string(string_data, zip_path, password):
        compressed_data = zlib.compress(string_data.encode('utf-8'))
        obfuscated_data = FileCompressor.obfuscate(compressed_data, password)
        with open(zip_path, 'wb') as zipf:
            zipf.write(obfuscated_data)

    @staticmethod
    def decompress_to_string(zip_path, password):
        with open(zip_path, 'rb') as zipf:
            obfuscated_data = zipf.read()
            compressed_data = FileCompressor.obfuscate(obfuscated_data, password)  # 反混淆
            return zlib.decompress(compressed_data).decode('utf-8')

    @staticmethod
    def compress_to_json(data, zip_path, password):
        try:
            json_string = json.dumps(data, indent=4, ensure_ascii=False)  # Convert data to JSON string
            FileCompressor.compress_string(json_string, zip_path, password)  # Call compress_string
        except Exception as e:
            print(f"Compression failed: {e}")

    @staticmethod
    def decompress_from_json(zip_path, password):
        try:
            if not os.path.exists(zip_path):
                raise FileNotFoundError(f"{zip_path} does not exist")
            json_string = FileCompressor.decompress_to_string(zip_path, password)  # Call decompress_to_string
            return json.loads(json_string)  # Convert back to dictionary
        except Exception as e:
            print(f"Decompression failed: {e}")
