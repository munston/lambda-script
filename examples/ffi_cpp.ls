module CppFFI

foreign cpp add_i32 : i32 -> i32 -> i32 = "ls_add_i32"
foreign cpp mul_f64 : f64 -> f64 -> f64 = "ls_mul_f64"
foreign cpp log_message : string -> void = "ls_log_message"

answer = add_i32(40, 2)
scaled = mul_f64(3.0, 2.5)
done = log_message("hello from LambdaScript")
