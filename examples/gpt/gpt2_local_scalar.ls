module Gpt2LocalScalar

max2 : f64 -> f64 -> f64
max2 a b = if a < b then b else a

exp_approx : f64 -> f64
exp_approx x = let x2 = x * x in 1.0 + x + 0.5 * x2 + 0.16666666666666666 * x2 * x + 0.041666666666666664 * x2 * x2

softmax2_left : f64 -> f64 -> f64
softmax2_left a b = let m = max2(a, b) in let ea = exp_approx(a - m) in let eb = exp_approx(b - m) in ea / (ea + eb)

softmax2_right : f64 -> f64 -> f64
softmax2_right a b = let m = max2(a, b) in let ea = exp_approx(a - m) in let eb = exp_approx(b - m) in eb / (ea + eb)

attention_scale : f64 -> f64 -> f64
attention_scale qk inv_sqrt_dk = qk * inv_sqrt_dk

causal_mask : i32 -> i32 -> f64
causal_mask i j = if i < j then -10000000000.0 else 0.0

residual_add : f64 -> f64 -> f64
residual_add x y = x + y

gelu_cubic : f64 -> f64
gelu_cubic z = 0.5 * z * (1.0 + 0.7978845608028654 * (z + 0.044715 * z * z * z))

rsqrt_step : f64 -> f64 -> f64
rsqrt_step y x = 0.5 * y * (3.0 - x * y * y)

rsqrt3 : f64 -> f64
rsqrt3 x = rsqrt_step(rsqrt_step(rsqrt_step(1.0, x), x), x)

layer_norm2_left : f64 -> f64 -> f64 -> f64 -> f64 -> f64
layer_norm2_left x0 x1 gamma beta epsilon = let mean = (x0 + x1) / 2.0 in let d0 = x0 - mean in let d1 = x1 - mean in let var = (d0 * d0 + d1 * d1) / 2.0 in gamma * d0 * rsqrt3(var + epsilon) + beta

linear2 : f64 -> f64 -> f64 -> f64 -> f64 -> f64
linear2 x0 x1 w0 w1 bias = x0 * w0 + x1 * w1 + bias
