# LambdaScript FFI backends

This directory starts the backend access layer for `glc`.

The first backend is a C++ runtime kernel with a stable C ABI. Python uses `ctypes` to call that ABI. This avoids a many-language FFI mesh while still allowing Python and other hosts to use the same compiled runtime.

```text
LambdaScript IR
  -> glc backend selection
  -> C++ runtime kernel through C ABI
  -> Python adapter through ctypes
```

Build and test locally from the repository root:

```sh
mkdir -p glc/backend/ffi/cpp/build
g++ -std=c++17 -fPIC -shared \
  glc/backend/ffi/cpp/src/lambda_script_ffi.cpp \
  -I glc/backend/ffi/cpp/include \
  -o glc/backend/ffi/cpp/build/liblambda_script_ffi.so

python3 glc/backend/ffi/test/test_python_ffi.py
```
