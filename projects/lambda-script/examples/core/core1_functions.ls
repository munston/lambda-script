module Core1Functions

add : i32 -> i32 -> i32
add x y = x + y

max_i32 : i32 -> i32 -> i32
max_i32 x y = if x <= y then y else x

fact : i32 -> i32
fact n = if n <= 1 then 1 else n * fact(n - 1)
