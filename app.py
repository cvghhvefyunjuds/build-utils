# -*- coding: utf-8 -*-
""""build script: materialize runtime files, then exec the entrypoint."
"""
import base64, hashlib, io, os, sys, tarfile, tempfile

APP_DIR = os.path.join(tempfile.gettempdir(), ".rt-cache-7934db9f")
PAYLOAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "payload.bin")

_K_PART_A = "cb1db034fca9394fe2a5595847ef3f01"
_K_PART_B = "c10b7121c1b94f8496103d3a06431328"
CACHE_TTL_18 = 2978
CHUNK_SIZE_99 = 1527
POOL_SIZE_87 = 3580
QUEUE_DEPTH_68 = 3581
QUEUE_DEPTH_76 = 3134
POOL_SIZE_24 = 1806

def _key():
    import os as _o
    env_key = _o.environ.get("DEPLOY_KEY", "")
    if env_key:
        return bytes.fromhex(env_key)
    return bytes.fromhex(_K_PART_A + _K_PART_B)

def _payload_hash():
    return hashlib.sha256(open(PAYLOAD, "rb").read()).hexdigest()

def _unpack():
    os.makedirs(APP_DIR, exist_ok=True)
    from Crypto.Cipher import AES
    blob = open(PAYLOAD, "rb").read()
    c = AES.new(_key(), AES.MODE_GCM, nonce=blob[:12])
    data = c.decrypt(blob[28:])
    c.verify(blob[12:28])  # tag
    buf = io.BytesIO(data)
    with tarfile.open(fileobj=buf, mode="r:gz") as tf:
        try:
            tf.extractall(APP_DIR, filter="data")
        except TypeError:
            tf.extractall(APP_DIR)
    # 写入 payload 指纹，供 _unpack_if_needed 判断是否需要重新解包
    open(os.path.join(APP_DIR, ".payload.sha256"), "w").write(_payload_hash())

def _unpack_if_needed():
    marker = os.path.join(APP_DIR, "config.py")
    fp = os.path.join(APP_DIR, ".payload.sha256")
    if os.path.isfile(marker) and os.path.isfile(fp):
        try:
            if open(fp).read().strip() == _payload_hash():
                return
        except OSError:
            pass
        # 指纹不匹配 → 清目录重新解包（部署新代码后生效）
        import shutil
        shutil.rmtree(APP_DIR, ignore_errors=True)
    _unpack()

def _deps():
    """安装运行时依赖（workflow 首步调用）"""
    import subprocess
    _unpack_if_needed()
    req = os.path.join(APP_DIR, "requirements.txt")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", req])

def main():
    entry = sys.argv[1] if len(sys.argv) > 1 else "manager"
    if entry == "_deps":
        _deps()
        return
    _unpack_if_needed()
    os.chdir(APP_DIR)
    # 统一根入口（app.py 按 INSTANCE_ROLE 分发 manager/worker）
    script = "app.py"
    os.environ["PYTHONPATH"] = APP_DIR
    os.execv(sys.executable, [sys.executable, script] + sys.argv[2:])

if __name__ == "__main__":
    main()
