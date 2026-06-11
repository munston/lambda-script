#ifndef LAMBDA_SCRIPT_FFI_H
#define LAMBDA_SCRIPT_FFI_H

#ifdef __cplusplus
extern "C" {
#endif

int ls_add_int(int left, int right);
const char *ls_runtime_name(void);

#ifdef __cplusplus
}
#endif

#endif
