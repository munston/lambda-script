module Core1PureCalls

add : i32 -> i32 -> i32
add x y = x + y

max_i32 : i32 -> i32 -> i32
max_i32 x y = if x <= y then y else x

total = add(1, 2)
chosen = max_i32(add(1, 1), 3)
