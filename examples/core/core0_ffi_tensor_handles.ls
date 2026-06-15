module Core0FFITensorHandles

foreign cpp gpt_alloc_f64_buffer : i32 -> i32 = "ls_gpt_alloc_f64_buffer"
foreign cpp gpt_free_handle : i32 -> void = "ls_gpt_free_handle"
foreign cpp gpt_read_f64 : i32 -> i32 -> f64 = "ls_gpt_read_f64"
foreign cpp gpt_write_f64 : i32 -> i32 -> f64 -> void = "ls_gpt_write_f64"
foreign cpp gpt_dot_f64 : i32 -> i32 -> i32 -> f64 = "ls_gpt_dot_f64"
foreign cpp gpt_matmul_f64 : i32 -> i32 -> i32 -> i32 -> i32 -> i32 -> i32 = "ls_gpt_matmul_f64"

sample_buffer = gpt_alloc_f64_buffer(16)
sample_dot = gpt_dot_f64(1, 2, 16)
cleanup = gpt_free_handle(1)
