#include "lambda_script_ffi.h"

int ls_add_int(int left, int right) {
    return left + right;
}

const char *ls_runtime_name(void) {
    return "lambda-script-cpp-ffi";
}
