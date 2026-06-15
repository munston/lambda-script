module Core0FFITypedBuffers

foreign cpp gpt_alloc_f64_buffer : i32 -> f64buf = "ls_gpt_alloc_f64_buffer"
foreign cpp gpt_free_f64_buffer : f64buf -> void = "ls_gpt_free_f64_buffer"
foreign cpp gpt_read_f64 : f64buf -> i32 -> f64 = "ls_gpt_read_f64"
foreign cpp gpt_write_f64 : f64buf -> i32 -> f64 -> void = "ls_gpt_write_f64"
foreign cpp gpt_alloc_i32_buffer : i32 -> i32buf = "ls_gpt_alloc_i32_buffer"
foreign cpp gpt_free_i32_buffer : i32buf -> void = "ls_gpt_free_i32_buffer"
foreign cpp gpt_create_model : string -> handle = "ls_gpt_create_model"
foreign cpp gpt_free_model : handle -> void = "ls_gpt_free_model"
foreign cpp gpt_model_score : handle -> i32buf -> i32 -> f64 = "ls_gpt_model_score"

weights = gpt_alloc_f64_buffer(16)
tokens = gpt_alloc_i32_buffer(4)
model = gpt_create_model("tiny-gpt")
first_weight = gpt_read_f64(weights, 0)
write_weight = gpt_write_f64(weights, 0, 1.0)
score = gpt_model_score(model, tokens, 4)
free_weights = gpt_free_f64_buffer(weights)
free_tokens = gpt_free_i32_buffer(tokens)
free_model = gpt_free_model(model)
